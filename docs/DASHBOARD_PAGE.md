# Dashboard Page Documentation

## Overview
The Dashboard page (`/dashboard`) serves as the main landing page and analytics hub for the NyTex Fireworks business intelligence system. It provides real-time insights into sales performance, seasonal trends, and business metrics across all locations.

## Page URL
- **Main Dashboard**: `/dashboard`
- **Metrics Endpoint**: `/dashboard/metrics`

## What This Page Does

The Dashboard page provides a comprehensive overview of business performance with the following key functions:

1. **Real-time Sales Monitoring**: Displays current sales data and transaction counts
2. **Seasonal Analytics**: Shows seasonal sales trends and comparisons
3. **Location Performance**: Breaks down sales by physical locations with weather integration
4. **Year-over-Year Comparisons**: Compares current performance to previous years
5. **Quick Access Navigation**: Provides links to detailed reports and management tools

## Page Components

### 1. **Sales Metrics Cards**
- **Total Sales**: Current day's total sales amount
- **Total Orders**: Number of transactions processed
- **Inventory Items**: Count of active inventory items
- **Low Stock Items**: Alert count for items below threshold

**Data Source**: 
- Square API (`SquareService.get_todays_sales()`)
- Local database aggregation queries
- Location-specific data from `locations` table

### 2. **Seasonal Sales Chart**
- **Interactive Line Chart**: Visual representation of sales over time
- **Date Range Selector**: Allows filtering by different time periods
- **Transaction Volume**: Shows both sales amounts and transaction counts

**Data Source**:
- `SeasonService.get_seasonal_sales()` method
- Queries seasonal data from `transactions` table
- Current season determined by `get_current_season()` function

### 3. **Location Performance Table**
- **Location Names**: All active business locations
- **Sales by Location**: Current day's sales per location
- **Order Counts**: Number of transactions per location
- **Weather Integration**: Current weather conditions for each location

**Data Source**:
- Square Locations API
- `WeatherService.get_weather_by_zip()` for weather data
- Location postal codes from `locations` table

### 4. **Annual Sales Comparison**
- **Year-over-Year Charts**: Compare current year to previous years
- **Growth Metrics**: Calculate percentage changes
- **Trend Analysis**: Identify seasonal patterns and growth trends

**Data Source**:
- Database queries on historical transaction data
- Aggregated by year, month, and season
- Filtered by active date ranges

## Data Flow

### Primary Data Sources

1. **Square API Integration**
   - **Endpoint**: Square Orders API and Locations API
   - **Update Frequency**: Real-time API calls
   - **Fallback**: Graceful degradation with mock data when API unavailable
   - **Configuration**: Controlled by `SQUARE_ACCESS_TOKEN` and `SQUARE_ENVIRONMENT`

2. **Local Database Tables**
   - **`transactions`**: Historical sales data
   - **`locations`**: Business location information
   - **`catalog_items`**: Inventory item counts
   - **`catalog_inventory`**: Stock levels and quantities

3. **Weather API**
   - **Service**: Third-party weather service
   - **Integration**: `WeatherService` class
   - **Data**: Temperature, conditions, and forecasts

### Data Processing

1. **Seasonal Calculations**
   ```python
   current_season = await get_current_season()
   sales_data = await season_service.get_seasonal_sales(current_season)
   ```

2. **Location Aggregation**
   ```python
   metrics = await square_service.get_todays_sales()
   for location_id, location in metrics.get('locations', {}).items():
       # Process location-specific data
   ```

3. **Error Handling**
   - Graceful fallback when APIs are unavailable
   - Default values for missing data
   - User-friendly error messages

## HTMX Integration

The Dashboard uses HTMX for dynamic content updates without full page reloads:

### Dynamic Components

1. **Location Sales Table** (`/dashboard/metrics/locations`)
   - Auto-refreshes location data
   - Weather updates
   - Real-time sales figures

2. **Total Sales Widget** (`/dashboard/metrics/total_sales`)
   - Live sales amount updates
   - Currency formatting
   - Error state handling

3. **Order Count Widget** (`/dashboard/metrics/total_orders`)
   - Real-time transaction counts
   - Performance indicators
   - Historical comparisons

### HTMX Endpoints

| Endpoint | Purpose | Update Frequency |
|----------|---------|------------------|
| `/dashboard/metrics/locations` | Location sales table | On demand |
| `/dashboard/metrics/total_sales` | Sales amount widget | Real-time |
| `/dashboard/metrics/total_orders` | Order count widget | Real-time |
| `/dashboard/metrics/annual_sales_comparison` | Year comparison chart | Daily |

## Error Handling

### Graceful Degradation

1. **Square API Unavailable**
   - Shows demo/mock data with clear indicators
   - Maintains page functionality
   - Logs errors for debugging

2. **Database Connection Issues**
   - Falls back to cached data
   - Shows appropriate error messages
   - Provides retry mechanisms

3. **Weather Service Failures**
   - Hides weather widgets gracefully
   - No impact on core functionality
   - Silent fallback to location data only

### Error Display

- **User-Friendly Messages**: Clear explanations of what went wrong
- **Technical Logs**: Detailed error information for developers
- **Retry Options**: Allow users to refresh specific components

## Configuration

### Required Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `SQUARE_ACCESS_TOKEN` | Square API authentication | None (required) |
| `SQUARE_ENVIRONMENT` | API environment (sandbox/production) | `production` |
| `DATABASE_URL` | Database connection string | Local PostgreSQL |

### Optional Settings

| Setting | Purpose | Default |
|---------|---------|---------|
| `WEATHER_API_KEY` | Weather service integration | None |
| `DASHBOARD_REFRESH_INTERVAL` | Auto-refresh frequency | 30 seconds |
| `DEFAULT_LOCATION` | Fallback location for weather | First active location |

## Performance Considerations

### Caching Strategy

1. **Seasonal Data**: Cached for 1 hour
2. **Location Data**: Cached for 15 minutes
3. **Weather Data**: Cached for 30 minutes

### Database Optimization

1. **Indexed Queries**: All date-based queries use database indexes
2. **Aggregation**: Pre-calculated totals where possible
3. **Connection Pooling**: Efficient database connection management

### API Rate Limiting

1. **Square API**: Respects Square's rate limits
2. **Weather API**: Batched requests for multiple locations
3. **Retry Logic**: Exponential backoff for failed requests

## Security

### Data Protection

1. **API Tokens**: Stored securely in environment variables
2. **Input Validation**: All user inputs sanitized
3. **HTTPS Only**: All external API calls use HTTPS

### Access Control

1. **Authentication**: Page requires valid user session
2. **Authorization**: Role-based access to different metrics
3. **Audit Logging**: All data access logged for compliance

## Troubleshooting

### Common Issues

1. **"Unable to load dashboard"**
   - Check Square API token configuration
   - Verify database connection
   - Review application logs

2. **Missing location data**
   - Ensure locations are properly synced from Square
   - Check location status in admin panel
   - Verify postal codes for weather integration

3. **Charts not displaying**
   - Check JavaScript console for errors
   - Verify seasonal data exists in database
   - Ensure proper date formatting

### Debug Tools

1. **Debug Endpoints**: `/dashboard/debug/*` for troubleshooting
2. **Log Files**: Application logs contain detailed error information
3. **Admin Panel**: System status and configuration validation

## Integration Points

### With Other Pages

1. **Reports Page**: Deep links to specific inventory reports
2. **Admin Page**: System status and data sync controls
3. **Catalog Page**: Quick access to catalog management
4. **Items Page**: Links to detailed item information

### External Systems

1. **Square POS**: Real-time sales and location data
2. **Weather Services**: Location-based weather information
3. **Google Cloud**: Production secrets and configuration management

This dashboard serves as the central command center for NyTex Fireworks operations, providing actionable insights for business decision-making and operational efficiency. 