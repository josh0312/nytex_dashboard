from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.logger import logger
import os
from decimal import Decimal
from datetime import datetime, date

class ItemsService:
    """Service for handling items data operations"""
    
    @staticmethod
    async def get_items(
        session: AsyncSession,
        sort: Optional[str] = None,
        direction: str = "asc",
        search: Optional[str] = None,
        filters: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get items with optional sorting, searching, and filtering
        Now uses the database view for better reliability and performance
        
        Args:
            session: Database session
            sort: Column to sort by
            direction: Sort direction ('asc' or 'desc')
            search: Global search term
            filters: Dictionary of column filters
            
        Returns:
            List of item dictionaries
        """
        try:
            # Use the view-based query method
            query = ItemsService.get_items_view_query(
                sort_field=sort,
                sort_direction=direction,
                search=search,
                filters=filters
            )
            
            logger.info(f"Executing items view query with sort={sort}, direction={direction}, search={search}")
            
            # Execute the query using the provided session
            result = await session.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dictionaries with proper JSON serialization
            items = []
            for row in rows:
                item_dict = {}
                for i, column in enumerate(columns):
                    value = row[i]
                    # Convert non-JSON-serializable objects
                    if isinstance(value, Decimal):
                        item_dict[column] = float(value)
                    elif isinstance(value, (datetime, date)):
                        item_dict[column] = value.isoformat() if value else None
                    else:
                        item_dict[column] = value
                items.append(item_dict)
            
            logger.info(f"Retrieved {len(items)} items from items_view")
            return items
            
        except Exception as e:
            logger.error(f"Error retrieving items from view: {str(e)}")
            raise
    
    @staticmethod
    async def get_filter_options(session: AsyncSession) -> Dict[str, List[str]]:
        """
        Get unique values for filter dropdowns
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with filter options for each column
        """
        try:
            # Get unique values for key columns
            filter_queries = {
                'categories': "SELECT DISTINCT categories FROM square_item_library_export WHERE archived != 'Y' AND categories IS NOT NULL ORDER BY categories",
                'vendors': "SELECT DISTINCT default_vendor_name FROM square_item_library_export WHERE archived != 'Y' AND default_vendor_name IS NOT NULL ORDER BY default_vendor_name",
                'item_types': "SELECT DISTINCT item_type FROM square_item_library_export WHERE archived != 'Y' AND item_type IS NOT NULL ORDER BY item_type",
                'prices': """
                    SELECT DISTINCT price_value FROM (
                        SELECT CASE 
                            WHEN cv.price_money IS NOT NULL AND (cv.price_money->>'amount') IS NOT NULL AND (cv.price_money->>'amount') != ''
                            THEN (cv.price_money->>'amount')::numeric / 100
                            WHEN sile.price IS NOT NULL 
                            THEN sile.price
                            ELSE NULL 
                        END AS price_value
                        FROM square_item_library_export sile
                        LEFT JOIN catalog_variations cv ON sile.sku = cv.sku AND cv.is_deleted = false
                        WHERE sile.archived != 'Y'
                    ) prices 
                    WHERE price_value IS NOT NULL 
                    ORDER BY price_value
                """,
                'costs': """
                    SELECT DISTINCT cost_value FROM (
                        SELECT CASE 
                            WHEN cv.default_unit_cost IS NOT NULL AND (cv.default_unit_cost->>'amount') IS NOT NULL AND (cv.default_unit_cost->>'amount') != ''
                            THEN (cv.default_unit_cost->>'amount')::numeric / 100
                            WHEN sile.default_unit_cost IS NOT NULL 
                            THEN sile.default_unit_cost
                            ELSE NULL 
                        END AS cost_value
                        FROM square_item_library_export sile
                        LEFT JOIN catalog_variations cv ON sile.sku = cv.sku AND cv.is_deleted = false
                        WHERE sile.archived != 'Y'
                    ) costs 
                    WHERE cost_value IS NOT NULL 
                    ORDER BY cost_value
                """
            }
            
            filter_options = {}
            
            for key, query in filter_queries.items():
                result = await session.execute(text(query))
                if key in ['prices', 'costs']:
                    # For price and cost, convert to float for sorting and format for display
                    values = []
                    for row in result.fetchall():
                        if row[0] is not None:
                            try:
                                # Convert to float for proper sorting
                                numeric_value = float(row[0])
                                values.append(numeric_value)
                            except (ValueError, TypeError):
                                continue
                    # Sort numerically and keep as numbers (Tabulator will format them)
                    filter_options[key] = sorted(list(set(values)))
                else:
                    # For text fields, keep as strings
                    values = [row[0] for row in result.fetchall() if row[0]]
                    filter_options[key] = sorted(set(values))
            
            return filter_options
            
        except Exception as e:
            logger.error(f"Error getting filter options: {str(e)}")
            return {}

    # Add view-based query method
    @staticmethod
    def get_items_view_query(sort_field=None, sort_direction="asc", search=None, filters=None):
        """Get items query using the database view (much simpler and more reliable)"""
        
        # Base query using the view
        query = "SELECT * FROM items_view"
        
        # Apply search if provided
        conditions = []
        if search:
            conditions.append(f"""
                (item_name ILIKE '%{search}%' 
                OR sku ILIKE '%{search}%' 
                OR description ILIKE '%{search}%'
                OR vendor_name ILIKE '%{search}%')
            """)
        
        # Apply filters if provided
        if filters:
            for field, value in filters.items():
                if value:  # Only apply non-empty filters
                    if field in ['price', 'cost', 'profit_margin_percent', 'profit_markup_percent']:
                        # Numeric fields
                        conditions.append(f"{field} = {value}")
                    else:
                        # String fields
                        conditions.append(f"{field} ILIKE '%{value}%'")
        
        # Add WHERE clause if we have conditions
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        valid_sort_fields = [
            'item_name', 'sku', 'category', 'price', 'cost', 'vendor_name', 'vendor_code',
            'profit_margin_percent', 'profit_markup_percent', 'aubrey_qty', 'bridgefarmer_qty',
            'building_qty', 'flomo_qty', 'justin_qty', 'quinlan_qty', 'terrell_qty', 'total_qty',
            'item_type', 'archived', 'sellable', 'stockable', 'created_at', 'updated_at'
        ]
        
        if sort_field and sort_field in valid_sort_fields:
            direction = "DESC" if sort_direction.upper() == "DESC" else "ASC" 
            query += f" ORDER BY {sort_field} {direction}"
        else:
            query += " ORDER BY item_name ASC"  # Default sort
            
        return query 