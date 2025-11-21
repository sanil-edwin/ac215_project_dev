"""LST - Iowa Corn Fields Only - 2016-2025 (May-Oct)"""
import ee, pandas as pd, io, logging, sys, json
from google.cloud import storage
import google.auth
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("LST - IOWA CORN FIELDS - 2016-2025 (MAY-OCT)")
logger.info("=" * 70)

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/earthengine',
           'https://www.googleapis.com/auth/cloud-platform']
)
storage_client = storage.Client(credentials=credentials, project=project)
bucket = storage_client.bucket("agriguard-ac215-data")
ee.Initialize(credentials=credentials, project=project, opt_url='https://earthengine-highvolume.googleapis.com')

logger.info("✓ Initialized")

# Load custom Iowa counties
logger.info("Loading Iowa counties from GCS...")
counties_blob = bucket.blob("data_raw/masks/iowa_counties.geojson")
counties_geojson = json.loads(counties_blob.download_as_text())
counties = ee.FeatureCollection(counties_geojson)
logger.info(f"✓ Loaded {counties.size().getInfo()} Iowa counties")

# Check existing data
gcs_path = "data_raw_new/modis/lst/iowa_corn_lst_20160501_20251031.parquet"
blob = bucket.blob(gcs_path)

if blob.exists():
    existing_df = pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
    last_date = pd.to_datetime(existing_df['date']).max()
    start_date = (last_date + timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info(f"Last date in existing data: {last_date.strftime('%Y-%m-%d')}")
    
    if start_date > datetime.now().strftime("%Y-%m-%d"):
        logger.info("✅ ALREADY UP TO DATE!")
        sys.exit(0)
else:
    existing_df = None
    start_date = "2016-05-01"

logger.info(f"Will download from: {start_date}")

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

# MODIS LST collection
collection = ee.ImageCollection('MODIS/061/MOD11A2') \
    .filterDate(start_date, '2025-10-31') \
    .filterBounds(counties) \
    .select('LST_Day_1km')

count = collection.size().getInfo()
logger.info(f"Found {count} LST images")

if count == 0:
    logger.info("✅ NO NEW DATA")
    sys.exit(0)

results = []
image_list = collection.toList(count)

logger.info("Processing images...")
for i in range(count):
    try:
        image = ee.Image(image_list.get(i))
        date_str = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        year = int(date_str.split('-')[0])
        month = int(date_str.split('-')[1])
        
        # Only May-October
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
        
        stats = masked_image.select('LST_Day_1km').reduceRegions(
            collection=counties,
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.stdDev(), sharedInputs=True
            ).combine(
                ee.Reducer.minMax(), sharedInputs=True
            ),
            scale=1000
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
        
        if (i+1) % 10 == 0 or (i+1) == count:
            logger.info(f"  Progress: {i+1}/{count} - {date_str} (mask: {mask_year}) - {len(results)} records")
    
    except Exception as e:
        logger.warning(f"  Error on image {i}: {e}")
        continue

logger.info(f"Extracted {len(results)} records")

new_df = pd.DataFrame(results)

# Apply scale factor (MODIS LST: 0.02, converts to Kelvin, then to Celsius)
for col in ['mean','std','min','max']:
    if col in new_df.columns and new_df[col].notna().any():
        new_df[col] = new_df[col] * 0.02 - 273.15  # Kelvin to Celsius

# Merge with existing
if existing_df is not None:
    final_df = pd.concat([existing_df, new_df], ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['date','fips'], keep='last')
    final_df = final_df.sort_values(['date','fips']).reset_index(drop=True)
else:
    final_df = new_df.sort_values(['date','fips']).reset_index(drop=True)

buffer = io.BytesIO()
final_df.to_parquet(buffer, index=False)
buffer.seek(0)
blob.upload_from_file(buffer, content_type='application/octet-stream')

logger.info("=" * 70)
logger.info(f"✅ LST COMPLETE!")
logger.info(f"📊 Total records: {len(final_df):,} ({len(new_df):,} new)")
logger.info(f"📅 Date range: {final_df['date'].min()} to {final_df['date'].max()}")
logger.info(f"🌡️  LST in Celsius")
logger.info(f"🌽 Corn-masked with year-specific CDL data")
logger.info(f"📁 gs://agriguard-ac215-data/{gcs_path}")
logger.info("=" * 70)
