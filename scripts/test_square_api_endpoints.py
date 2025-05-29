#!/usr/bin/env python3
"""
Test Square API endpoints to understand data structure
"""
import asyncio
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from app.config import Config

async def test_square_endpoints():
    """Test Square API endpoints"""
    
    square_access_token = getattr(Config, 'SQUARE_ACCESS_TOKEN', '')
    square_environment = getattr(Config, 'SQUARE_ENVIRONMENT', 'production')
    
    if square_environment.lower() == 'production':
        base_url = "https://connect.squareup.com"
    else:
        base_url = "https://connect.squareupsandbox.com"
    
    print("🧪 Testing Square API Endpoints")
    print("=" * 50)
    print(f"Environment: {square_environment}")
    print(f"Base URL: {base_url}")
    
    if not square_access_token:
        print("❌ No Square access token configured")
        return
        
    timeout = aiohttp.ClientTimeout(total=30)
    
    # Test endpoints
    endpoints_to_test = [
        {
            'name': 'Orders Search',
            'url': '/v2/orders/search',
            'method': 'POST',
            'payload': {
                "location_ids": ["{location_id}"],
                "query": {
                    "filter": {
                        "date_time_filter": {
                            "created_at": {
                                "start_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                                "end_at": datetime.now(timezone.utc).isoformat()
                            }
                        }
                    }
                },
                "limit": 3
            }
        },
        {
            'name': 'Payments List', 
            'url': '/v2/payments',
            'method': 'GET',
            'params': {
                'begin_time': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat(),
                'limit': 3,
                'location_id': '{location_id}'
            }
        },
        {
            'name': 'Transactions List',  
            'url': '/v2/locations/{location_id}/transactions',
            'method': 'GET',
            'params': {
                'begin_time': (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat(),
                'limit': 3
            }
        }
    ]
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # First get a location ID for transactions endpoint
        location_id = None
        try:
            headers = {'Authorization': f'Bearer {square_access_token}'}
            async with session.get(f"{base_url}/v2/locations", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    locations = data.get('locations', [])
                    if locations:
                        location_id = locations[0]['id']
                        print(f"🔍 Using location ID: {location_id}")
        except Exception as e:
            print(f"⚠️ Could not get location ID: {e}")
        
        # Test each endpoint
        for endpoint in endpoints_to_test:
            print(f"\n📡 Testing: {endpoint['name']}")
            print("-" * 30)
            
            try:
                url = endpoint['url']
                payload = endpoint.get('payload', {})
                params = endpoint.get('params', {})
                
                # Handle location_id placeholder in URL
                if '{location_id}' in url:
                    if location_id:
                        url = url.replace('{location_id}', location_id)
                    else:
                        print("❌ Skipping - no location ID available")
                        continue
                
                # Handle location_id placeholder in payload
                if payload:
                    payload_str = json.dumps(payload)
                    if '{location_id}' in payload_str and location_id:
                        payload_str = payload_str.replace('{location_id}', location_id)
                        payload = json.loads(payload_str)
                
                # Handle location_id placeholder in params
                if params:
                    for key, value in params.items():
                        if isinstance(value, str) and '{location_id}' in value and location_id:
                            params[key] = value.replace('{location_id}', location_id)
                
                full_url = f"{base_url}{url}"
                headers = {'Authorization': f'Bearer {square_access_token}'}
                
                if endpoint['method'] == 'POST':
                    headers['Content-Type'] = 'application/json'
                    async with session.post(full_url, headers=headers, json=payload) as response:
                        status = response.status
                        data = await response.json()
                elif endpoint['method'] == 'GET':
                    async with session.get(full_url, headers=headers, params=params) as response:
                        status = response.status
                        data = await response.json()
                
                print(f"Status: {status}")
                
                if status == 200:
                    # Find the main data array
                    main_key = None
                    for key in ['orders', 'payments', 'transactions']:
                        if key in data:
                            main_key = key
                            break
                    
                    if main_key and data[main_key]:
                        items = data[main_key]
                        print(f"✅ Found {len(items)} {main_key}")
                        
                        # Show structure of first item
                        if items:
                            first_item = items[0]
                            print(f"📋 Sample {main_key[:-1]} structure:")
                            for key in sorted(first_item.keys())[:10]:  # First 10 keys
                                value = first_item[key]
                                if isinstance(value, dict):
                                    print(f"  {key}: {type(value).__name__} with {len(value)} fields")
                                elif isinstance(value, list):
                                    print(f"  {key}: {type(value).__name__} with {len(value)} items")
                                else:
                                    print(f"  {key}: {value}")
                            
                            if len(first_item.keys()) > 10:
                                print(f"  ... and {len(first_item.keys()) - 10} more fields")
                    else:
                        print(f"✅ Response received but no {endpoint['name'].lower()} found")
                        print(f"Available keys: {list(data.keys())}")
                else:
                    print(f"❌ Error: {status}")
                    if 'errors' in data:
                        for error in data['errors']:
                            print(f"  - {error.get('detail', error)}")
                    else:
                        print(f"  Response: {data}")
                        
            except Exception as e:
                print(f"❌ Exception: {str(e)}")
    
    print(f"\n🎯 Next Steps:")
    print("1. Review the API response structures above")
    print("2. Update the incremental sync to match the actual API responses")  
    print("3. Test with a small subset of data first")

if __name__ == "__main__":
    asyncio.run(test_square_endpoints()) 