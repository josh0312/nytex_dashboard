# 📚 Integrated Documentation System

## Overview

The NyTex Fireworks Dashboard now includes a comprehensive, integrated documentation system that serves as a wiki-style knowledge base accessible directly from the web interface.

## Features

### 🌐 Web-Based Documentation
- **Accessible from `/docs`** - Full documentation browsable through the web interface
- **No external tools needed** - Users can access documentation without leaving the application
- **Responsive design** - Works seamlessly on desktop and mobile devices

### 🔗 Automatic Cross-Linking
- **Intelligent linking** - Key terms are automatically converted to clickable links
- **Cross-references** - Navigate between related documentation sections easily
- **Contextual navigation** - Breadcrumbs and sidebar navigation for easy browsing

### 📝 Markdown Processing
- **Rich formatting** - Full Markdown support with extensions
- **Code highlighting** - Syntax highlighting for code blocks
- **Table of contents** - Automatic generation for long documents
- **Tables and lists** - Properly formatted data presentation

### 🎯 Contextual Help
- **Help links** - Contextual help icons throughout the interface
- **Floating help button** - Global access to documentation from any page
- **Page-specific help** - Direct links to relevant documentation sections

## Documentation Structure

```
/docs/
├── overview                    # System overview (README.md)
├── pages/
│   ├── dashboard              # Dashboard documentation
│   ├── reports                # Reports documentation
│   ├── catalog               # Catalog management
│   ├── items                 # Items & inventory
│   ├── tools                 # Administrative tools
│   └── admin                 # System administration
└── technical/
    ├── development           # Local development setup
    ├── docker               # Docker deployment
    ├── authentication      # Auth configuration
    ├── secrets             # Secrets management
    ├── troubleshooting     # Common issues
    └── historical-sync     # Historical data sync
```

## Cross-Reference System

The system automatically converts key terms into clickable links:

- **Dashboard** → `/docs/pages/dashboard`
- **Reports** → `/docs/pages/reports`
- **Catalog** → `/docs/pages/catalog`
- **Items** → `/docs/pages/items`
- **Tools** → `/docs/pages/tools`
- **Admin** → `/docs/pages/admin`
- **Square API** → `/docs/technical/authentication`
- **database** → `/docs/technical/development`
- **Docker** → `/docs/technical/docker`
- **authentication** → `/docs/technical/authentication`

## Usage

### Accessing Documentation
1. **Main navigation** - Click "Help" in the top navigation
2. **Floating button** - Use the blue help button (bottom-right corner)
3. **Contextual links** - Click help icons next to page titles
4. **Direct URL** - Navigate to `/docs` directly

### Navigation
- **Sidebar** - Browse all documentation categories
- **Breadcrumbs** - Track your current location
- **Table of contents** - Jump to specific sections
- **Cross-links** - Follow automatic links between topics

### Search
The search functionality (coming soon) will allow full-text search across all documentation.

## Technical Implementation

### Routes
- **Main router**: `app/routes/docs.py`
- **URL structure**: `/docs/{category}/{page}`
- **Templates**: `app/templates/docs/`

### Markdown Processing
- **Library**: Python `markdown` with extensions
- **Features**: TOC, code highlighting, tables, fenced code blocks
- **Cross-linking**: Automatic term detection and linking

### Templates
- **Index**: `docs/index.html` - Documentation homepage
- **Page**: `docs/page.html` - Individual documentation pages
- **Components**: Reusable help link components

### Styling
- **Responsive design** - Works on all screen sizes
- **Dark mode support** - Consistent with application theme
- **Professional typography** - Easy-to-read documentation

## Adding New Documentation

### 1. Create Markdown File
Add your `.md` file to the `docs/` directory:

```markdown
# Page Title

## Section 1
Content here...

## Section 2
More content...
```

### 2. Update Structure
Add entry to `DOCS_STRUCTURE` in `app/routes/docs.py`:

```python
"new-page": {
    "title": "Page Title",
    "file": "NEW_PAGE.md",
    "description": "Brief description"
}
```

### 3. Add Cross-References
Update `CROSS_REFERENCES` for automatic linking:

```python
"Key Term": "/docs/path/to/page"
```

### 4. Add Contextual Help
Include help links in templates:

```html
{% include 'components/shared/help_link.html' with help_url="/docs/path/to/page" %}
```

## Benefits

### For Users
- **Self-service support** - Find answers without asking
- **Always up-to-date** - Documentation reflects current system
- **Contextual help** - Get help exactly where you need it
- **No external dependencies** - Everything in one place

### For Administrators
- **Reduced support tickets** - Users can find answers themselves
- **Centralized knowledge** - All information in one system
- **Easy maintenance** - Simple Markdown files
- **Version controlled** - Documentation changes tracked in Git

## Future Enhancements

- **Full-text search** - Search all documentation content
- **User feedback** - Rate documentation helpfulness
- **Bookmarking** - Save frequently accessed pages
- **Print-friendly** - Generate PDF versions
- **Multi-language** - Support for multiple languages

## Maintenance

Documentation is automatically updated when:
- Markdown files are modified in the `docs/` directory
- Application is restarted (for structure changes)
- Cross-reference mappings are updated

The system requires no database or external services - everything is file-based and integrated into the main application. 