# NYTex Dashboard Tests

This directory contains all test scripts for the NYTex Dashboard system.

## Unit Tests

### Core Application Tests
- `test_app.py` - Main application test suite
- `test_db.py` - Database connection and basic operations tests
- `test_query.py` - Database query functionality tests

### Business Logic Tests
- `test_season_service.py` - Operating seasons service tests
- `test_season_dict.py` - Season dictionary functionality tests
- `test_current_season.py` - Current season detection tests
- `test_seasonal_sales.py` - Seasonal sales reporting tests

## Integration Tests

### Square API Tests
- `test_square_api_endpoints.py` - Square API connectivity and endpoint tests
- `test_square_custom_fields.py` - Custom field handling in Square API tests

### System Tests
- `test_incremental_sync.py` - Incremental sync functionality tests

## Running Tests

Run all tests:
```bash
python -m pytest tests/
```

Run specific test files:
```bash
# Unit tests
python -m pytest tests/test_seasonal_sales.py

# Integration tests
python -m pytest tests/test_square_api_endpoints.py
python -m pytest tests/test_incremental_sync.py
```

Run with verbose output:
```bash
python -m pytest tests/ -v
```

## Test Categories

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test system components working together
- **API Tests**: Test external API integrations (Square API)

## Notes

- Tests require proper environment variables to be set
- Integration tests may require database access
- API tests require valid Square API credentials 