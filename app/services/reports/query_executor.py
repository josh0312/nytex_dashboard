import os
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from app.database import async_session, get_session
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
            
            # Apply sorting if specified in params
            if params and 'sort_column' in params and 'sort_direction' in params:
                sort_column = params['sort_column']
                sort_direction = params['sort_direction']
                
                if sort_column in df.columns and sort_direction != 'none':
                    ascending = sort_direction.lower() == 'asc'
                    df = df.sort_values(by=sort_column, ascending=ascending)
            
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
    
    async def export_query_to_pdf(self, query_name: str, params: dict = None) -> str:
        """Execute a query and export results to PDF file."""
        df = await self.execute_query_to_df(query_name, params)
        
        # Create exports directory if it doesn't exist
        exports_dir = os.path.join('app', 'static', 'exports')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{query_name}_{timestamp}.pdf"
        filepath = os.path.join(exports_dir, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        # Add title
        report_title = query_name.replace('_', ' ').title()
        title = Paragraph(f"{report_title} Report", title_style)
        elements.append(title)
        
        # Add generation timestamp
        timestamp_text = f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
        timestamp_para = Paragraph(timestamp_text, styles['Normal'])
        elements.append(timestamp_para)
        elements.append(Spacer(1, 20))
        
        if not df.empty:
            # Convert DataFrame to list of lists for table
            data = [df.columns.tolist()]  # Header row
            data.extend(df.values.tolist())  # Data rows
            
            # Truncate long text in cells to prevent layout issues
            for i, row in enumerate(data):
                for j, cell in enumerate(row):
                    if isinstance(cell, str) and len(cell) > 50:
                        data[i][j] = cell[:47] + "..."
                    elif pd.isna(cell):
                        data[i][j] = ""
                    else:
                        data[i][j] = str(cell)
            
            # Create table
            table = Table(data)
            
            # Style the table
            table.setStyle(TableStyle([
                # Header row styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data rows styling
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(table)
        else:
            # No data message
            no_data_para = Paragraph("No data available for this report.", styles['Normal'])
            elements.append(no_data_para)
        
        # Add footer with record count
        elements.append(Spacer(1, 20))
        footer_text = f"Total Records: {len(df)}"
        footer_para = Paragraph(footer_text, styles['Normal'])
        elements.append(footer_para)
        
        # Build PDF
        doc.build(elements)
        
        return filename 