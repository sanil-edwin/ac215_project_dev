"""USDA NASS Corn Yields - Download and Archive (2010-2025)"""
import pandas as pd, logging, sys, io, os
from google.cloud import storage
import google.auth
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Download and archive USDA NASS corn yields"""
    
    logger.info("=" * 70)
    logger.info("USDA NASS CORN YIELDS - DOWNLOAD & ARCHIVE (2010-2025)")
    logger.info("=" * 70)

    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform']
    )
    storage_client = storage.Client(credentials=credentials, project=project)
    bucket = storage_client.bucket("agriguard-ac215-data")

    logger.info("✓ Initialized")

    # Check existing consolidated file
    gcs_path = "data_raw/yields/iowa_corn_yields_2010_2025.csv"
    blob = bucket.blob(gcs_path)

    if blob.exists():
        logger.info("Found existing yields file, checking coverage...")
        existing_df = pd.read_csv(io.StringIO(blob.download_as_text()))
        existing_years = sorted(existing_df['year'].unique())
        logger.info(f"Existing years: {existing_years}")
    else:
        existing_df = None
        existing_years = []

    # Target years
    start_year = 2010
    end_year = 2025
    target_years = list(range(start_year, end_year + 1))
    missing_years = [y for y in target_years if y not in existing_years]

    if not missing_years:
        logger.info("✓ ALL YEARS COMPLETE!")
        return

    logger.info(f"Will download {len(missing_years)} missing years: {missing_years}")

    # USDA NASS API endpoint
    # Get API key from environment variable or use None for public access
    api_key = os.getenv('NASS_API_KEY')
    if not api_key:
        logger.warning("NASS_API_KEY environment variable not set. Using public API (limited rate).")
        logger.info("To set API key: export NASS_API_KEY='your_key_here'")
        api_key = None
    else:
        logger.info("✓ Using NASS API key from environment")
    
    base_url = "https://quickstats.nass.usda.gov/api/api_GET"

    all_results = []

    for year in missing_years:
        try:
            logger.info(f"\nDownloading yields for {year}...")
            
            params = {
                'commodity_desc': 'CORN',
                'data_item': 'CORN, GRAIN - YIELD, MEASURED IN BU / ACRE',
                'geographic_level': 'COUNTY',
                'state_name': 'IOWA',
                'year': year,
                'format': 'JSON'
            }
            
            # Add API key if available
            if api_key:
                params['key'] = api_key
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data or len(data['data']) == 0:
                logger.warning(f"  No data for {year}")
                continue
            
            records = data['data']
            logger.info(f"  Found {len(records)} records for {year}")
            
            # Parse records
            for record in records:
                value_str = record.get('Value', '')
                try:
                    yield_value = float(value_str) if value_str else None
                except:
                    yield_value = None
                
                all_results.append({
                    'year': int(record.get('year', year)),
                    'state': record.get('state_name', 'IOWA'),
                    'state_fips': record.get('state_fips_code', '19'),
                    'county': record.get('county_name', ''),
                    'county_fips': record.get('county_code', ''),
                    'yield_bu_per_acre': yield_value,
                    'unit': record.get('unit_desc', 'BU / ACRE'),
                    'fips': (record.get('state_fips_code', '19') + 
                            record.get('county_code', '').zfill(3))
                })
            
            logger.info(f"  ✓ {year} - {len(records)} records")
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"  ✗ {year} - 401 Unauthorized: API key required or invalid")
                logger.error("    Get API key: https://quickstats.nass.usda.gov/api")
                logger.error("    Set: export NASS_API_KEY='your_key_here'")
            else:
                logger.error(f"  ✗ Error downloading {year}: {e}")
            continue
        
        except Exception as e:
            logger.error(f"  ✗ Error downloading {year}: {e}")
            continue

    if not all_results:
        logger.error("No new data downloaded!")
        return

    new_df = pd.DataFrame(all_results)
    logger.info(f"\nTotal new records: {len(new_df):,}")

    # Merge with existing
    if existing_df is not None:
        logger.info(f"Merging {len(existing_df)} existing + {len(new_df)} new records")
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['year', 'fips'], keep='last')
        final_df = final_df.sort_values(['year', 'county']).reset_index(drop=True)
    else:
        final_df = new_df.sort_values(['year', 'county']).reset_index(drop=True)

    # Save consolidated file
    logger.info(f"Saving {len(final_df):,} total records...")
    csv_content = final_df.to_csv(index=False)
    blob.upload_from_string(csv_content, content_type='text/csv')

    logger.info("")
    logger.info("=" * 70)
    logger.info("✓ YIELD DOWNLOAD COMPLETE!")
    logger.info(f"📊 Total records: {len(final_df):,}")
    logger.info(f"📊 Year range: {int(final_df['year'].min())} - {int(final_df['year'].max())}")
    logger.info(f"📊 Counties: {final_df['county'].nunique()}")
    logger.info(f"📊 Mean yield: {final_df['yield_bu_per_acre'].mean():.1f} bu/acre")
    logger.info(f"📁 gs://agriguard-ac215-data/{gcs_path}")
    logger.info("=" * 70)

    logger.info("\nNote: Yields are published annually (typically January for prior year)")
    logger.info("Current year yields won't be available until following January")

if __name__ == '__main__':
    main()
