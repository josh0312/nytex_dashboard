from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.services.reports.query_executor import QueryExecutor

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/export/{query_name}")
async def export_report(query_name: str):
    """Export a report query to Excel."""
    try:
        executor = QueryExecutor()
        filename = await executor.export_query_to_excel(query_name)
        
        # Get the full path to the exported file
        exports_dir = os.path.join('app', 'static', 'exports')
        file_path = os.path.join(exports_dir, filename)
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}") 