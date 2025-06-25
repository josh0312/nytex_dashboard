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
            logger.info("=== Starting Square API orders fetch ===")
            # Get active locations
            logger.info("Fetching active locations...")
            active_locations = await self.get_active_locations()
            if not active_locations:
                logger.warning("No active locations found")
                return None

            location_ids = [loc.get('id') for loc in active_locations]
            logger.info(f"Found {len(location_ids)} active locations")
            
            # Get today's date range in Central Time (converted to UTC for API)
            start_time, end_time = get_central_today_range()
            logger.info(f"Date range for orders:")
            logger.info(f"- Start: {start_time.astimezone(CENTRAL_TZ)} Central")
            logger.info(f"- End: {end_time.astimezone(CENTRAL_TZ)} Central")

            # Build the base query
            base_query = {
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
                },
                "limit": 500  # Maximum allowed by Square API
            }
            logger.info("Prepared Square API base query")

            # Initialize variables for pagination
            all_orders = []
            cursor = None
            page = 1

            while True:
                # Add cursor to query if we have one
                body = base_query.copy()
                if cursor:
                    body["cursor"] = cursor

                logger.info(f"Making Square API search_orders call (page {page})...")
                result = self.client.orders.search_orders(body=body)
                
                if result.is_success():
                    orders = result.body.get('orders', [])
                    logger.info(f"Retrieved {len(orders)} orders on page {page}")
                    all_orders.extend(orders)
                    
                    # Check if we have more pages
                    cursor = result.body.get('cursor')
                    if not cursor:
                        logger.info("No more pages to fetch")
                        break
                    
                    page += 1
                    logger.info(f"Moving to page {page}")
                else:
                    logger.error(f"Square API error: {result.errors}")
                    logger.error("=== Failed Square API orders fetch ===")
                    return None

            logger.info(f"Successfully retrieved {len(all_orders)} total orders across all pages")
            
            # Calculate total sales
            total_sales = sum(float(order.get('total_money', {}).get('amount', 0)) / 100 for order in all_orders)
            logger.info(f"Calculated total sales: ${total_sales:,.2f}")
            
            # Filter out $0 orders (no sale transactions to open cash drawer)
            orders_with_sales = [order for order in all_orders if float(order.get('total_money', {}).get('amount', 0)) > 0]
            logger.info(f"Filtered out {len(all_orders) - len(orders_with_sales)} $0 orders (no sale transactions)")
            
            # Process location data
            locations_data = {}
            for loc in active_locations:
                loc_id = loc.get('id')
                loc_orders = [order for order in orders_with_sales if order.get('location_id') == loc_id]
                loc_sales = sum(float(order.get('total_money', {}).get('amount', 0)) / 100 for order in loc_orders)
                
                locations_data[loc_id] = {
                    'name': loc.get('name'),
                    'sales': loc_sales,
                    'orders': len(loc_orders),
                    'postal_code': loc.get('address', {}).get('postal_code', '').split('-')[0]
                }
                logger.info(f"Location {loc.get('name')}: ${loc_sales:,.2f} ({len(loc_orders)} orders)")
            
            response_data = {
                'total_sales': total_sales,
                'total_orders': len(orders_with_sales),
                'orders': orders_with_sales,
                'locations': locations_data
            }
            
            logger.info("Successfully compiled orders response")
            logger.info("=== Completed Square API orders fetch ===")
            return response_data
                
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}", exc_info=True)
            logger.error("=== Failed Square API orders fetch ===")
            return None

    async def get_todays_sales(self):
        """Get today's sales metrics"""
        try:
            logger.info("=== Starting Square API sales metrics fetch ===")
            # Fetch fresh data from Square
            logger.info("Initiating fetch_todays_orders call...")
            square_data = await self.fetch_todays_orders()
            logger.info(f"fetch_todays_orders returned data: {bool(square_data)}")
            
            if not square_data:
                logger.warning("No sales data available from Square API")
                return None
            
            # Extract metrics
            total_sales = square_data.get('total_sales', 0)
            total_orders = square_data.get('total_orders', 0)
            locations = square_data.get('locations', {})
            
            logger.info(f"Processed metrics:")
            logger.info(f"- Total Sales: ${total_sales:,.2f}")
            logger.info(f"- Total Orders: {total_orders}")
            logger.info(f"- Number of Locations: {len(locations)}")
            
            # Get inventory metrics (placeholder for now)
            inventory_items = 0
            low_stock_items = 0
            
            metrics = {
                'total_sales': total_sales,
                'total_orders': total_orders,
                'inventory_items': inventory_items,
                'low_stock_items': low_stock_items,
                'locations': locations
            }
            
            logger.info("Successfully compiled sales metrics")
            logger.info("=== Completed Square API sales metrics fetch ===")
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting today's sales: {str(e)}", exc_info=True)
            logger.error("=== Failed Square API sales metrics fetch ===")
            return None 