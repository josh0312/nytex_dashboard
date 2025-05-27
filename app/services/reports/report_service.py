from typing import List, Dict, Any
import pandas as pd
from fastapi import HTTPException
from fastapi.responses import FileResponse
import tempfile
import os
from datetime import datetime
from pathlib import Path

class ReportService:
    @staticmethod
    async def export_to_excel(data: List[Dict[Any, Any]], filename: str) -> FileResponse:
        """Export data to Excel file"""
        try:
            # Create exports directory if it doesn't exist
            exports_dir = Path("app/static/exports")
            exports_dir.mkdir(parents=True, exist_ok=True)

            # Create DataFrame and export to Excel
            df = pd.DataFrame(data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = exports_dir / f"{filename}_{timestamp}.xlsx"
            
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            return FileResponse(
                path=file_path,
                filename=file_path.name,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")

    @staticmethod
    async def generate_print_view(data: List[Dict[Any, Any]], template_name: str) -> str:
        """Generate print-friendly HTML view"""
        # This will be rendered by the template with print-specific styles
        return data

    @staticmethod
    async def email_report(data: List[Dict[Any, Any]], recipient: str, subject: str) -> Dict[str, str]:
        """Email report to specified recipient"""
        try:
            # TODO: Implement email sending logic
            # For now, return success message
            return {"message": "Report email scheduled for delivery"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    @staticmethod
    def cleanup_old_exports(max_age_hours: int = 24):
        """Clean up export files older than specified hours"""
        try:
            exports_dir = Path("app/static/exports")
            if not exports_dir.exists():
                return

            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_hours * 3600

            for file in exports_dir.glob("*.xlsx"):
                if (current_time - file.stat().st_mtime) > max_age_seconds:
                    file.unlink()
        except Exception as e:
            # Log error but don't raise exception
            print(f"Failed to cleanup exports: {str(e)}") 