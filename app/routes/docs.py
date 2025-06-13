from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from app.logger import logger
import markdown
from pathlib import Path
import re
from typing import Dict, List

router = APIRouter(tags=["documentation"])

# Documentation structure
DOCS_STRUCTURE = {
    "overview": {
        "title": "System Overview",
        "file": "README.md",
        "description": "Complete overview of the NyTex Fireworks Dashboard system"
    },
    "pages": {
        "title": "Page Documentation",
        "children": {
            "dashboard": {
                "title": "Dashboard",
                "file": "DASHBOARD_PAGE.md",
                "description": "Main analytics and business intelligence hub"
            },
            "reports": {
                "title": "Reports",
                "file": "REPORTS_PAGE.md", 
                "description": "Comprehensive inventory and business reports"
            },
            "catalog": {
                "title": "Catalog Management",
                "file": "CATALOG_PAGE.md",
                "description": "Square catalog management and export system"
            },
            "items": {
                "title": "Items & Inventory",
                "file": "ITEMS_PAGE.md",
                "description": "Advanced inventory management and search"
            },
            "tools": {
                "title": "Administrative Tools",
                "file": "TOOLS_PAGE.md",
                "description": "Administrative utilities and system tools"
            },
            "admin": {
                "title": "System Administration",
                "file": "ADMIN_PAGE.md",
                "description": "System administration and data synchronization"
            }
        }
    },
    "technical": {
        "title": "Technical Documentation",
        "children": {
            "development": {
                "title": "Local Development",
                "file": "LOCAL_DEVELOPMENT.md",
                "description": "Setting up the development environment"
            },
            "docker": {
                "title": "Docker Guide",
                "file": "DOCKER_GUIDE.md",
                "description": "Complete Docker setup and workflow"
            },
            "deployment": {
                "title": "Deployment",
                "file": "DEPLOYMENT.md",
                "description": "Production deployment guide"
            },
            "authentication": {
                "title": "Authentication",
                "file": "AUTHENTICATION.md",
                "description": "O365 and manual authentication setup"
            },
            "secrets": {
                "title": "Secrets Management",
                "file": "SECRETS_GUIDE.md",
                "description": "Google Secret Manager integration"
            },
            "troubleshooting": {
                "title": "Troubleshooting",
                "file": "TROUBLESHOOTING.md",
                "description": "Common issues and solutions"
            },
            "historical-sync": {
                "title": "Historical Orders Sync",
                "file": "HISTORICAL_ORDERS_SYNC.md",
                "description": "Detailed historical data synchronization"
            }
        }
    }
}

# Cross-reference mappings for auto-linking
CROSS_REFERENCES = {
    "Dashboard": "/docs/pages/dashboard",
    "Reports": "/docs/pages/reports", 
    "Catalog": "/docs/pages/catalog",
    "Items": "/docs/pages/items",
    "Tools": "/docs/pages/tools",
    "Admin": "/docs/pages/admin",
    "Square API": "/docs/technical/authentication",
    "Square POS": "/docs/technical/authentication",
    "database": "/docs/technical/development",
    "Docker": "/docs/technical/docker",
    "HTMX": "/docs/pages/dashboard",
    "authentication": "/docs/technical/authentication",
    "sync": "/docs/pages/admin",
    "synchronization": "/docs/pages/admin",
    "export": "/docs/pages/catalog",
    "inventory": "/docs/pages/items",
    "PostgreSQL": "/docs/technical/development"
}

def get_docs_path() -> Path:
    """Get the path to the docs directory"""
    return Path(__file__).parent.parent.parent / "docs"

def read_markdown_file(filename: str) -> str:
    """Read a markdown file from the docs directory"""
    docs_path = get_docs_path()
    file_path = docs_path / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Documentation file not found: {filename}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading documentation file {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reading documentation file")

def process_cross_references(html_content: str) -> str:
    """Add automatic cross-reference links to documentation"""
    for term, link in CROSS_REFERENCES.items():
        # Create a regex pattern that matches the term but not if it's already in a link
        pattern = rf'(?<!<a[^>]*>)(?<!href="[^"]*")\b{re.escape(term)}\b(?![^<]*</a>)'
        replacement = f'<a href="{link}" class="doc-link">{term}</a>'
        html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
    
    return html_content

def convert_markdown_to_html(markdown_content: str) -> tuple[str, str]:
    """Convert markdown to HTML with extensions"""
    md = markdown.Markdown(
        extensions=[
            'toc',          # Table of contents
            'codehilite',   # Code highlighting  
            'tables',       # Table support
            'fenced_code',  # Fenced code blocks
            'attr_list'     # Attribute lists
        ],
        extension_configs={
            'toc': {
                'permalink': True,
                'permalink_class': 'anchor-link',
                'permalink_title': 'Link to this section'
            },
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': False  # Use CSS classes instead
            }
        }
    )
    
    html = md.convert(markdown_content)
    
    # Add cross-reference links
    html = process_cross_references(html)
    
    return html, getattr(md, 'toc', '')

def find_doc_by_path(path_parts: List[str]) -> Dict:
    """Find documentation entry by URL path parts"""
    current = DOCS_STRUCTURE
    
    for part in path_parts:
        if part in current:
            current = current[part]
        elif 'children' in current and part in current['children']:
            current = current['children'][part]
        else:
            return None
    
    return current

def get_breadcrumbs(path_parts: List[str]) -> List[Dict]:
    """Generate breadcrumb navigation"""
    breadcrumbs = [{"title": "Documentation", "url": "/docs"}]
    
    current_path = "/docs"
    current = DOCS_STRUCTURE
    
    for i, part in enumerate(path_parts):
        current_path += f"/{part}"
        
        if part in current:
            breadcrumbs.append({
                "title": current[part]["title"],
                "url": current_path
            })
            current = current[part]
        elif 'children' in current and part in current['children']:
            breadcrumbs.append({
                "title": current['children'][part]["title"], 
                "url": current_path
            })
            current = current['children'][part]
    
    return breadcrumbs

@router.get("/", response_class=HTMLResponse)
async def docs_index(request: Request):
    """Documentation index page"""
    try:
        # Read the main README for overview
        readme_content = read_markdown_file("README.md")
        overview_html, toc = convert_markdown_to_html(readme_content)
        
        return templates.TemplateResponse("docs/index.html", {
            "request": request,
            "title": "Documentation",
            "docs_structure": DOCS_STRUCTURE,
            "overview_html": overview_html,
            "toc": toc,
            "breadcrumbs": [{"title": "Documentation", "url": "/docs"}]
        })
    except Exception as e:
        logger.error(f"Error loading documentation index: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading documentation")

@router.get("/{path:path}", response_class=HTMLResponse)
async def docs_page(request: Request, path: str):
    """Serve individual documentation pages"""
    try:
        # Parse the path
        path_parts = [p for p in path.split('/') if p]
        
        if not path_parts:
            # Redirect to index
            return templates.TemplateResponse("docs/index.html", {
                "request": request,
                "title": "Documentation",
                "docs_structure": DOCS_STRUCTURE
            })
        
        # Find the documentation entry
        doc_entry = find_doc_by_path(path_parts)
        
        if not doc_entry or 'file' not in doc_entry:
            raise HTTPException(status_code=404, detail="Documentation page not found")
        
        # Read and convert the markdown file
        markdown_content = read_markdown_file(doc_entry['file'])
        html_content, toc = convert_markdown_to_html(markdown_content)
        
        # Generate breadcrumbs
        breadcrumbs = get_breadcrumbs(path_parts)
        
        return templates.TemplateResponse("docs/page.html", {
            "request": request,
            "title": f"{doc_entry['title']} - Documentation",
            "page_title": doc_entry['title'],
            "description": doc_entry.get('description', ''),
            "content": html_content,
            "toc": toc,
            "breadcrumbs": breadcrumbs,
            "docs_structure": DOCS_STRUCTURE
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading documentation page {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading documentation page") 