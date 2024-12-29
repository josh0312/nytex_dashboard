# NYTEX Dashboard

A FastAPI-based dashboard for monitoring sales data across NYTEX Fireworks locations.

## Features

- Real-time sales metrics from Square API
- Seasonal sales tracking with daily breakdowns
- Location-specific sales monitoring
- Interactive charts using Chart.js
- Responsive design with Tailwind CSS

## Recent Updates

- Migrated from Flask to FastAPI for improved performance
- Fixed seasonal sales chart to:
  - Show all days in the season up to today (including days with zero sales)
  - Properly handle timezone conversions for date comparisons
  - Exclude future dates from the chart
- Improved database model relationships and initialization
- Added proper error handling and logging

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   npm install  # For Tailwind CSS
   ```

3. Set up environment variables in `.env`:
   ```
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
   SQUARE_ACCESS_TOKEN=your_square_token
   SQUARE_ENVIRONMENT=production
   SECRET_KEY=your_secret_key
   ```

4. Run the application:
   ```bash
   python run.py
   ```

## Development

- The application uses SQLAlchemy for async database operations
- Templates are rendered using Jinja2
- Static files are served from `app/static`
- Database models are in `app/database/models`
- Routes are in `app/routes`
- Services (business logic) are in `app/services`

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests: `pytest`
4. Submit a pull request

## License

Proprietary - All rights reserved 