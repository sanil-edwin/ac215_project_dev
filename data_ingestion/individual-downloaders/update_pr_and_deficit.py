"""
Incremental Precipitation + Water Deficit Updater for AgriGuard
1. Updates Precipitation data
2. Recalculates Water Deficit with updated data
"""
import ee
import pandas as pd
import io
import logging
from datetime import datetime, timedelta
from google.cloud import storage
import google.auth
import geopandas as gpd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Earth Engine
ee.Initialize()

# Initialize GCS
credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
storage_client = storage.Client(credentials=credentials, project=project)
bucket = storage_client.bucket("agriguard-ac215-data")

logger.info("=" * 70)
logger.info("INCREMENTAL PRECIPITATION + WATER DEFICIT UPDATE")
logger.info("=" * 70)

# File paths
PR_FILE = "data_raw_new/weather/pr/iowa_corn_pr_20160501_20251031.parquet"
ETO_FILE = "data_raw_new/weather/eto/iowa_corn_eto_20160501_20251031.parquet"
DEFICIT_FILE = "data_raw_new/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet"
COUNTIES_FILE = "data_raw/masks/iowa_counties.geojson"

# ============================================================================
# STEP 1: UPDATE PRECIPITATION DATA
# ============================================================================

logger.info("\n" + "=" * 70)
logger.info("STEP 1: UPDATING PRECIPITATION DATA")
logger.info("=" * 70)

# Load existing precipitation data
logger.info("\nLoading existing Precipitation data...")
pr_blob = bucket.blob(PR_FILE)
existing_pr_df = pd.read_parquet(io.BytesIO(pr_blob.download_as_bytes()))
logger.info(f"  ✓ Loaded {len(existing_pr_df):,} existing records")
logger.info(f"  Latest date: {existing_pr_df['date'].max()}")

# Determine date range to download
latest_date = pd.to_datetime(existing_pr_df['date'].max())
today = datetime.now()
start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
end_date = today.strftime('%Y-%m-%d')

logger.info(f"\nDate range to download: {start_date} to {end_date}")

if start_date > end_date:
    logger.info("✓ Precipitation data is already up to date!")
    pr_updated = False
    merged_pr_df = existing_pr_df
else:
    # Load counties
    logger.info("\nLoading Iowa counties...")
    counties_blob = bucket.blob(COUNTIES_FILE)
    counties_gdf = gpd.read_file(io.BytesIO(counties_blob.download_as_bytes()))
    logger.info(f"  ✓ Loaded {len(counties_gdf)} counties")
    
    # Determine mask year
    current_year = today.year
    mask_year = current_year - 1
    logger.info(f"  Using {mask_year} corn mask")
    
    # Download new precipitation data
    logger.info("\nDownloading new Precipitation data...")
    iowa_bounds = ee.FeatureCollection(
        [ee.Feature(ee.Geometry.Rectangle(
            counties_gdf.total_bounds.tolist()
        ))]
    )
    
    gridmet = ee.ImageCollection("IDAHO_EPSCOR/GRIDMET") \
        .select('pr') \
        .filterDate(start_date, end_date) \
        .filterBounds(iowa_bounds)
    
    images = gridmet.toList(gridmet.size())
    num_images = images.size().getInfo()
    logger.info(f"  Found {num_images} new daily images")
    
    if num_images == 0:
        logger.info("  No new images to process")
        pr_updated = False
        merged_pr_df = existing_pr_df
    else:
        # Process new images
        new_pr_records = []
        logger.info("\nProcessing images...")
        
        for i in range(num_images):
            img = ee.Image(images.get(i))
            date = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
            
            # Extract county statistics
            for idx, county in counties_gdf.iterrows():
                fips = county['GEOID']
                county_name = county['NAME']
                geometry = ee.Geometry(county['geometry'].__geo_interface__)
                
                try:
                    stats = img.reduceRegion(
                        reducer=ee.Reducer.mean().combine(
                            ee.Reducer.stdDev(), '', True
                        ).combine(
                            ee.Reducer.minMax(), '', True
                        ),
                        geometry=geometry,
                        scale=4000,
                        maxPixels=1e9
                    ).getInfo()
                    
                    if stats.get('pr_mean') is not None:
                        new_pr_records.append({
                            'date': date,
                            'fips': fips,
                            'county_name': county_name,
                            'mean': stats['pr_mean'],
                            'std': stats.get('pr_stdDev', 0),
                            'min': stats.get('pr_min', stats['pr_mean']),
                            'max': stats.get('pr_max', stats['pr_mean']),
                            'mask_year': mask_year
                        })
                except Exception as e:
                    logger.warning(f"  Error processing {fips} on {date}: {e}")
                    continue
            
            if (i + 1) % 10 == 0 or (i + 1) == num_images:
                logger.info(f"  Processed {i + 1}/{num_images} images")
        
        logger.info(f"\n✓ Extracted {len(new_pr_records):,} new precipitation records")
        
        if len(new_pr_records) == 0:
            logger.info("  No new data extracted")
            pr_updated = False
            merged_pr_df = existing_pr_df
        else:
            # Merge with existing data
            new_pr_df = pd.DataFrame(new_pr_records)
            merged_pr_df = pd.concat([existing_pr_df, new_pr_df], ignore_index=True)
            merged_pr_df = merged_pr_df.drop_duplicates(subset=['date', 'fips'], keep='last')
            merged_pr_df = merged_pr_df.sort_values(['date', 'fips']).reset_index(drop=True)
            
            logger.info(f"\nMerged Precipitation dataset:")
            logger.info(f"  Total records: {len(merged_pr_df):,}")
            logger.info(f"  Date range: {merged_pr_df['date'].min()} to {merged_pr_df['date'].max()}")
            
            # Save updated precipitation file
            logger.info("\nSaving updated Precipitation file...")
            buffer = io.BytesIO()
            merged_pr_df.to_parquet(buffer, index=False)
            buffer.seek(0)
            pr_blob.upload_from_file(buffer, content_type='application/octet-stream')
            logger.info("  ✓ Precipitation file updated")
            
            pr_updated = True

# ============================================================================
# STEP 2: RECALCULATE WATER DEFICIT
# ============================================================================

logger.info("\n" + "=" * 70)
logger.info("STEP 2: RECALCULATING WATER DEFICIT")
logger.info("=" * 70)

# Load latest ETo data
logger.info("\nLoading latest ETo data...")
eto_blob = bucket.blob(ETO_FILE)
eto_df = pd.read_parquet(io.BytesIO(eto_blob.download_as_bytes()))
logger.info(f"  ✓ Loaded {len(eto_df):,} ETo records")

# Use merged precipitation data
logger.info("Using Precipitation data...")
pr_df = merged_pr_df
logger.info(f"  ✓ Using {len(pr_df):,} Precipitation records")

# Merge ETo and Precipitation
logger.info("\nMerging ETo and Precipitation...")
merged = eto_df.merge(pr_df, on=['date', 'fips'], suffixes=('_eto', '_pr'))
logger.info(f"  ✓ Merged to {len(merged):,} records")

# Calculate water deficit
logger.info("Calculating water deficit...")
water_deficit_df = pd.DataFrame({
    'date': merged['date'],
    'fips': merged['fips'],
    'county_name': merged['county_name_eto'],
    'eto_mean': merged['mean_eto'],
    'pr_mean': merged['mean_pr'],
    'water_deficit': merged['mean_eto'] - merged['mean_pr'],
    'eto_std': merged['std_eto'],
    'pr_std': merged['std_pr'],
    'mask_year': merged['mask_year_eto']
})

logger.info(f"  ✓ Calculated water deficit")
logger.info(f"  Date range: {water_deficit_df['date'].min()} to {water_deficit_df['date'].max()}")

# Calculate statistics
total = len(water_deficit_df)
surplus = (water_deficit_df['water_deficit'] < 0).sum()
normal = ((water_deficit_df['water_deficit'] >= 0) & (water_deficit_df['water_deficit'] <= 2)).sum()
moderate = ((water_deficit_df['water_deficit'] > 2) & (water_deficit_df['water_deficit'] <= 4)).sum()
high = ((water_deficit_df['water_deficit'] > 4) & (water_deficit_df['water_deficit'] <= 6)).sum()
severe = (water_deficit_df['water_deficit'] > 6).sum()

logger.info("\nWater Deficit Statistics:")
logger.info(f"  Mean: {water_deficit_df['water_deficit'].mean():.2f} mm/day")
logger.info(f"  Min: {water_deficit_df['water_deficit'].min():.2f} mm/day")
logger.info(f"  Max: {water_deficit_df['water_deficit'].max():.2f} mm/day")
logger.info(f"\nStress Distribution:")
logger.info(f"  Surplus (negative): {surplus:,} ({surplus/total*100:.1f}%)")
logger.info(f"  Normal (0-2 mm): {normal:,} ({normal/total*100:.1f}%)")
logger.info(f"  Moderate (2-4 mm): {moderate:,} ({moderate/total*100:.1f}%)")
logger.info(f"  High (4-6 mm): {high:,} ({high/total*100:.1f}%)")
logger.info(f"  Severe (>6 mm): {severe:,} ({severe/total*100:.1f}%)")

# Save updated water deficit file
logger.info("\nSaving updated Water Deficit file...")
deficit_blob = bucket.blob(DEFICIT_FILE)
buffer = io.BytesIO()
water_deficit_df.to_parquet(buffer, index=False)
buffer.seek(0)
deficit_blob.upload_from_file(buffer, content_type='application/octet-stream')

logger.info("=" * 70)
logger.info("✅ UPDATE COMPLETE!")
if pr_updated:
    logger.info(f"📊 Added {len(new_pr_records):,} new Precipitation records")
logger.info(f"📊 Total Precipitation records: {len(pr_df):,}")
logger.info(f"📊 Total Water Deficit records: {len(water_deficit_df):,}")
logger.info(f"📅 Latest date: {water_deficit_df['date'].max()}")
logger.info(f"📍 gs://agriguard-ac215-data/{PR_FILE}")
logger.info(f"📍 gs://agriguard-ac215-data/{DEFICIT_FILE}")
logger.info("=" * 70)
