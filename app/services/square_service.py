import os
from datetime import datetime, timezone
from square.client import Client
from app.config import Config
from app.logger import logger
from app.utils.timezone import get_central_today_range, parse_utc_datetime, CENTRAL_TZ

class SquareService:
    def __init__(self):
        access_token = Config.SQUARE_ACCESS_TOKEN
        environment = Config.SQUARE_ENVIRONMENT
        if not access_token:
            raise ValueError("Square access token not found in environment variables")
        
        logger.info(f"Initializing Square client with environment: {environment}")
        self.client = Client(
            access_token=access_token,
            environment=environment
        )

    async def get_active_locations(self):
        """Fetch all active locations from Square"""
        try:
            result = self.client.locations.list_locations()
            if result.is_success():
                locations = result.body.get('locations', [])
                # Filter for active locations
                active_locations = [loc for loc in locations if loc.get('status') == 'ACTIVE']
                logger.info(f"Found {len(active_locations)} active locations")
                
                # Log location details
                for loc in active_locations:
                    logger.info(f"Location: {loc.get('name')}")
                    logger.info(f"Address: {loc.get('address', {})}")
                    
                return active_locations
            else:
                logger.error(f"Error fetching locations: {result.errors}")
                return []
        except Exception as e:
            logger.error(f"Error fetching locations: {str(e)}", exc_info=True)
            return []

    async def fetch_todays_orders(self):
        """Fetch today's orders from Square API for all active locations"""
        try:
            # Get active locations
            active_locations = await self.get_active_locations()
            if not active_locations:
                logger.warning("No active locations found")
                return None

            location_ids = [loc.get('id') for loc in active_locations]
            
            # Get today's date range in Central Time (converted to UTC for API)
            start_time, end_time = get_central_today_range()
            logger.info(f"Fetching orders between {start_time.astimezone(CENTRAL_TZ)} and {end_time.astimezone(CENTRAL_TZ)} for {len(location_ids)} locations")

            # Build the query
            body = {
                "location_ids": location_ids,
                "query": {
                    "filter": {
                        "date_time_filter": {
                            "created_at": {
                                "start_at": start_time.isoformat(),
                                "end_at": end_time.isoformat()
                            }
                        },
                        "state_filter": {
                            "states": ["COMPLETED"]
                        }
                    }
                }
            }

            # Make the API call
            result = self.client.orders.search_orders(body=body)
            
            if result.is_success():
                orders = result.body.get('orders', [])
                logger.info(f"Found {len(orders)} orders across all locations")
                
                # Calculate total sales
                total_sales = sum(float(order.get('total_money', {}).get('amount', 0)) / 100 for order in orders)
                logger.info(f"Total sales across all locations: ${total_sales:.2f}")
                
                return {
                    'total_sales': total_sales,
                    'total_orders': len(orders),
                    'orders': orders,
                    'locations': {
                        loc.get('id'): {
                            'name': loc.get('name'),
                            'sales': sum(
                                float(order.get('total_money', {}).get('amount', 0)) / 100 
                                for order in orders 
                                if order.get('location_id') == loc.get('id')
                            ),
                            'orders': len([
                                order for order in orders 
                                if order.get('location_id') == loc.get('id')
                            ]),
                            'postal_code': loc.get('address', {}).get('postal_code', '').split('-')[0]
                        }
                        for loc in active_locations
                    }
                }
            else:
                logger.error(f"Error fetching orders: {result.errors}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}", exc_info=True)
            return None

    async def get_todays_sales(self):
        """Get today's sales metrics"""
        try:
            logger.info("Fetching today's sales metrics...")
            # Fetch fresh data from Square
            square_data = await self.fetch_todays_orders()
            if not square_data:
                logger.warning("No sales data available")
                return None
            
            # Get inventory metrics (placeholder for now)
            inventory_items = 0
            low_stock_items = 0
            
            return {
                'total_sales': square_data['total_sales'],
                'total_orders': square_data['total_orders'],
                'inventory_items': inventory_items,
                'low_stock_items': low_stock_items,
                'locations': square_data['locations']
            }
            
        except Exception as e:
            logger.error(f"Error getting today's sales: {str(e)}", exc_info=True)
            return None 