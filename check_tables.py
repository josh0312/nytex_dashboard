import asyncio
import os
os.environ['SECRET_KEY'] = 'test'
from app.database.connection import get_db
from sqlalchemy import text

async def check_tables():
    async with get_db() as db:
        result = await db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('users', 'sessions')"))
        tables = result.fetchall()
        print('Found tables:', [row[0] for row in tables])

asyncio.run(check_tables()) 