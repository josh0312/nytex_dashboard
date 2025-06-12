import aiohttp
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.config import Config
from app.logger import logger
from app.database.models.square_catalog_export import SquareItemLibraryExport


class SquareCatalogService:
    """Service for calling the external square_catalog_export service"""
    
    def __init__(self):
        # Configuration for the external square_catalog_export service
        base_url = getattr(Config, 'SQUARE_CATALOG_EXPORT_URL', 'http://localhost:5001')
        
        # Support multiple URLs for Docker environments
        if base_url == 'http://localhost:5001':
            # Default case - try Docker-aware URLs
            self.export_service_urls = [
                'http://host.docker.internal:5001',
                'http://localhost:5001'
            ]
        else:
            # Custom URL provided - use as-is
            self.export_service_urls = [base_url]
            
        self.timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout for export operations
        
    async def _make_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Dict[str, Any]:
        """Make a request to the external service, trying multiple URLs if needed"""
        last_error = None
        
        for base_url in self.export_service_urls:
            try:
                url = f"{base_url}/{endpoint.lstrip('/')}"
                logger.info(f"Trying {method} request to: {url}")
                
                async with aiohttp.ClientSession(timeout=self.timeout) as client_session:
                    if method.upper() == 'POST':
                        async with client_session.post(url, **kwargs) as response:
                            return await self._handle_response(response, url)
                    else:
                        async with client_session.get(url, **kwargs) as response:
                            return await self._handle_response(response, url)
                            
            except aiohttp.ClientConnectorError as e:
                logger.warning(f"Connection failed to {url}: {str(e)}")
                last_error = e
                continue
            except Exception as e:
                logger.error(f"Request failed to {url}: {str(e)}")
                last_error = e
                continue
        
        # If we get here, all URLs failed
        raise aiohttp.ClientError(f"All service URLs failed. Last error: {str(last_error)}")
    
    async def _handle_response(self, response, url: str) -> Dict[str, Any]:
        """Handle HTTP response from the external service"""
        if response.status == 200:
            result_data = await response.json()
            logger.info(f"Successful response from {url}")
            return {'success': True, 'data': result_data, 'status_code': response.status}
        else:
            error_text = await response.text()
            logger.error(f"Service at {url} returned status {response.status}: {error_text}")
            return {
                'success': False, 
                'error': f"Service returned status {response.status}: {error_text}",
                'status_code': response.status
            }
    
    async def export_catalog_to_database(self, session: AsyncSession) -> Dict[str, Any]:
        """Call the external square_catalog_export service to perform the export"""
        try:
            logger.info("Starting Square catalog export via external service")
            
            # Use the new helper method that tries multiple URLs
            response_data = await self._make_request('export', method='POST')
            
            if response_data['success']:
                result_data = response_data['data']
                
                # Check if the external service indicates the export is still running
                if result_data.get('status') == 'running':
                    logger.info(f"External export service started: {result_data}")
                    return {
                        'success': True,
                        'status': 'running',
                        'message': result_data.get('message', 'Export started'),
                        'export_time': datetime.now(timezone.utc).isoformat(),
                        'external_service_response': result_data,
                        'note': 'Export started via external square_catalog_export service - check logs for progress'
                    }
                else:
                    # Export completed
                    logger.info(f"External export service completed: {result_data}")
                    
                    # Get the updated count from our database to confirm
                    from sqlalchemy import text
                    count_result = await session.execute(text("SELECT COUNT(*) FROM square_item_library_export"))
                    total_items = count_result.scalar()
                    
                    return {
                        'success': True,
                        'status': 'completed',
                        'items_exported': total_items,
                        'export_time': datetime.now(timezone.utc).isoformat(),
                        'external_service_response': result_data,
                        'note': 'Export completed via external square_catalog_export service'
                    }
            else:
                logger.error(f"External export service failed: {response_data['error']}")
                return {
                    'success': False,
                    'error': response_data['error'],
                    'export_time': datetime.now(timezone.utc).isoformat()
                }
                        
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling external export service: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': f"Network error: {str(e)}",
                'export_time': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error during external catalog export: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'export_time': datetime.now(timezone.utc).isoformat()
            }
    
    async def check_export_status(self) -> Dict[str, Any]:
        """Check the status of the external export service"""
        try:
            # Use the new helper method that tries multiple URLs
            response_data = await self._make_request('status', method='GET')
            
            if response_data['success']:
                return {
                    'success': True,
                    'external_service_status': response_data['data']
                }
            else:
                return {
                    'success': False,
                    'error': response_data['error']
                }
                        
        except aiohttp.ClientError as e:
            return {
                'success': False,
                'error': f"Network error checking status: {str(e)}"
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Error checking export status: {str(e)}"
            }

    
    async def get_export_status(self, session: AsyncSession) -> Dict[str, Any]:
        """Get current export status and statistics"""
        try:
            # Get total count
            result = await session.execute(select(SquareItemLibraryExport))
            records = result.scalars().all()
            
            if not records:
                return {
                    'total_items': 0,
                    'last_export': None,
                    'has_data': False
                }
            
            # Get latest export date
            latest_record = max(records, key=lambda r: r.export_date)
            
            # Treat the database datetime as UTC and format it properly
            if latest_record.export_date:
                # Assume the database datetime is in UTC (since it's stored without timezone info)
                # Replace the timezone info to make it explicitly UTC
                utc_export_date = latest_record.export_date.replace(tzinfo=timezone.utc)
                last_export_iso = utc_export_date.isoformat()
            else:
                last_export_iso = None
            
            return {
                'total_items': len(records),
                'last_export': last_export_iso,
                'has_data': True
            }
            
        except Exception as e:
            logger.error(f"Error getting export status: {str(e)}")
            return {
                'total_items': 0,
                'last_export': None,
                'has_data': False,
                'error': str(e)
            } 