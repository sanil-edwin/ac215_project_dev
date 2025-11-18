"""Incremental ETo Update - Only downloads missing dates (May-Oct only)"""
import ee, pandas as pd, io, logging, sys, json
from google.cloud import storage
import google.auth
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("ETo INCREMENTAL UPDATE - IOWA CORN FIELDS (MAY-OCT)")
logger.info("=" * 70)

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/earthengine',
           'https://www.googleapis.com/auth/cloud-platform']
)
storage_client = storage.Client(credentials=credentials, project=project)
bucket = storage_client.bucket("agriguard-ac215-data")
ee.Initialize(credentials=credentials, project=project, opt_url='https://earthengine-highvolume.googleapis.com')

logger.info("✓ Initialized")

counties_blob = bucket.blob("data_raw/masks/iowa_counties.geojson")
counties_geojson = json.loads(counties_blob.download_as_text())
counties = ee.FeatureCollection(counties_geojson)
logger.info(f"✓ Loaded {counties.size().getInfo()} Iowa counties")

# Determine date range - ONLY May-October
current_year = datetime.now().year
season_start = f"{current_year}-05-01"
season_end_date = min(datetime.now() - timedelta(days=2), datetime(current_year, 10, 31))
season_end = season_end_date.strftime("%Y-%m-%d")

logger.info(f"Growing season: May 1 - Oct 31")
logger.info(f"Update period: {season_start} to {season_end}")

yearly_path = f"data_raw_new/weather/eto/yearly/iowa_corn_eto_{current_year}.parquet"
blob = bucket.blob(yearly_path)

existing_dates = set()
if blob.exists():
    logger.info("Loading existing data...")
    existing_df = pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
    existing_dates = set(existing_df['date'].unique())
    logger.info(f"  Found {len(existing_dates)} existing dates")
else:
    logger.info("No existing file - downloading full season")
    existing_df = None

mask_year = min(current_year, 2024)
mask_path = f"gs://agriguard-ac215-data/data_raw/masks/corn/iowa_corn_mask_{mask_year}.tif"
corn_mask = ee.Image.loadGeoTIFF(mask_path)
logger.info(f"✓ Using {mask_year} corn mask")

collection = ee.ImageCollection('IDAHO_EPSCOR/GRIDMET') \
    .filterDate(season_start, season_end) \
    .filterBounds(counties) \
    .select('eto')

count = collection.size().getInfo()
logger.info(f"Found {count} total images in date range")

if count == 0:
    logger.info("✅ No new data available")
    sys.exit(0)

results = []
image_list = collection.toList(count)
logger.info("Checking for missing dates...")
new_dates = 0

for i in range(count):
    image = ee.Image(image_list.get(i))
    date_str = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
    
    if date_str in existing_dates:
        continue
    
    new_dates += 1
    
    try:
        masked_image = image.updateMask(corn_mask)
        stats = masked_image.select('eto').reduceRegions(
            collection=counties,
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True).combine(ee.Reducer.minMax(), sharedInputs=True),
            scale=4000
        )
        
        for feature in stats.getInfo()['features']:
            props = feature['properties']
            results.append({
                'date': date_str,
                'fips': props.get('GEOID') or props.get('fips'),
                'county_name': props.get('NAME') or props.get('name'),
                'mean': props.get('mean'),
                'std': props.get('stdDev'),
                'min': props.get('min'),
                'max': props.get('max'),
                'mask_year': mask_year
            })
    except Exception as e:
        logger.warning(f"  Error on date {date_str}: {e}")
        continue
    
    if new_dates % 10 == 0:
        logger.info(f"  Processed {new_dates} new dates...")

logger.info(f"Downloaded {new_dates} new dates with {len(results)} records")

if len(results) == 0:
    logger.info("✅ Already up to date!")
    sys.exit(0)

new_df = pd.DataFrame(results)
if existing_df is not None:
    merged_df = pd.concat([existing_df, new_df], ignore_index=True)
else:
    merged_df = new_df

merged_df = merged_df.drop_duplicates(subset=['date', 'fips'], keep='last')
merged_df = merged_df.sort_values(['date', 'fips']).reset_index(drop=True)

buffer = io.BytesIO()
merged_df.to_parquet(buffer, index=False)
buffer.seek(0)
blob.upload_from_file(buffer, content_type='application/octet-stream')

logger.info("=" * 70)
logger.info(f"✅ ETo UPDATE COMPLETE!")
logger.info(f"📊 New records added: {len(results):,}")
logger.info(f"📊 Total records: {len(merged_df):,}")
logger.info(f"📅 Latest date: {merged_df['date'].max()}")
logger.info("=" * 70)

logger.info("Updating consolidated file...")
yearly_prefix = "data_raw_new/weather/eto/yearly/"
blobs = list(bucket.list_blobs(prefix=yearly_prefix))
yearly_files = [b.name for b in blobs if b.name.endswith('.parquet')]

dfs = []
for file_path in sorted(yearly_files):
    df = pd.read_parquet(io.BytesIO(bucket.blob(file_path).download_as_bytes()))
    dfs.append(df)

consolidated_df = pd.concat(dfs, ignore_index=True)
consolidated_df = consolidated_df.drop_duplicates(subset=['date', 'fips'], keep='last')
consolidated_df = consolidated_df.sort_values(['date', 'fips']).reset_index(drop=True)

output_path = "data_raw_new/weather/eto/iowa_corn_eto_20160501_20251031.parquet"
buffer = io.BytesIO()
consolidated_df.to_parquet(buffer, index=False)
buffer.seek(0)
bucket.blob(output_path).upload_from_file(buffer, content_type='application/octet-stream')

logger.info(f"✓ Consolidated file updated: {len(consolidated_df):,} total records")
