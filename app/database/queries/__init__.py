from pathlib import Path
import logging

logger = logging.getLogger(__name__)

async def get_query_text(query_name: str) -> str:
    """
    Read SQL query from file.
    Args:
        query_name: Name of the SQL file (e.g., 'missing_sku_inventory.sql')
    Returns:
        str: SQL query text
    """
    try:
        query_path = Path("app/database/queries") / query_name
        logger.info(f"Reading query from {query_path}")
        
        if not query_path.exists():
            raise FileNotFoundError(f"Query file not found: {query_path}")
            
        with open(query_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading query file {query_name}: {str(e)}")
        raise 