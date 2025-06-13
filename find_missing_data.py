#!/usr/bin/env python3
"""
Find exactly what data is missing in production compared to development
"""

import pandas as pd

def find_missing_data():
    """Find what data is missing in production vs development"""
    
    try:
        # File paths
        prod_file = '/Users/joshgoble/Downloads/square_catalog_export_20250613_023527.xlsx'
        dev_file = '/Users/joshgoble/Downloads/square_catalog_export_20250613_023622.xlsx'
        
        print("📊 Loading export files to find missing data...")
        prod_df = pd.read_excel(prod_file)
        dev_df = pd.read_excel(dev_file)
        
        print(f'Production: {len(prod_df)} rows')
        print(f'Development: {len(dev_df)} rows')
        print()
        
        # Create unique identifiers for each row
        print('=== IDENTIFYING UNIQUE ITEMS ===')
        
        # Use SKU + Item Name as unique identifier
        prod_df['unique_id'] = prod_df['SKU'].astype(str) + '|' + prod_df['Item Name'].astype(str)
        dev_df['unique_id'] = dev_df['SKU'].astype(str) + '|' + dev_df['Item Name'].astype(str)
        
        prod_items = set(prod_df['unique_id'])
        dev_items = set(dev_df['unique_id'])
        
        print(f'Production unique items: {len(prod_items)}')
        print(f'Development unique items: {len(dev_items)}')
        
        # Find items only in development (missing from production)
        missing_in_prod = dev_items - prod_items
        missing_in_dev = prod_items - dev_items
        
        print(f'Items missing in PRODUCTION: {len(missing_in_prod)}')
        print(f'Items missing in DEVELOPMENT: {len(missing_in_dev)}')
        print()
        
        if missing_in_prod:
            print('=== ITEMS MISSING IN PRODUCTION ===')
            missing_df = dev_df[dev_df['unique_id'].isin(missing_in_prod)]
            
            print(f'Found {len(missing_df)} items in development that are missing in production:')
            for idx, row in missing_df.head(10).iterrows():
                print(f'  - {row["Item Name"]} (SKU: {row["SKU"]})')
            
            if len(missing_df) > 10:
                print(f'  ... and {len(missing_df) - 10} more')
            
            print()
            print('Sample of missing items with key details:')
            key_cols = ['Item Name', 'SKU', 'Categories', 'Enabled Aubrey', 'Current Quantity Aubrey']
            available_cols = [col for col in key_cols if col in missing_df.columns]
            print(missing_df[available_cols].head(5).to_string(index=False))
            print()
        
        if missing_in_dev:
            print('=== ITEMS MISSING IN DEVELOPMENT ===')
            missing_df = prod_df[prod_df['unique_id'].isin(missing_in_dev)]
            
            print(f'Found {len(missing_df)} items in production that are missing in development:')
            for idx, row in missing_df.head(10).iterrows():
                print(f'  - {row["Item Name"]} (SKU: {row["SKU"]})')
            
            if len(missing_df) > 10:
                print(f'  ... and {len(missing_df) - 10} more')
            print()
        
        # Check for items with same name but different SKUs
        print('=== CHECKING FOR SKU MISMATCHES ===')
        
        prod_names = prod_df.groupby('Item Name')['SKU'].apply(list).to_dict()
        dev_names = dev_df.groupby('Item Name')['SKU'].apply(list).to_dict()
        
        sku_mismatches = 0
        for name in set(prod_names.keys()) & set(dev_names.keys()):
            prod_skus = set(prod_names[name])
            dev_skus = set(dev_names[name])
            
            if prod_skus != dev_skus:
                sku_mismatches += 1
                if sku_mismatches <= 5:  # Show first 5 mismatches
                    print(f'Item "{name}":')
                    print(f'  Production SKUs: {sorted(prod_skus)}')
                    print(f'  Development SKUs: {sorted(dev_skus)}')
                    print(f'  Missing in prod: {sorted(dev_skus - prod_skus)}')
                    print(f'  Missing in dev: {sorted(prod_skus - dev_skus)}')
                    print()
        
        if sku_mismatches > 5:
            print(f'... and {sku_mismatches - 5} more items with SKU mismatches')
        
        print('=== DATA FRESHNESS CHECK ===')
        
        # Check if this might be a data sync timing issue
        # Look at categories to see if there are systematic differences
        prod_categories = set(prod_df['Categories'].dropna())
        dev_categories = set(dev_df['Categories'].dropna())
        
        print(f'Production categories: {len(prod_categories)}')
        print(f'Development categories: {len(dev_categories)}')
        
        if dev_categories - prod_categories:
            print(f'Categories only in DEV: {list(dev_categories - prod_categories)[:5]}...' if len(dev_categories - prod_categories) > 5 else f'Categories only in DEV: {list(dev_categories - prod_categories)}')
        
        if prod_categories - dev_categories:
            print(f'Categories only in PROD: {list(prod_categories - dev_categories)[:5]}...' if len(prod_categories - dev_categories) > 5 else f'Categories only in PROD: {list(prod_categories - dev_categories)}')
        
        print()
        print('=== SUMMARY ===')
        print(f'🔍 Data Completeness Analysis:')
        print(f'  - Production has {len(prod_items):,} unique items')
        print(f'  - Development has {len(dev_items):,} unique items')
        print(f'  - {len(missing_in_prod):,} items missing in production')
        print(f'  - {len(missing_in_dev):,} items missing in development')
        print(f'  - {sku_mismatches:,} items with SKU mismatches')
        
        if missing_in_prod > 0:
            print(f'  ❌ PRODUCTION IS MISSING DATA - needs investigation!')
        elif missing_in_dev > 0:
            print(f'  ❌ DEVELOPMENT IS MISSING DATA - needs investigation!')
        else:
            print(f'  ✅ Both environments have the same items')
        
    except Exception as e:
        print(f'❌ Error finding missing data: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    find_missing_data() 