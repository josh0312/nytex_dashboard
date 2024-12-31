import os
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from app.database import async_session, get_session

class QueryExecutor:
    def __init__(self):
        self.queries_dir = os.path.join('app', 'database', 'queries')
    
    def _read_query(self, query_name: str) -> str:
        """Read a query from the queries directory."""
        query_path = os.path.join(self.queries_dir, f"{query_name}.sql")
        with open(query_path, 'r') as f:
            return f.read()
    
    async def execute_query_to_df(self, query_name: str, params: dict = None) -> pd.DataFrame:
        """Execute a query and return results as a pandas DataFrame."""
        query = self._read_query(query_name)
        async with get_session() as session:
            result = await session.execute(text(query), params or {})
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=result.keys())
            return df
    
    async def export_query_to_excel(self, query_name: str, params: dict = None) -> str:
        """Execute a query and export results to Excel file."""
        df = await self.execute_query_to_df(query_name, params)
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join('app', 'static', 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{query_name}_{timestamp}.xlsx"
        filepath = os.path.join(exports_dir, filename)
        
        # Export to Excel
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        return filename 