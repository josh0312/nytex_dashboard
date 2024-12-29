import asyncio
import asyncpg
from datetime import datetime, date
import logging
import pytest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_seasonal_sales_query():
    # Connect to the database
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/square_data_sync')
    
    # Test parameters
    start_date = date(2024, 12, 20)
    end_date = date(2025, 1, 1)
    
    try:
        # First, let's check orders by day
        daily_orders_query = """
            SELECT 
                date(o.created_at AT TIME ZONE 'America/Chicago') as sale_date,
                COUNT(*) as order_count,
                sum((p.amount_money->>'amount')::integer)/100.0 as total
            FROM orders o 
            JOIN payments p ON o.id = p.order_id 
            WHERE o.created_at >= $1::date AT TIME ZONE 'America/Chicago'
            AND o.created_at < ($2::date + interval '1 day') AT TIME ZONE 'America/Chicago'
            AND p.status = $3
            GROUP BY date(o.created_at AT TIME ZONE 'America/Chicago')
            ORDER BY sale_date;
        """
        
        orders = await conn.fetch(daily_orders_query, start_date, end_date, 'COMPLETED')
        logger.info("Daily Order Counts:")
        total_orders = 0
        total_sales = 0
        for day in orders:
            logger.info(f"Date: {day['sale_date']}, Orders: {day['order_count']}, Total: ${day['total']:.2f}")
            total_orders += day['order_count']
            total_sales += day['total']
        
        logger.info(f"\nTotal Orders in Period: {total_orders}")
        logger.info(f"Total Sales in Period: ${total_sales:.2f}")
        
        # Now test the full query with dates filled in
        query = """
            WITH dates AS (
                SELECT generate_series($1::date, $2::date, '1 day'::interval)::date AS date
            ),
            daily_sales AS (
                SELECT 
                    date(o.created_at AT TIME ZONE 'America/Chicago') as sale_date, 
                    COUNT(*) as order_count,
                    sum((p.amount_money->>'amount')::integer) as total
                FROM orders o
                JOIN payments p ON o.id = p.order_id
                WHERE o.created_at >= $1::date AT TIME ZONE 'America/Chicago'
                AND o.created_at < ($2::date + interval '1 day') AT TIME ZONE 'America/Chicago'
                AND p.status = $3
                GROUP BY date(o.created_at AT TIME ZONE 'America/Chicago')
            )
            SELECT 
                d.date,
                COALESCE(s.order_count, 0) as order_count,
                COALESCE(s.total, 0) as total
            FROM dates d
            LEFT JOIN daily_sales s ON d.date = s.sale_date
            ORDER BY d.date;
        """
        
        # Execute the query
        rows = await conn.fetch(query, start_date, end_date, 'COMPLETED')
        
        # Print results
        logger.info("\nFull Date Range (including zero days):")
        total_with_zeros = 0
        orders_with_zeros = 0
        for row in rows:
            logger.info(f"Date: {row['date']}, Orders: {row['order_count']}, Total: ${float(row['total'])/100:.2f}")
            total_with_zeros += float(row['total'])/100
            orders_with_zeros += row['order_count']
            
        logger.info(f"\nTotals including zero days:")
        logger.info(f"Total Orders: {orders_with_zeros}")
        logger.info(f"Total Sales: ${total_with_zeros:.2f}")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(test_seasonal_sales_query()) 