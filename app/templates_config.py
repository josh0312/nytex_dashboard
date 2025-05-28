"""Shared Jinja2Templates configuration with custom filters."""

from fastapi.templating import Jinja2Templates
from app.filters import filters

# Create a single templates instance with custom filters
templates = Jinja2Templates(directory="app/templates")

# Register all custom filters
for name, func in filters.items():
    templates.env.filters[name] = func 