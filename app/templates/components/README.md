# NyTex Dashboard Design System

## Overview
This design system ensures consistent colors, spacing, and styling across all pages in the NyTex Dashboard. It provides reusable CSS classes and template components for statistics cards, status badges, and other UI elements.

## Statistics Cards

### Using the Reusable Component
The easiest way to create consistent statistics cards is using the shared component:

```html
<!-- Basic usage -->
{% set theme = "red" %}
{% set icon = "alert-triangle" %}
{% set label = "Low Stock Items" %}
{% set value = "7" %}
{% include 'components/shared/stat_card.html' %}

<!-- Clickable card -->
{% set theme = "blue" %}
{% set icon = "users" %}
{% set label = "Vendors Affected" %}
{% set value = "4" %}
{% set clickable = true %}
{% include 'components/shared/stat_card.html' %}

<!-- Card with link -->
{% set theme = "indigo" %}
{% set icon = "dollar-sign" %}
{% set label = "Total Sales" %}
{% set value = "$45,621" %}
{% set href = "/reports/sales" %}
{% include 'components/shared/stat_card.html' %}
```

### Manual CSS Classes
If you prefer to build cards manually, use these CSS classes:

```html
<div class="stat-card-red">
    <div class="stat-content">
        <div class="stat-icon-red">
            <i data-lucide="alert-triangle" class="icon-red stat-icon-lg"></i>
        </div>
        <div class="stat-text">
            <p class="stat-label">Low Stock Items</p>
            <p class="stat-value-red">7</p>
        </div>
    </div>
</div>
```

## Color Themes

### Theme Categories
Each theme is designed for specific types of content:

| Theme | Usage | Example |
|-------|-------|---------|
| `red` | Alerts, Low Stock, Critical Items | Low stock warnings, system errors |
| `blue` | Inventory, Data, Orders | Total orders, inventory counts |
| `indigo` | Sales, Revenue, Primary Metrics | Total sales, main KPIs |
| `green` | Success, Customers, Positive Metrics | Customer count, completed orders |
| `yellow` | Warnings, Pending, Attention Needed | Pending approvals, warnings |
| `orange` | Tools, System, Administrative | System tools, admin functions |
| `purple` | Analytics, Reports, Insights | Report metrics, analytics |
| `gray` | Neutral, Settings, Meta Information | System info, neutral metrics |

### CSS Classes Available

#### Card Containers
- `.stat-card-{theme}` - Complete card with background, shadow, padding
- `.stat-card-{theme}:hover` - Hover effects for interactive cards

#### Icon Containers  
- `.stat-icon-{theme}` - Icon background circle
- `.icon-{theme}` - Icon color
- `.stat-icon-lg` - Standard icon size (h-6 w-6)

#### Text Elements
- `.stat-label` - Gray label text (consistent across themes)
- `.stat-value-{theme}` - Colored value text matching theme

#### Layout Utilities
- `.stat-grid` - Responsive grid for card layouts
- `.stat-content` - Flex container for card content
- `.stat-text` - Text container with left margin

## Grid Layouts

### Standard Statistics Grid
```html
<div class="stat-grid">
    <!-- Cards go here -->
</div>
```

This creates a responsive grid:
- 1 column on mobile
- 2 columns on small screens
- 4 columns on large screens
- Consistent gap spacing

## Status Badges

For smaller status indicators, use these badge classes:

```html
<span class="status-success">Active</span>
<span class="status-warning">Pending</span>
<span class="status-error">Failed</span>
<span class="status-info">Processing</span>
<span class="status-neutral">Unknown</span>
```

## Complete Examples

### Dashboard Metrics Section
```html
<div class="stat-grid">
    {% set theme = "indigo" %}
    {% set icon = "dollar-sign" %}
    {% set label = "Total Sales" %}
    {% set value = "$45,621" %}
    {% include 'components/shared/stat_card.html' %}
    
    {% set theme = "blue" %}
    {% set icon = "shopping-cart" %}
    {% set label = "Total Orders" %}
    {% set value = "234" %}
    {% include 'components/shared/stat_card.html' %}
    
    {% set theme = "green" %}
    {% set icon = "users" %}
    {% set label = "Customers" %}
    {% set value = "1,543" %}
    {% include 'components/shared/stat_card.html' %}
    
    {% set theme = "red" %}
    {% set icon = "alert-triangle" %}
    {% set label = "Low Stock" %}
    {% set value = "7" %}
    {% set href = "/reports/inventory/low-stock" %}
    {% include 'components/shared/stat_card.html' %}
</div>
```

### Report Statistics
```html
<div class="stat-grid">
    {% set theme = "red" %}
    {% set icon = "alert-triangle" %}
    {% set label = "Low Stock Items" %}
    {% set value = total_items %}
    {% include 'components/shared/stat_card.html' %}
    
    {% set theme = "blue" %}
    {% set icon = "users" %}
    {% set label = "Vendors Affected" %}
    {% set value = vendors|length %}
    {% include 'components/shared/stat_card.html' %}
    
    {% set theme = "gray" %}
    {% set icon = "percent" %}
    {% set label = "Threshold" %}
    {% set value = "15%" %}
    {% include 'components/shared/stat_card.html' %}
</div>
```

## Rebuilding CSS
After making changes to `app/static/css/src/main.css`, rebuild with:

```bash
npm run build:css
```

Or for development with auto-rebuild:

```bash
npm run watch:css
```

## Best Practices

1. **Consistency**: Always use the same theme for the same type of content across pages
2. **Accessibility**: The color combinations are designed for good contrast in both light and dark modes
3. **Semantic**: Choose themes based on meaning, not just appearance
4. **Performance**: CSS classes are optimized and use Tailwind's component layer
5. **Maintenance**: Update the design system here rather than adding custom styles throughout the app

## Migration Guide

### From Old Manual Classes
Replace manual Tailwind classes with design system classes:

**Before:**
```html
<div class="bg-red-100 dark:bg-red-800 p-4 rounded-lg shadow-sm">
    <div class="flex items-center">
        <div class="p-3 bg-red-200 dark:bg-red-700 rounded-full">
            <i data-lucide="alert-triangle" class="h-6 w-6 text-red-600 dark:text-red-300"></i>
        </div>
        <div class="ml-4">
            <p class="text-sm font-medium text-gray-600 dark:text-gray-300">Low Stock Items</p>
            <p class="text-2xl font-semibold text-red-600 dark:text-red-300">7</p>
        </div>
    </div>
</div>
```

**After:**
```html
{% set theme = "red" %}
{% set icon = "alert-triangle" %}
{% set label = "Low Stock Items" %}
{% set value = "7" %}
{% include 'components/shared/stat_card.html' %}
```

This approach:
- ✅ Reduces code by ~90%
- ✅ Ensures consistency across pages
- ✅ Makes theming changes easy (one place to update)
- ✅ Provides better maintainability 