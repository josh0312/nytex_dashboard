from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.logger import logger
from app.utils.timezone import get_central_now, convert_utc_to_central
from app.database.models.operating_season import OperatingSeason
from sqlalchemy import select


class DailySalesService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_daily_sales_report(self, report_date: date = None, location_id: str = None) -> Dict[str, Any]:
        """
        Get comprehensive daily sales report data.
        
        Args:
            report_date: Date to report on (defaults to today in Central Time)
            location_id: Specific location (None for all locations)
        """
        if report_date is None:
            report_date = get_central_now().date()
        
        try:
            # Get current season information
            current_season = await self._get_current_season(report_date)
            
            # Get basic daily metrics
            today_performance = await self._get_today_performance(report_date, location_id)
            
            # Get comparison metrics
            comparisons = await self._get_comparison_metrics(report_date, location_id, current_season)
            
            # Get best performers
            best_performers = await self._get_best_performers(report_date, location_id)
            
            # Get worst performers (unsold items this season)
            worst_performers = await self._get_unsold_items_this_season(current_season, location_id)
            
            # Get operational insights
            operational_insights = await self._get_operational_insights(report_date, location_id)
            
            # Get hourly breakdown
            hourly_breakdown = await self._get_hourly_breakdown(report_date, location_id)
            
            return {
                "report_date": report_date,
                "current_season": current_season,
                "today_performance": today_performance,
                "comparisons": comparisons,
                "best_performers": best_performers,
                "worst_performers": worst_performers,
                "operational_insights": operational_insights,
                "hourly_breakdown": hourly_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error generating daily sales report: {str(e)}")
            return self._get_empty_report_data(report_date)

    async def _get_current_season(self, report_date: date) -> Optional[Dict[str, Any]]:
        """Get current operating season information"""
        try:
            query = select(OperatingSeason).where(
                OperatingSeason.start_date <= report_date,
                OperatingSeason.end_date >= report_date
            )
            result = await self.session.execute(query)
            season = result.scalar_one_or_none()
            
            if season:
                # Calculate days into season
                days_into_season = (report_date - season.start_date).days + 1
                total_season_days = (season.end_date - season.start_date).days + 1
                
                return {
                    "id": season.id,
                    "name": season.name,
                    "start_date": season.start_date,
                    "end_date": season.end_date,
                    "days_into_season": days_into_season,
                    "total_season_days": total_season_days
                }
            return None
        except Exception as e:
            logger.error(f"Error getting current season: {str(e)}")
            return None

    async def _get_today_performance(self, report_date: date, location_id: str = None) -> Dict[str, Any]:
        """Get today's performance metrics"""
        try:
            location_filter = ""
            if location_id:
                location_filter = "AND o.location_id = :location_id"
            
            query = text(f"""
                SELECT 
                    COUNT(DISTINCT o.id) as transaction_count,
                    COALESCE(SUM((o.total_money->>'amount')::numeric / 100), 0) as total_revenue,
                    COALESCE(SUM(oli.quantity::numeric), 0) as units_sold
                FROM orders o
                LEFT JOIN order_line_items oli ON o.id = oli.order_id
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                AND o.state = 'COMPLETED'
                {location_filter}
            """)
            
            params = {"report_date": report_date}
            if location_id:
                params["location_id"] = location_id
                
            result = await self.session.execute(query, params)
            row = result.fetchone()
            
            if row:
                transaction_count = row[0] or 0
                total_revenue = float(row[1] or 0)
                units_sold = float(row[2] or 0)
                avg_order_value = total_revenue / transaction_count if transaction_count > 0 else 0
                
                return {
                    "total_revenue": total_revenue,
                    "transaction_count": transaction_count,
                    "avg_order_value": avg_order_value,
                    "units_sold": units_sold
                }
            
            return {"total_revenue": 0, "transaction_count": 0, "avg_order_value": 0, "units_sold": 0}
            
        except Exception as e:
            logger.error(f"Error getting today's performance: {str(e)}")
            return {"total_revenue": 0, "transaction_count": 0, "avg_order_value": 0, "units_sold": 0}

    async def _get_comparison_metrics(self, report_date: date, location_id: str = None, current_season: dict = None) -> Dict[str, Any]:
        """Get comparison metrics vs yesterday and same day last year"""
        try:
            yesterday = report_date - timedelta(days=1)
            same_day_last_year = report_date.replace(year=report_date.year - 1)
            
            location_filter = ""
            if location_id:
                location_filter = "AND o.location_id = :location_id"
            
            # Yesterday's performance
            yesterday_query = text(f"""
                SELECT 
                    COALESCE(SUM((o.total_money->>'amount')::numeric / 100), 0) as total_revenue,
                    COUNT(DISTINCT o.id) as transaction_count
                FROM orders o
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :yesterday
                AND o.state = 'COMPLETED'
                {location_filter}
            """)
            
            params_yesterday = {"yesterday": yesterday}
            if location_id:
                params_yesterday["location_id"] = location_id
                
            result = await self.session.execute(yesterday_query, params_yesterday)
            yesterday_row = result.fetchone()
            yesterday_revenue = float(yesterday_row[0] or 0) if yesterday_row else 0
            yesterday_transactions = yesterday_row[1] or 0 if yesterday_row else 0
            
            # Same day last year performance  
            last_year_query = text(f"""
                SELECT 
                    COALESCE(SUM((o.total_money->>'amount')::numeric / 100), 0) as total_revenue,
                    COUNT(DISTINCT o.id) as transaction_count
                FROM orders o
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :same_day_last_year
                AND o.state = 'COMPLETED'
                {location_filter}
            """)
            
            params_last_year = {"same_day_last_year": same_day_last_year}
            if location_id:
                params_last_year["location_id"] = location_id
                
            result = await self.session.execute(last_year_query, params_last_year)
            last_year_row = result.fetchone()
            last_year_revenue = float(last_year_row[0] or 0) if last_year_row else 0
            last_year_transactions = last_year_row[1] or 0 if last_year_row else 0
            
            return {
                "yesterday_revenue": yesterday_revenue,
                "yesterday_transactions": yesterday_transactions,
                "last_year_revenue": last_year_revenue,
                "last_year_transactions": last_year_transactions
            }
            
        except Exception as e:
            logger.error(f"Error getting comparison metrics: {str(e)}")
            return {
                "yesterday_revenue": 0,
                "yesterday_transactions": 0,
                "last_year_revenue": 0,
                "last_year_transactions": 0
            }

    async def _get_best_performers(self, report_date: date, location_id: str = None) -> Dict[str, Any]:
        """Get top performing items and locations for today"""
        try:
            location_filter = ""
            if location_id:
                location_filter = "AND o.location_id = :location_id"
            
            # Top selling items today
            items_query = text(f"""
                SELECT 
                    oli.name,
                    oli.sku,
                    SUM(oli.quantity::numeric) as total_quantity,
                    SUM((oli.total_money->>'amount')::numeric / 100) as total_revenue
                FROM orders o
                JOIN order_line_items oli ON o.id = oli.order_id
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                AND o.state = 'COMPLETED'
                {location_filter}
                GROUP BY oli.name, oli.sku
                ORDER BY total_quantity DESC
                LIMIT 5
            """)
            
            params = {"report_date": report_date}
            if location_id:
                params["location_id"] = location_id
                
            result = await self.session.execute(items_query, params)
            top_items = []
            for row in result.fetchall():
                top_items.append({
                    "name": row[0],
                    "sku": row[1],
                    "quantity_sold": float(row[2] or 0),
                    "revenue": float(row[3] or 0)
                })
            
            # Top performing locations (only if viewing all locations)
            top_locations = []
            if not location_id:
                locations_query = text("""
                    SELECT 
                        l.name,
                        l.id,
                        COUNT(DISTINCT o.id) as transaction_count,
                        SUM((o.total_money->>'amount')::numeric / 100) as total_revenue
                    FROM orders o
                    JOIN locations l ON o.location_id = l.id
                    WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                    AND o.state = 'COMPLETED'
                    GROUP BY l.name, l.id
                    ORDER BY total_revenue DESC
                """)
                
                result = await self.session.execute(locations_query, {"report_date": report_date})
                for row in result.fetchall():
                    top_locations.append({
                        "name": row[0],
                        "id": row[1],
                        "transaction_count": row[2] or 0,
                        "revenue": float(row[3] or 0)
                    })
            
            return {
                "top_items": top_items,
                "top_locations": top_locations
            }
            
        except Exception as e:
            logger.error(f"Error getting best performers: {str(e)}")
            return {"top_items": [], "top_locations": []}

    async def _get_unsold_items_this_season(self, current_season: dict = None, location_id: str = None) -> List[Dict[str, Any]]:
        """Get items that haven't sold this season"""
        try:
            if not current_season:
                return []
            
            location_filter = ""
            location_join = ""
            
            # Build location filter for items_view based on specific location
            if location_id:
                location_map = {
                    "aubrey": "aubrey_qty > 0",
                    "bridgefarmer": "bridgefarmer_qty > 0", 
                    "building": "building_qty > 0",
                    "flomo": "flomo_qty > 0",
                    "justin": "justin_qty > 0",
                    "quinlan": "quinlan_qty > 0",
                    "terrell": "terrell_qty > 0"
                }
                location_filter = f"AND {location_map.get(location_id, 'total_qty > 0')}"
                location_join = "AND o.location_id = :location_id"
            
            query = text(f"""
                SELECT 
                    iv.item_name,
                    iv.sku,
                    iv.category,
                    iv.vendor_name,
                    iv.total_qty as current_inventory
                FROM items_view iv
                WHERE iv.sellable = 'Y'
                AND iv.total_qty > 0
                {location_filter}
                AND NOT EXISTS (
                    SELECT 1 
                    FROM orders o
                    JOIN order_line_items oli ON o.id = oli.order_id
                    WHERE oli.sku = iv.sku
                    AND DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') 
                        BETWEEN :season_start AND :season_end
                    AND o.state = 'COMPLETED'
                    {location_join}
                )
                ORDER BY iv.total_qty DESC
                LIMIT 20
            """)
            
            params = {
                "season_start": current_season["start_date"],
                "season_end": current_season["end_date"]
            }
            if location_id:
                params["location_id"] = location_id
            
            result = await self.session.execute(query, params)
            unsold_items = []
            for row in result.fetchall():
                unsold_items.append({
                    "name": row[0],
                    "sku": row[1],
                    "category": row[2],
                    "vendor_name": row[3],
                    "current_inventory": row[4] or 0
                })
            
            return unsold_items
            
        except Exception as e:
            logger.error(f"Error getting unsold items: {str(e)}")
            return []

    async def _get_operational_insights(self, report_date: date, location_id: str = None) -> Dict[str, Any]:
        """Get operational insights like payment methods, peak hours, etc."""
        try:
            location_filter = ""
            if location_id:
                location_filter = "AND o.location_id = :location_id"
            
            # Payment method breakdown
            payment_query = text(f"""
                SELECT 
                    t.type as payment_method,
                    COUNT(*) as transaction_count,
                    SUM((t.amount_money->>'amount')::numeric / 100) as total_amount
                FROM orders o
                JOIN tenders t ON o.id = t.order_id
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                AND o.state = 'COMPLETED'
                {location_filter}
                GROUP BY t.type
                ORDER BY total_amount DESC
            """)
            
            params = {"report_date": report_date}
            if location_id:
                params["location_id"] = location_id
            
            result = await self.session.execute(payment_query, params)
            payment_methods = []
            for row in result.fetchall():
                payment_methods.append({
                    "method": row[0],
                    "transaction_count": row[1],
                    "total_amount": float(row[2] or 0)
                })
            
            # Peak hour analysis
            peak_hour_query = text(f"""
                SELECT 
                    EXTRACT(HOUR FROM o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') as hour,
                    COUNT(*) as transaction_count,
                    SUM((o.total_money->>'amount')::numeric / 100) as total_revenue
                FROM orders o
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                AND o.state = 'COMPLETED'
                {location_filter}
                GROUP BY EXTRACT(HOUR FROM o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')
                ORDER BY total_revenue DESC
                LIMIT 1
            """)
            
            result = await self.session.execute(peak_hour_query, params)
            peak_hour_row = result.fetchone()
            peak_hour_info = None
            if peak_hour_row:
                peak_hour_info = {
                    "hour": int(peak_hour_row[0]),
                    "transaction_count": peak_hour_row[1],
                    "revenue": float(peak_hour_row[2] or 0)
                }
            
            return {
                "payment_methods": payment_methods,
                "peak_hour": peak_hour_info
            }
            
        except Exception as e:
            logger.error(f"Error getting operational insights: {str(e)}")
            return {"payment_methods": [], "peak_hour": None}

    async def _get_hourly_breakdown(self, report_date: date, location_id: str = None) -> List[Dict[str, Any]]:
        """Get hourly sales breakdown for charting"""
        try:
            location_filter = ""
            if location_id:
                location_filter = "AND o.location_id = :location_id"
            
            query = text(f"""
                SELECT 
                    EXTRACT(HOUR FROM o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') as hour,
                    COUNT(*) as transaction_count,
                    SUM((o.total_money->>'amount')::numeric / 100) as total_revenue
                FROM orders o
                WHERE DATE(o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago') = :report_date
                AND o.state = 'COMPLETED'
                {location_filter}
                GROUP BY EXTRACT(HOUR FROM o.created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Chicago')
                ORDER BY hour
            """)
            
            params = {"report_date": report_date}
            if location_id:
                params["location_id"] = location_id
            
            result = await self.session.execute(query, params)
            
            # Initialize all hours with 0
            hourly_data = [{"hour": h, "revenue": 0, "transactions": 0} for h in range(24)]
            
            # Fill in actual data
            for row in result.fetchall():
                hour = int(row[0])
                hourly_data[hour] = {
                    "hour": hour,
                    "revenue": float(row[2] or 0),
                    "transactions": row[1] or 0
                }
            
            return hourly_data
            
        except Exception as e:
            logger.error(f"Error getting hourly breakdown: {str(e)}")
            return []

    def _get_empty_report_data(self, report_date: date) -> Dict[str, Any]:
        """Return empty report structure when there's an error"""
        return {
            "report_date": report_date,
            "current_season": None,
            "today_performance": {"total_revenue": 0, "transaction_count": 0, "avg_order_value": 0, "units_sold": 0},
            "comparisons": {"yesterday_revenue": 0, "yesterday_transactions": 0, "last_year_revenue": 0, "last_year_transactions": 0},
            "best_performers": {"top_items": [], "top_locations": []},
            "worst_performers": [],
            "operational_insights": {"payment_methods": [], "peak_hour": None},
            "hourly_breakdown": []
        }

    async def get_available_locations(self) -> List[Dict[str, str]]:
        """Get list of all available locations for the dropdown."""
        try:
            query = text("""
                SELECT id, name
                FROM locations
                ORDER BY name
            """)
            
            result = await self.session.execute(query)
            locations = []
            for row in result.fetchall():
                locations.append({
                    "id": row[0],
                    "name": row[1]
                })
            
            return locations
            
        except Exception as e:
            logger.error(f"Error getting available locations: {str(e)}")
            return [] 