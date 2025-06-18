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
            where_conditions = ["sile.archived != 'Y'"]
            
            # Add global search if provided
            if search and search.strip():
                # Escape single quotes in search term
                escaped_search = search.replace("'", "''")
                search_condition = f"""
                (LOWER(sile.item_name) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sile.sku, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sile.description, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sile.categories, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sile.default_vendor_name, '')) LIKE LOWER('%{escaped_search}%') OR
                 LOWER(COALESCE(sile.default_vendor_code, '')) LIKE LOWER('%{escaped_search}%'))
                """
                where_conditions.append(search_condition)
            
            # Add column-specific filters if provided
            if filters:
                for column, value in filters.items():
                    if value and value != '' and value != []:
                        # Handle both single values (strings) and multi-select values (arrays)
                        if isinstance(value, list) and len(value) > 0:
                            # Filter out empty values from the array
                            non_empty_values = [item for item in value if item and str(item).strip()]
                            if non_empty_values:
                                # Map display column names to actual column names with proper table aliases
                                column_mapping = {
                                    'item_name': 'sile.item_name',
                                    'sku': 'sile.sku',
                                    'description': 'sile.description',
                                    'category': 'sile.categories',
                                    'vendor_name': 'sile.default_vendor_name',
                                    'vendor_code': 'sile.default_vendor_code',
                                    'price': 'sile.price',
                                    'cost': 'sile.default_unit_cost'
                                }
                                
                                actual_column = column_mapping.get(column, f'sile.{column}')
                                
                                # Handle numeric fields (price/cost) vs text fields differently
                                if column in ['price', 'cost']:
                                    # For numeric fields, use exact value matching with IN clause
                                    numeric_values = []
                                    for val in non_empty_values:
                                        try:
                                            numeric_values.append(float(val))
                                        except (ValueError, TypeError):
                                            continue
                                    
                                    if numeric_values:
                                        # Create IN clause for exact numeric matches
                                        values_str = ','.join([str(v) for v in numeric_values])
                                        filter_condition = f"{actual_column} IN ({values_str})"
                                        where_conditions.append(filter_condition)
                                elif column == 'category':
                                    # For category, use exact matching (not partial LIKE matching)
                                    escaped_values = [str(item).replace("'", "''") for item in non_empty_values]
                                    or_conditions = [f"LOWER(COALESCE({actual_column}, '')) = LOWER('{val}')" for val in escaped_values]
                                    filter_condition = f"({' OR '.join(or_conditions)})"
                                    where_conditions.append(filter_condition)
                                else:
                                    # For other text fields, use LIKE for partial matching
                                    escaped_values = [str(item).replace("'", "''") for item in non_empty_values]
                                    or_conditions = [f"LOWER(COALESCE({actual_column}, '')) LIKE LOWER('%{val}%')" for val in escaped_values]
                                    filter_condition = f"({' OR '.join(or_conditions)})"
                                    where_conditions.append(filter_condition)
                        elif isinstance(value, str) and value.strip():
                            # Single value: handle numeric vs text filters differently
                            escaped_value = value.replace("'", "''").strip()
                            
                            # Map display column names to actual column names with proper table aliases
                            column_mapping = {
                                'item_name': 'sile.item_name',
                                'sku': 'sile.sku',
                                'description': 'sile.description',
                                'category': 'sile.categories',
                                'vendor_name': 'sile.default_vendor_name',
                                'vendor_code': 'sile.default_vendor_code',
                                'price': 'sile.price',
                                'cost': 'sile.default_unit_cost'
                            }
                            
                            actual_column = column_mapping.get(column, f'sile.{column}')
                            
                            # Handle numeric fields differently
                            if column in ['price', 'cost']:
                                # For numeric fields, use >= comparison and validate the input
                                try:
                                    numeric_value = float(escaped_value)
                                    # Only add filter if value is >= 0 (negative prices/costs don't make sense)
                                    if numeric_value >= 0:
                                        filter_condition = f"{actual_column} >= {numeric_value}"
                                        where_conditions.append(filter_condition)
                                except ValueError:
                                    # If not a valid number, skip this filter
                                    logger.warning(f"Invalid numeric value for {column}: {escaped_value}")
                                    continue
                            elif column == 'category':
                                # For category, use exact matching (not partial LIKE matching)
                                if escaped_value:
                                    filter_condition = f"LOWER(COALESCE({actual_column}, '')) = LOWER('{escaped_value}')"
                                    where_conditions.append(filter_condition)
                            else:
                                # For other text fields, use LIKE for partial matching
                                if escaped_value:
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
                # Map display column names to query column aliases with proper table qualification
                sort_mapping = {
                    'item_name': 'sile.item_name',
                    'sku': 'sile.sku',
                    'description': 'sile.description',
                    'category': 'category',  # This is aliased in SELECT
                    'price': 'price',        # This is aliased in SELECT
                    'vendor_name': 'vendor_name',  # This is aliased in SELECT
                    'vendor_code': 'vendor_code',  # This is aliased in SELECT
                    'profit_margin_percent': 'profit_margin_percent',  # This is aliased in SELECT
                    'profit_markup_percent': 'profit_markup_percent',  # This is aliased in SELECT
                    'total_qty': 'total_qty',      # This is aliased in SELECT
                    'aubrey_qty': 'aubrey_qty',    # This is aliased in SELECT
                    'bridgefarmer_qty': 'bridgefarmer_qty',  # This is aliased in SELECT
                    'building_qty': 'building_qty',  # This is aliased in SELECT
                    'flomo_qty': 'flomo_qty',      # This is aliased in SELECT
                    'justin_qty': 'justin_qty',    # This is aliased in SELECT
                    'quinlan_qty': 'quinlan_qty',  # This is aliased in SELECT
                    'terrell_qty': 'terrell_qty',  # This is aliased in SELECT
                    'item_type': 'sile.item_type',
                    'cost': 'cost'  # This is aliased in SELECT
                }
                
                actual_sort_column = sort_mapping.get(sort, 'sile.item_name')
                
                # Remove existing ORDER BY and add new one
                if 'ORDER BY' in query:
                    query = query.split('ORDER BY')[0]
                
                query += f' ORDER BY {actual_sort_column} {direction.upper()}'
            elif 'ORDER BY' not in query:
                query += ' ORDER BY sile.item_name ASC'
            
            logger.info(f"Executing items query with sort={sort}, direction={direction}, search={search}")
            
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