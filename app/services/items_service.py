from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.logger import logger
import os

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
        Get items data with optional sorting, filtering, and search
        
        Args:
            session: Database session
            sort: Column to sort by
            direction: Sort direction (asc/desc)
            search: Global search term
            filters: Column-specific filters
            
        Returns:
            List of item dictionaries
        """
        try:
            # Load the base query
            query_file = os.path.join(os.path.dirname(__file__), '..', 'database', 'queries', 'items_inventory.sql')
            with open(query_file, 'r') as f:
                base_query = f.read()
            
            # Remove comments and get just the query part
            query_lines = []
            in_query = False
            for line in base_query.split('\n'):
                if line.strip().startswith('SELECT') or in_query:
                    in_query = True
                    if not line.strip().startswith('--'):
                        query_lines.append(line)
            
            query = '\n'.join(query_lines).strip()
            
            # Build WHERE conditions
            where_conditions = ["archived != 'Y'"]
            
            # Add global search if provided
            if search and search.strip():
                # Escape single quotes in search term
                escaped_search = search.replace("'", "''")
                search_condition = f"""
                (LOWER(item_name) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sku, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(description, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(categories, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(default_vendor_name, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(default_vendor_code, '')) LIKE LOWER('%{escaped_search}%'))
                """
                where_conditions.append(search_condition)
            
            # Add column-specific filters if provided
            if filters:
                for column, value in filters.items():
                    if value and value.strip():
                        # Escape single quotes in filter value
                        escaped_value = value.replace("'", "''")
                        
                        # Map display column names to actual column names
                        column_mapping = {
                            'item_name': 'item_name',
                            'sku': 'sku',
                            'description': 'description',
                            'category': 'categories',
                            'vendor_name': 'default_vendor_name',
                            'vendor_code': 'default_vendor_code'
                        }
                        
                        actual_column = column_mapping.get(column, column)
                        filter_condition = f"LOWER(COALESCE({actual_column}, '')) LIKE LOWER('%{escaped_value}%')"
                        where_conditions.append(filter_condition)
            
            # Replace the existing WHERE clause
            if 'WHERE' in query:
                # Split on WHERE and preserve everything after GROUP BY
                query_parts = query.split('WHERE')
                before_where = query_parts[0]
                after_where = query_parts[1] if len(query_parts) > 1 else ''
                
                # Check if there's a GROUP BY clause after WHERE
                if 'GROUP BY' in after_where:
                    group_by_part = 'GROUP BY' + after_where.split('GROUP BY')[1]
                    query = before_where + 'WHERE ' + ' AND '.join(where_conditions) + ' ' + group_by_part
                else:
                    query = before_where + 'WHERE ' + ' AND '.join(where_conditions)
            else:
                query += ' WHERE ' + ' AND '.join(where_conditions)
            
            # Add sorting if specified
            if sort:
                # Map display column names to query column aliases
                sort_mapping = {
                    'item_name': 'item_name',
                    'sku': 'sku',
                    'description': 'description',
                    'category': 'category',
                    'price': 'price',
                    'vendor_name': 'vendor_name',
                    'vendor_code': 'vendor_code',
                    'profit_margin_percent': 'profit_margin_percent',
                    'total_qty': 'total_qty',
                    'aubrey_qty': 'aubrey_qty',
                    'bridgefarmer_qty': 'bridgefarmer_qty',
                    'building_qty': 'building_qty',
                    'flomo_qty': 'flomo_qty',
                    'justin_qty': 'justin_qty',
                    'quinlan_qty': 'quinlan_qty',
                    'terrell_qty': 'terrell_qty'
                }
                
                actual_sort_column = sort_mapping.get(sort, 'item_name')
                
                # Remove existing ORDER BY and add new one
                if 'ORDER BY' in query:
                    query = query.split('ORDER BY')[0]
                
                query += f' ORDER BY {actual_sort_column} {direction.upper()}'
            elif 'ORDER BY' not in query:
                query += ' ORDER BY item_name ASC'
            
            logger.info(f"Executing items query with sort={sort}, direction={direction}, search={search}")
            
            # Execute the query using the provided session
            result = await session.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dictionaries
            items = []
            for row in rows:
                item_dict = {}
                for i, column in enumerate(columns):
                    item_dict[column] = row[i]
                items.append(item_dict)
            
            logger.info(f"Retrieved {len(items)} items")
            return items
            
        except Exception as e:
            logger.error(f"Error retrieving items: {str(e)}")
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
                'item_types': "SELECT DISTINCT item_type FROM square_item_library_export WHERE archived != 'Y' AND item_type IS NOT NULL ORDER BY item_type"
            }
            
            filter_options = {}
            
            for key, query in filter_queries.items():
                result = await session.execute(text(query))
                values = [row[0] for row in result.fetchall() if row[0]]
                filter_options[key] = sorted(set(values))
            
            return filter_options
            
        except Exception as e:
            logger.error(f"Error getting filter options: {str(e)}")
            return {} 