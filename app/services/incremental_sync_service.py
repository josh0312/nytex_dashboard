"""
Incremental Sync Service
Handles intelligent change detection and targeted updates from Square API
"""
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, update, delete, and_
from sqlalchemy.dialects.postgresql import insert
import json

from app.config import Config
from app.logger import logger
from app.database.models.location import Location
from app.database.models.catalog import CatalogCategory, CatalogItem, CatalogVariation, CatalogInventory
from app.database.models.vendor import Vendor


class IncrementalSyncService:
    """Service for performing incremental data synchronization with Square API"""
    
    def __init__(self):
        self.square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
        self.square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'production')
        
        if self.square_environment.lower() == 'production':
            self.base_url = "https://connect.squareup.com"
        else:
            self.base_url = "https://connect.squareupsandbox.com"
            
        self.timeout = aiohttp.ClientTimeout(total=600)
        
        # Sync configurations for each data type
        self.sync_configs = {
            'locations': {
                'model': Location,
                'api_endpoint': '/v2/locations',
                'method': 'GET',
                'update_strategy': 'timestamp',
                'dependencies': []
            },
            'catalog_categories': {
                'model': CatalogCategory,
                'api_endpoint': '/v2/catalog/search',
                'method': 'POST',
                'update_strategy': 'version',
                'dependencies': [],
                'object_types': ['CATEGORY']
            },
            'catalog_items': {
                'model': CatalogItem,
                'api_endpoint': '/v2/catalog/search',
                'method': 'POST',
                'update_strategy': 'version',
                'dependencies': ['catalog_categories'],
                'object_types': ['ITEM']
            },
            'catalog_variations': {
                'model': CatalogVariation,
                'api_endpoint': '/v2/catalog/search',
                'method': 'POST',
                'update_strategy': 'version',
                'dependencies': ['catalog_items'],
                'object_types': ['ITEM_VARIATION']
            },
            'catalog_inventory': {
                'model': CatalogInventory,
                'api_endpoint': '/v2/inventory/counts/batch-retrieve',
                'method': 'POST',
                'update_strategy': 'timestamp',
                'dependencies': ['catalog_variations', 'locations']
            },
            'vendors': {
                'model': Vendor,
                'api_endpoint': '/v2/vendors',
                'method': 'GET',
                'update_strategy': 'timestamp',
                'dependencies': []
            },
            'orders': {
                'model': None,  # We'll need to create these models
                'api_endpoint': '/v2/orders/search',
                'method': 'POST',
                'update_strategy': 'timestamp',
                'dependencies': ['locations']
            },
            'payments': {
                'model': None,  # We'll need to create these models
                'api_endpoint': '/v2/payments',
                'method': 'GET', 
                'update_strategy': 'timestamp',
                'dependencies': ['locations']
            },
            'transactions': {
                'model': None,  # We'll need to create these models  
                'api_endpoint': '/v2/transactions',
                'method': 'GET',
                'update_strategy': 'timestamp',
                'dependencies': ['locations']
            }
        }

    async def run_incremental_sync(self, session: AsyncSession, sync_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run incremental sync for specified data types"""
        try:
            logger.info("🔄 Starting Incremental Sync")
            logger.info("=" * 50)
            
            if not self.square_access_token:
                return {
                    'success': False,
                    'error': 'Square access token not configured',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            
            # Initialize sync state tracking if not exists
            await self._ensure_sync_state_table(session)
            
            # Determine which syncs to run
            if sync_types is None:
                sync_types = list(self.sync_configs.keys())
            
            # Order syncs by dependencies
            ordered_syncs = self._order_syncs_by_dependencies(sync_types)
            
            results = {}
            total_changes = 0
            
            for sync_type in ordered_syncs:
                logger.info(f"🔄 Processing {sync_type}...")
                
                result = await self._sync_data_type(session, sync_type)
                results[sync_type] = result
                
                if result['success']:
                    total_changes += result.get('changes_applied', 0)
                    logger.info(f"✅ {sync_type}: {result.get('changes_applied', 0)} changes applied")
                else:
                    logger.error(f"❌ {sync_type}: {result.get('error', 'Unknown error')}")
                    # Continue with other syncs even if one fails
            
            # Update overall sync status
            await self._update_sync_status(session, 'incremental_sync', total_changes)
            
            logger.info("=" * 50)
            logger.info(f"✅ Incremental sync completed - {total_changes} total changes applied")
            
            return {
                'success': True,
                'total_changes': total_changes,
                'results': results,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Incremental sync failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    async def _sync_data_type(self, session: AsyncSession, sync_type: str) -> Dict[str, Any]:
        """Sync a specific data type incrementally"""
        try:
            config = self.sync_configs[sync_type]
            
            # Get last sync timestamp
            last_sync = await self._get_last_sync_timestamp(session, sync_type)
            
            # Fetch changes from Square API
            if sync_type == 'locations':
                changes = await self._fetch_location_changes(last_sync)
            elif sync_type.startswith('catalog_'):
                changes = await self._fetch_catalog_changes(sync_type, config, last_sync)
            elif sync_type == 'vendors':
                changes = await self._fetch_vendor_changes(last_sync)
            elif sync_type == 'orders':
                changes = await self._fetch_orders_changes(last_sync)
            elif sync_type == 'payments':
                changes = await self._fetch_payments_changes(last_sync)
            elif sync_type == 'transactions':
                changes = await self._fetch_transactions_changes(last_sync)
            else:
                return {'success': False, 'error': f'Unknown sync type: {sync_type}'}
            
            if not changes['success']:
                return changes
            
            # Apply changes to database
            changes_applied = await self._apply_changes(session, sync_type, changes['data'])
            
            # Update sync timestamp
            await self._update_last_sync_timestamp(session, sync_type, changes_applied)
            
            return {
                'success': True,
                'changes_applied': changes_applied,
                'last_sync': last_sync.isoformat() if last_sync else None,
                'new_sync_time': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error syncing {sync_type}: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def _fetch_location_changes(self, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch location changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/locations"
                headers = {'Authorization': f'Bearer {self.square_access_token}'}
                
                async with client_session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        locations = data.get('locations', [])
                        
                        # For now, return all locations (in a real incremental system, 
                        # we'd filter by updated_at > last_sync)
                        return {
                            'success': True,
                            'data': locations,
                            'total_items': len(locations)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fetch_catalog_changes(self, sync_type: str, config: Dict, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch catalog changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/catalog/search"
                headers = {
                    'Authorization': f'Bearer {self.square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                all_objects = []
                
                for object_type in config.get('object_types', []):
                    cursor = None
                    page = 1
                    
                    while True:
                        payload = {
                            "object_types": [object_type],
                            "include_deleted_objects": False,
                            "limit": 1000
                        }
                        
                        if cursor:
                            payload["cursor"] = cursor
                        
                        # Add timestamp filter if we have a last sync time
                        if last_sync and sync_type != 'catalog_inventory':
                            # For catalog items, use updated_at filter
                            # Note: Square API may not support this filter for all endpoints
                            pass
                        
                        async with client_session.post(url, headers=headers, json=payload) as response:
                            if response.status == 200:
                                data = await response.json()
                                objects = data.get('objects', [])
                                all_objects.extend(objects)
                                
                                cursor = data.get('cursor')
                                if not cursor:
                                    break
                                    
                                page += 1
                                logger.info(f"  📄 Fetched page {page} - {len(objects)} {object_type} objects")
                            else:
                                error_text = await response.text()
                                return {
                                    'success': False,
                                    'error': f'Square API error: {response.status} - {error_text}'
                                }
                
                return {
                    'success': True,
                    'data': all_objects,
                    'total_items': len(all_objects)
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fetch_vendor_changes(self, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch vendor changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/vendors"
                headers = {'Authorization': f'Bearer {self.square_access_token}'}
                
                async with client_session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        vendors = data.get('vendors', [])
                        
                        return {
                            'success': True,
                            'data': vendors,
                            'total_items': len(vendors)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fetch_orders_changes(self, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch orders changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/orders/search"
                headers = {
                    'Authorization': f'Bearer {self.square_access_token}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    "query": {
                        "filter": {
                            "updated_at": {
                                "start_at": last_sync.isoformat() if last_sync else None,
                                "end_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    }
                }
                
                async with client_session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        orders = data.get('orders', [])
                        
                        return {
                            'success': True,
                            'data': orders,
                            'total_items': len(orders)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fetch_payments_changes(self, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch payments changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/payments"
                headers = {'Authorization': f'Bearer {self.square_access_token}'}
                
                payload = {
                    "query": {
                        "filter": {
                            "updated_at": {
                                "start_at": last_sync.isoformat() if last_sync else None,
                                "end_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    }
                }
                
                async with client_session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        payments = data.get('payments', [])
                        
                        return {
                            'success': True,
                            'data': payments,
                            'total_items': len(payments)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _fetch_transactions_changes(self, last_sync: Optional[datetime]) -> Dict[str, Any]:
        """Fetch transactions changes from Square API"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                url = f"{self.base_url}/v2/transactions"
                headers = {'Authorization': f'Bearer {self.square_access_token}'}
                
                payload = {
                    "query": {
                        "filter": {
                            "updated_at": {
                                "start_at": last_sync.isoformat() if last_sync else None,
                                "end_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    }
                }
                
                async with client_session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        transactions = data.get('transactions', [])
                        
                        return {
                            'success': True,
                            'data': transactions,
                            'total_items': len(transactions)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f'Square API error: {response.status} - {error_text}'
                        }
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _apply_changes(self, session: AsyncSession, sync_type: str, data: List[Dict[str, Any]]) -> int:
        """Apply changes to the database using upsert strategy"""
        changes_applied = 0
        
        try:
            if sync_type == 'locations':
                changes_applied = await self._apply_location_changes(session, data)
            elif sync_type == 'catalog_categories':
                changes_applied = await self._apply_category_changes(session, data)
            elif sync_type == 'catalog_items':
                changes_applied = await self._apply_item_changes(session, data)
            elif sync_type == 'catalog_variations':
                changes_applied = await self._apply_variation_changes(session, data)
            elif sync_type == 'catalog_inventory':
                changes_applied = await self._apply_inventory_changes(session, data)
            elif sync_type == 'vendors':
                changes_applied = await self._apply_vendor_changes(session, data)
            elif sync_type == 'orders':
                changes_applied = await self._apply_orders_changes(session, data)
            elif sync_type == 'payments':
                changes_applied = await self._apply_payments_changes(session, data)
            elif sync_type == 'transactions':
                changes_applied = await self._apply_transactions_changes(session, data)
            
        except Exception as e:
            logger.error(f"Error applying {sync_type} changes: {str(e)}", exc_info=True)
            raise
        
        return changes_applied

    async def _apply_location_changes(self, session: AsyncSession, locations: List[Dict[str, Any]]) -> int:
        """Apply location changes using upsert"""
        changes = 0
        
        for location_data in locations:
            stmt = insert(Location).values(
                id=location_data['id'],
                name=location_data.get('name', ''),
                address=json.dumps(location_data.get('address', {})),
                timezone=location_data.get('timezone', ''),
                status=location_data.get('status', 'ACTIVE'),
                capabilities=location_data.get('capabilities', []),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                description=location_data.get('description', ''),
                coordinates=json.dumps(location_data.get('coordinates', {})),
                business_hours=location_data.get('business_hours', {}),
                business_email=location_data.get('business_email', ''),
                phone_number=location_data.get('phone_number', ''),
                website_url=location_data.get('website_url', '')
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(
                    name=stmt.excluded.name,
                    address=stmt.excluded.address,
                    timezone=stmt.excluded.timezone,
                    status=stmt.excluded.status,
                    capabilities=stmt.excluded.capabilities,
                    updated_at=stmt.excluded.updated_at,
                    description=stmt.excluded.description,
                    coordinates=stmt.excluded.coordinates,
                    business_hours=stmt.excluded.business_hours,
                    business_email=stmt.excluded.business_email,
                    phone_number=stmt.excluded.phone_number,
                    website_url=stmt.excluded.website_url
                )
            )
            
            await session.execute(stmt)
            changes += 1
        
        return changes

    async def _apply_category_changes(self, session: AsyncSession, categories: List[Dict[str, Any]]) -> int:
        """Apply category changes using upsert"""
        changes = 0
        
        for category_data in categories:
            category_info = category_data.get('category_data', {})
            
            stmt = insert(CatalogCategory).values(
                id=category_data['id'],
                name=category_info.get('name', ''),
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(
                    name=stmt.excluded.name,
                    is_deleted=stmt.excluded.is_deleted,
                    updated_at=stmt.excluded.updated_at
                )
            )
            
            await session.execute(stmt)
            changes += 1
        
        return changes

    async def _apply_item_changes(self, session: AsyncSession, items: List[Dict[str, Any]]) -> int:
        """Apply item changes using upsert"""
        changes = 0
        
        for item_data in items:
            item_info = item_data.get('item_data', {})
            
            stmt = insert(CatalogItem).values(
                id=item_data['id'],
                name=item_info.get('name', ''),
                description=item_info.get('description', ''),
                category_id=item_info.get('category_id'),
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(
                    name=stmt.excluded.name,
                    description=stmt.excluded.description,
                    category_id=stmt.excluded.category_id,
                    is_deleted=stmt.excluded.is_deleted,
                    updated_at=stmt.excluded.updated_at
                )
            )
            
            await session.execute(stmt)
            changes += 1
        
        return changes

    async def _apply_variation_changes(self, session: AsyncSession, variations: List[Dict[str, Any]]) -> int:
        """Apply variation changes using upsert"""
        changes = 0
        
        for variation_data in variations:
            variation_info = variation_data.get('item_variation_data', {})
            
            stmt = insert(CatalogVariation).values(
                id=variation_data['id'],
                name=variation_info.get('name', ''),
                item_id=variation_info.get('item_id'),
                sku=variation_info.get('sku', ''),
                price_money=json.dumps(variation_info.get('price_money', {})),
                is_deleted=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(
                    name=stmt.excluded.name,
                    item_id=stmt.excluded.item_id,
                    sku=stmt.excluded.sku,
                    price_money=stmt.excluded.price_money,
                    is_deleted=stmt.excluded.is_deleted,
                    updated_at=stmt.excluded.updated_at
                )
            )
            
            await session.execute(stmt)
            changes += 1
        
        return changes

    async def _apply_inventory_changes(self, session: AsyncSession, inventory_data: List[Dict[str, Any]]) -> int:
        """Apply inventory changes using upsert"""
        changes = 0
        
        # This would be implemented based on the inventory API response structure
        # For now, placeholder implementation
        
        return changes

    async def _apply_vendor_changes(self, session: AsyncSession, vendors: List[Dict[str, Any]]) -> int:
        """Apply vendor changes using upsert"""
        changes = 0
        
        for vendor_data in vendors:
            stmt = insert(Vendor).values(
                id=vendor_data['id'],
                name=vendor_data.get('name', ''),
                account_number=vendor_data.get('account_number', ''),
                note=vendor_data.get('note', ''),
                status=vendor_data.get('status', 'ACTIVE'),
                version=vendor_data.get('version', ''),
                address=json.dumps(vendor_data.get('address', {})),
                contacts=json.dumps(vendor_data.get('contacts', [])),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                synced_at=datetime.utcnow()
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_=dict(
                    name=stmt.excluded.name,
                    account_number=stmt.excluded.account_number,
                    note=stmt.excluded.note,
                    status=stmt.excluded.status,
                    version=stmt.excluded.version,
                    address=stmt.excluded.address,
                    contacts=stmt.excluded.contacts,
                    updated_at=stmt.excluded.updated_at,
                    synced_at=stmt.excluded.synced_at
                )
            )
            
            await session.execute(stmt)
            changes += 1
        
        return changes

    async def _apply_orders_changes(self, session: AsyncSession, orders: List[Dict[str, Any]]) -> int:
        """Apply orders changes using raw SQL upsert"""
        changes = 0
        
        for order_data in orders:
            await session.execute(text("""
                INSERT INTO orders (
                    id, location_id, created_at, updated_at, closed_at,
                    state, version, total_money, total_tax_money, total_discount_money,
                    net_amounts, source, return_amounts, order_metadata
                ) VALUES (
                    :id, :location_id, :created_at, :updated_at, :closed_at,
                    :state, :version, :total_money, :total_tax_money, :total_discount_money,
                    :net_amounts, :source, :return_amounts, :order_metadata
                )
                ON CONFLICT (id) DO UPDATE SET
                    location_id = EXCLUDED.location_id,
                    updated_at = EXCLUDED.updated_at,
                    closed_at = EXCLUDED.closed_at,
                    state = EXCLUDED.state,
                    version = EXCLUDED.version,
                    total_money = EXCLUDED.total_money,
                    total_tax_money = EXCLUDED.total_tax_money,
                    total_discount_money = EXCLUDED.total_discount_money,
                    net_amounts = EXCLUDED.net_amounts,
                    source = EXCLUDED.source,
                    return_amounts = EXCLUDED.return_amounts,
                    order_metadata = EXCLUDED.order_metadata
            """), {
                'id': order_data['id'],
                'location_id': order_data.get('location_id'),
                'created_at': order_data.get('created_at'),
                'updated_at': order_data.get('updated_at'),
                'closed_at': order_data.get('closed_at'),
                'state': order_data.get('state'),
                'version': order_data.get('version'),
                'total_money': json.dumps(order_data.get('total_money', {})),
                'total_tax_money': json.dumps(order_data.get('total_tax_money', {})),
                'total_discount_money': json.dumps(order_data.get('total_discount_money', {})),
                'net_amounts': json.dumps(order_data.get('net_amounts', {})),
                'source': json.dumps(order_data.get('source', {})),
                'return_amounts': json.dumps(order_data.get('return_amounts', {})),
                'order_metadata': json.dumps(order_data.get('metadata', {}))
            })
            changes += 1
        
        return changes

    async def _apply_payments_changes(self, session: AsyncSession, payments: List[Dict[str, Any]]) -> int:
        """Apply payments changes using raw SQL upsert"""
        changes = 0
        
        for payment_data in payments:
            await session.execute(text("""
                INSERT INTO payments (
                    id, created_at, updated_at, amount_money, status, source_type,
                    location_id, order_id, receipt_number, receipt_url, card_details,
                    cash_details, external_details, refunded_money, approved_money,
                    processing_fee, refund_ids, risk_evaluation, buyer_email_address,
                    billing_address, shipping_address, note, statement_description_identifier,
                    total_money, tip_money, app_fee_money, delay_duration, delay_action,
                    delayed_until, reference_id, capabilities, device_details,
                    application_details, version_token
                ) VALUES (
                    :id, :created_at, :updated_at, :amount_money, :status, :source_type,
                    :location_id, :order_id, :receipt_number, :receipt_url, :card_details,
                    :cash_details, :external_details, :refunded_money, :approved_money,
                    :processing_fee, :refund_ids, :risk_evaluation, :buyer_email_address,
                    :billing_address, :shipping_address, :note, :statement_description_identifier,
                    :total_money, :tip_money, :app_fee_money, :delay_duration, :delay_action,
                    :delayed_until, :reference_id, :capabilities, :device_details,
                    :application_details, :version_token
                )
                ON CONFLICT (id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    status = EXCLUDED.status,
                    amount_money = EXCLUDED.amount_money,
                    refunded_money = EXCLUDED.refunded_money,
                    approved_money = EXCLUDED.approved_money,
                    processing_fee = EXCLUDED.processing_fee,
                    version_token = EXCLUDED.version_token
            """), {
                'id': payment_data['id'],
                'created_at': payment_data.get('created_at'),
                'updated_at': payment_data.get('updated_at'),
                'amount_money': json.dumps(payment_data.get('amount_money', {})),
                'status': payment_data.get('status'),
                'source_type': payment_data.get('source_type'),
                'location_id': payment_data.get('location_id'),
                'order_id': payment_data.get('order_id'),
                'receipt_number': payment_data.get('receipt_number'),
                'receipt_url': payment_data.get('receipt_url'),
                'card_details': json.dumps(payment_data.get('card_details', {})),
                'cash_details': json.dumps(payment_data.get('cash_details', {})),
                'external_details': json.dumps(payment_data.get('external_details', {})),
                'refunded_money': json.dumps(payment_data.get('refunded_money', {})),
                'approved_money': json.dumps(payment_data.get('approved_money', {})),
                'processing_fee': json.dumps(payment_data.get('processing_fee', {})),
                'refund_ids': json.dumps(payment_data.get('refund_ids', [])),
                'risk_evaluation': json.dumps(payment_data.get('risk_evaluation', {})),
                'buyer_email_address': payment_data.get('buyer_email_address'),
                'billing_address': json.dumps(payment_data.get('billing_address', {})),
                'shipping_address': json.dumps(payment_data.get('shipping_address', {})),
                'note': payment_data.get('note'),
                'statement_description_identifier': payment_data.get('statement_description_identifier'),
                'total_money': json.dumps(payment_data.get('total_money', {})),
                'tip_money': json.dumps(payment_data.get('tip_money', {})),
                'app_fee_money': json.dumps(payment_data.get('app_fee_money', {})),
                'delay_duration': payment_data.get('delay_duration'),
                'delay_action': payment_data.get('delay_action'),
                'delayed_until': payment_data.get('delayed_until'),
                'reference_id': payment_data.get('reference_id'),
                'capabilities': json.dumps(payment_data.get('capabilities', [])),
                'device_details': json.dumps(payment_data.get('device_details', {})),
                'application_details': json.dumps(payment_data.get('application_details', {})),
                'version_token': payment_data.get('version_token')
            })
            changes += 1
        
        return changes

    async def _apply_transactions_changes(self, session: AsyncSession, transactions: List[Dict[str, Any]]) -> int:
        """Apply transactions changes using raw SQL upsert"""
        changes = 0
        
        for transaction_data in transactions:
            await session.execute(text("""
                INSERT INTO transactions (
                    id, location_id, created_at
                ) VALUES (
                    :id, :location_id, :created_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    location_id = EXCLUDED.location_id,
                    created_at = EXCLUDED.created_at
            """), {
                'id': transaction_data['id'],
                'location_id': transaction_data.get('location_id'),
                'created_at': transaction_data.get('created_at')
            })
            changes += 1
        
        return changes

    async def _ensure_sync_state_table(self, session: AsyncSession):
        """Ensure sync_state table exists"""
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS sync_state (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(50) UNIQUE,
                last_sync_timestamp TIMESTAMP,
                last_sync_version BIGINT,
                records_synced INTEGER,
                sync_duration_seconds INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))

    async def _get_last_sync_timestamp(self, session: AsyncSession, sync_type: str) -> Optional[datetime]:
        """Get the last sync timestamp for a data type"""
        result = await session.execute(text("""
            SELECT last_sync_timestamp FROM sync_state 
            WHERE table_name = :table_name
        """), {"table_name": sync_type})
        
        row = result.fetchone()
        return row[0] if row else None

    async def _update_last_sync_timestamp(self, session: AsyncSession, sync_type: str, records_synced: int):
        """Update the last sync timestamp for a data type"""
        await session.execute(text("""
            INSERT INTO sync_state (table_name, last_sync_timestamp, records_synced, updated_at)
            VALUES (:table_name, NOW(), :records_synced, NOW())
            ON CONFLICT (table_name) DO UPDATE SET
                last_sync_timestamp = NOW(),
                records_synced = :records_synced,
                updated_at = NOW()
        """), {"table_name": sync_type, "records_synced": records_synced})

    async def _update_sync_status(self, session: AsyncSession, sync_name: str, total_changes: int):
        """Update overall sync status"""
        await session.execute(text("""
            INSERT INTO sync_state (table_name, last_sync_timestamp, records_synced, updated_at)
            VALUES (:sync_name, NOW(), :total_changes, NOW())
            ON CONFLICT (table_name) DO UPDATE SET
                last_sync_timestamp = NOW(),
                records_synced = :total_changes,
                updated_at = NOW()
        """), {"sync_name": sync_name, "total_changes": total_changes})

    def _order_syncs_by_dependencies(self, sync_types: List[str]) -> List[str]:
        """Order syncs by their dependencies"""
        ordered = []
        remaining = set(sync_types)
        
        while remaining:
            # Find syncs with no remaining dependencies
            ready = []
            for sync_type in remaining:
                deps = set(self.sync_configs[sync_type].get('dependencies', []))
                if deps.issubset(set(ordered)):
                    ready.append(sync_type)
            
            if not ready:
                # If no syncs are ready, there might be a circular dependency
                # Just pick the first one
                ready = [list(remaining)[0]]
            
            for sync_type in ready:
                ordered.append(sync_type)
                remaining.remove(sync_type)
        
        return ordered

    async def get_sync_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get comprehensive sync status"""
        try:
            result = await session.execute(text("""
                SELECT table_name, last_sync_timestamp, records_synced, sync_duration_seconds, updated_at
                FROM sync_state
                ORDER BY updated_at DESC
            """))
            
            sync_statuses = []
            for row in result.fetchall():
                sync_statuses.append({
                    'table_name': row[0],
                    'last_sync_timestamp': row[1].isoformat() if row[1] else None,
                    'records_synced': row[2],
                    'sync_duration_seconds': row[3],
                    'updated_at': row[4].isoformat() if row[4] else None
                })
            
            return {
                'success': True,
                'sync_statuses': sync_statuses,
                'total_tables_tracked': len(sync_statuses),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            } 