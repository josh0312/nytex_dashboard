import pytest
import asyncio
from app import app_context
from app.database import db
from sqlalchemy import text

@pytest.mark.asyncio
async def test_database_connection():
    """Test that we can connect to the database"""
    with app_context() as app:
        # Add your database connection test logic here
        pass

if __name__ == "__main__":
    asyncio.run(test_database_connection()) 