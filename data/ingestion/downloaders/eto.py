"""ETo - Iowa Corn Fields Only - Incremental (May-Oct)"""
import ee, pandas as pd, io, logging, sys, json
from google.cloud import storage
import google.auth
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Download and update ETo data incrementally"""
    
    logger.info("=" * 70)
    logger.info("ETo - IOWA CORN FIELDS - INCREMENTAL (MAY-OCT)")
    logger.info("=" * 70)

    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/earthengine',
               'https://www.googleapis.com/auth/cloud-platform']
    )
    storage_client = storage.Client(credentials=credentials, project=project)
    bucket = storage_client.bucket("agriguard-ac215-data")
    ee.Initialize(credentials=credentials, project=project, opt_url='https://earthengine-highvolume.googleapis.com')

    logger.info("✓ Initialized")

    # Load Iowa counties
    logger.info("Loading Iowa counties from GCS...")
    counties_blob = bucket.blob("data_raw/masks/iowa_counties.geojson")
    counties_geojson = json.loads(counties_blob.download_as_text())
    counties = ee.FeatureCollection(counties_geojson)
    logger.info(f"✓ Loaded {counties.size().getInfo()} Iowa counties")

    # Check existing consolidated data
    gcs_path = "data_raw_new/weather/eto/iowa_corn_eto_20160501_20251031.parquet"
    blob = bucket.blob(gcs_path)

    if blob.exists():
        logger.info("Found existing data, checking last date...")
        existing_df = pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
        last_date = pd.to_datetime(existing_df['date']).max()
        start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
        logger.info(f"Last date in existing data: {last_date.strftime('%Y-%m-%d')}")
        
        if start_date > datetime.now().strftime("%Y-%m-%d"):
            logger.info("✓ ALREADY UP TO DATE!")
            return
    else:
        existing_df = None
        start_date = "2016-05-01"

    # Use current date as end (not fixed Oct 31)
    end_date = datetime.now().strftime("%Y-%m-%d")
    logger.info(f"Will download from: {start_date} to {end_date}")

    # Load corn masks
    logger.info("Loading corn masks from GCS...")
    corn_masks = {}
    for year in range(2010, 2025):
        mask_path = f"gs://agriguard-ac215-data/data_raw/masks/corn/iowa_corn_mask_{year}.tif"
        try:
            corn_masks[year] = ee.Image.loadGeoTIFF(mask_path)
            logger.info(f"  ✓ {year}")
        except:
            pass

    # GridMET ETo daily collection
    collection = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET') \
        .filterDate(start_date, end_date) \
        .filterBounds(counties) \
        .select('eto')

    count = collection.size().getInfo()
    logger.info(f"Found {count} daily ETo images")

    if count == 0:
        logger.info("✓ NO NEW DATA")
        return

    results = []
    image_list = collection.toList(count)

    logger.info("Processing images...")
    for i in range(count):
        try:
            image = ee.Image(image_list.get(i))
            date_str = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            year = int(date_str.split('-')[0])
            month = int(date_str.split('-')[1])
            
            # Only May-October (corn season)
            if month < 5 or month > 10:
                continue
            
            # Get corn mask
            mask_year = year
            while mask_year >= 2010 and mask_year not in corn_masks:
                mask_year -= 1
            
            if mask_year >= 2010 and mask_year in corn_masks:
                masked_image = image.updateMask(corn_masks[mask_year])
            else:
                logger.warning(f"  No mask for {year}, skipping")
                continue
            
            stats = masked_image.select('eto').reduceRegions(
                collection=counties,
                reducer=ee.Reducer.mean().combine(
                    ee.Reducer.stdDev(), sharedInputs=True
                ).combine(
                    ee.Reducer.minMax(), sharedInputs=True
                ),
                scale=4000
            )
            
            for feature in stats.getInfo()['features']:
                props = feature['properties']
                results.append({
                    'date': date_str,
                    'fips': props.get('GEOID') or props.get('fips') or props.get('FIPS'),
                    'county_name': props.get('NAME') or props.get('name') or props.get('county_name'),
                    'mean': props.get('mean'),
                    'std': props.get('stdDev'),
                    'min': props.get('min'),
                    'max': props.get('max'),
                    'mask_year': mask_year
                })
            
            if (i+1) % 30 == 0 or (i+1) == count:
                logger.info(f"  Progress: {i+1}/{count} - {date_str} (mask: {mask_year}) - {len(results)} records")
        
        except Exception as e:
            logger.warning(f"  Error on image {i}: {e}")
            continue

    logger.info(f"Extracted {len(results)} records from {count} images")

    if len(results) == 0:
        logger.info("✓ Already up to date!")
        return

    new_df = pd.DataFrame(results)

    # Merge with existing
    if existing_df is not None:
        logger.info(f"Merging {len(existing_df)} existing + {len(new_df)} new records")
        final_df = pd.concat([existing_df, new_df], ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['date','fips'], keep='last')
        final_df = final_df.sort_values(['date','fips']).reset_index(drop=True)
    else:
        final_df = new_df.sort_values(['date','fips']).reset_index(drop=True)

    # Save to GCS
    buffer = io.BytesIO()
    final_df.to_parquet(buffer, index=False)
    buffer.seek(0)
    blob.upload_from_file(buffer, content_type='application/octet-stream')

    logger.info("=" * 70)
    logger.info(f"✓ ETo COMPLETE!")
    logger.info(f"📊 Total records: {len(final_df):,} ({len(new_df):,} new)")
    logger.info(f"📅 Date range: {final_df['date'].min()} to {final_df['date'].max()}")
    logger.info(f"🌡️  ETo in mm/day")
    logger.info(f"🌽 Corn-masked with year-specific CDL data")
    logger.info(f"📁 gs://agriguard-ac215-data/{gcs_path}")
    logger.info("=" * 70)

if __name__ == '__main__':
    main()
