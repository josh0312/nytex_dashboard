from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.templates_config import templates
from app.logger import logger
import markdown
from pathlib import Path
import re
import yaml
from typing import Dict, List, Optional, Tuple
import os

router = APIRouter(tags=["help"])

def get_help_directory() -> Path:
    """Get the path to the help directory"""
    return Path(__file__).parent.parent / "static" / "help"

def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """Parse YAML frontmatter from markdown content"""
    if content.startswith('---'):
        try:
            # Split frontmatter and content
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                markdown_content = parts[2].strip()
                return frontmatter or {}, markdown_content
        except yaml.YAMLError:
            pass
    
    return {}, content

def discover_help_files() -> Dict[str, Dict]:
    """Automatically discover help files from the help directory"""
    help_dir = get_help_directory()
    help_structure = {}
    
    if not help_dir.exists():
        logger.warning(f"Help directory not found: {help_dir}")
        return help_structure
    
    # Find all .md files
    for md_file in help_dir.glob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse frontmatter
            frontmatter, markdown_content = parse_frontmatter(content)
            
            # Use filename as key (without extension)
            key = md_file.stem
            
            help_structure[key] = {
                "title": frontmatter.get("title", key.replace("-", " ").title()),
                "description": frontmatter.get("description", ""),
                "icon": frontmatter.get("icon", "help-circle"),
                "order": frontmatter.get("order", 999),
                "content": markdown_content,
                "filename": md_file.name
            }
            
        except Exception as e:
            logger.error(f"Error reading help file {md_file}: {str(e)}")
            continue
    
    # Sort by order, then by title
    help_structure = dict(sorted(
        help_structure.items(), 
        key=lambda x: (x[1].get("order", 999), x[1].get("title", ""))
    ))
    
    return help_structure

# Cross-reference mappings for user help - SAFE INTERNAL LINKS ONLY
HELP_CROSS_REFERENCES = {
    "Dashboard": "/help/dashboard",
    "Reports": "/help/reports", 
    "Catalog": "/help/catalog",
    "Items": "/help/items",
    "search": "/help/items",
    "inventory": "/help/items",
    "export": "/help/catalog",
    "getting started": "/help/getting-started"
}

def process_cross_references(html_content: str, current_topic: str = None) -> str:
    """Add automatic cross-reference links to help content"""
    for term, link in HELP_CROSS_REFERENCES.items():
        # Skip self-references (don't link "Dashboard" on the dashboard page)
        if current_topic and link.endswith(f"/{current_topic}"):
            continue
            
        # Simple replacement - just avoid replacing if already in a link
        # Check if term is not already part of a link by looking for <a...>term</a> pattern
        if f'>{term}<' not in html_content and f'>{term.lower()}<' not in html_content:
            pattern = rf'\b{re.escape(term)}\b'
            replacement = f'<a href="{link}" class="help-link text-blue-600 dark:text-blue-400 hover:underline">{term}</a>'
            html_content = re.sub(pattern, replacement, html_content, flags=re.IGNORECASE)
    
    return html_content

def convert_markdown_to_html(markdown_content: str, current_topic: str = None) -> tuple[str, str]:
    """Convert markdown to HTML with extensions"""
    md = markdown.Markdown(
        extensions=[
            'toc',          # Table of contents
            'tables',       # Table support
            'fenced_code',  # Fenced code blocks
        ],
        extension_configs={
            'toc': {
                'permalink': False,  # Disable paragraph symbols
                'anchorlink': False  # Disable anchor links completely
            }
        }
    )
    
    html = md.convert(markdown_content)
    
    # Add cross-reference links (but avoid self-references)
    html = process_cross_references(html, current_topic)
    
    return html, getattr(md, 'toc', '')

@router.get("/", response_class=HTMLResponse)
async def help_index(request: Request):
    """User help index page"""
    try:
        # Discover help files dynamically
        help_structure = discover_help_files()
        
        return templates.TemplateResponse("help/index.html", {
            "request": request,
            "title": "Help Center",
            "help_structure": help_structure,
            "breadcrumbs": [{"title": "Help", "url": "/help"}]
        })
    except Exception as e:
        logger.error(f"Error loading help index: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading help")

@router.get("/{help_topic}", response_class=HTMLResponse)
async def help_page(request: Request, help_topic: str):
    """Serve individual help pages"""
    try:
        # Discover help files dynamically
        help_structure = discover_help_files()
        
        # Find the help entry
        if help_topic not in help_structure:
            raise HTTPException(status_code=404, detail="Help topic not found")
        
        help_entry = help_structure[help_topic]
        
        # Convert markdown content to HTML
        html_content, toc = convert_markdown_to_html(help_entry['content'], help_topic)
        
        # Generate breadcrumbs
        breadcrumbs = [
            {"title": "Help", "url": "/help"},
            {"title": help_entry['title'], "url": f"/help/{help_topic}"}
        ]
        
        return templates.TemplateResponse("help/page.html", {
            "request": request,
            "title": f"{help_entry['title']} - Help",
            "page_title": help_entry['title'],
            "description": help_entry.get('description', ''),
            "content": html_content,
            "toc": toc,
            "breadcrumbs": breadcrumbs,
            "help_structure": help_structure
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading help page {help_topic}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading help page") 