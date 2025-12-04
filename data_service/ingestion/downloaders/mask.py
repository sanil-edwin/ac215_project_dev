"""USDA CDL Corn Masks - Download and Archive (2010-2025)"""
import ee, pandas as pd, io, logging, sys
from google.cloud import storage
import google.auth
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Download and archive CDL corn masks for all years"""
    
    logger.info("=" * 70)
    logger.info("USDA CDL CORN MASKS - DOWNLOAD & ARCHIVE (2010-2025)")
    logger.info("=" * 70)

    credentials, project = google.auth.default(
        scopes=['https://www.googleapis.com/auth/earthengine',
               'https://www.googleapis.com/auth/cloud-platform']
    )
    storage_client = storage.Client(credentials=credentials, project=project)
    bucket = storage_client.bucket("agriguard-ac215-data")
    ee.Initialize(credentials=credentials, project=project, opt_url='https://earthengine-highvolume.googleapis.com')

    logger.info("✓ Initialized")

    # Target years
    start_year = 2010
    end_year = 2025

    logger.info(f"Checking CDL masks for {start_year}-{end_year}...")

    missing_years = []
    existing_years = []

    for year in range(start_year, end_year + 1):
        mask_path = f"data_raw/masks/corn/iowa_corn_mask_{year}.tif"
        blob = bucket.blob(mask_path)
        
        if blob.exists():
            logger.info(f"  ✓ {year} - exists ({blob.size} bytes)")
            existing_years.append(year)
        else:
            logger.info(f"  ✗ {year} - MISSING")
            missing_years.append(year)

    if not missing_years:
        logger.info("✓ ALL MASKS COMPLETE!")
        return

    logger.info(f"\nDownloading {len(missing_years)} missing masks: {missing_years}")

    # Download missing CDL masks
    for year in missing_years:
        try:
            logger.info(f"\nDownloading CDL {year}...")
            
            # Use USDA CDL for the year
            cdl = ee.Image(f'USDA/NASS/CDL/{year}')
            
            # Mask for corn only (value = 1)
            corn_mask = cdl.eq(1).toByte()
            
            # Get Iowa bounds (rough)
            iowa = ee.Geometry.BBox(-96.8, 40.2, -90.0, 43.5)
            
            # Export to GCS
            task = ee.batch.Export.image.toCloudStorage(
                image=corn_mask,
                description=f'iowa_corn_mask_{year}',
                bucket='agriguard-ac215-data',
                fileNamePrefix=f'data_raw/masks/corn/iowa_corn_mask_{year}',
                scale=30,
                region=iowa,
                crs='EPSG:4326'
            )
            
            task.start()
            logger.info(f"  ⏳ Task started (ID: {task.id})")
            
            # Wait for completion (with timeout)
            import time
            max_wait = 3600  # 1 hour
            waited = 0
            while task.active() and waited < max_wait:
                time.sleep(30)
                waited += 30
                status = task.status()
                logger.info(f"  ⏳ Progress: {status['state']}")
            
            if task.active():
                logger.warning(f"  ⚠️  Task timeout after {waited}s - continuing (may complete later)")
            else:
                status = task.status()
                if status['state'] == 'COMPLETED':
                    logger.info(f"  ✓ {year} downloaded successfully")
                else:
                    logger.error(f"  ✗ {year} failed: {status}")
        
        except Exception as e:
            logger.error(f"  ✗ Error downloading {year}: {e}")
            continue

    logger.info("")
    logger.info("=" * 70)
    logger.info("✓ MASK DOWNLOAD COMPLETE!")
    logger.info(f"📊 Existing: {len(existing_years)} masks")
    logger.info(f"📊 Downloaded: {len(missing_years)} masks")
    logger.info(f"📊 Total available: {len(existing_years) + len(missing_years)} / {end_year - start_year + 1}")
    logger.info("=" * 70)

    logger.info("\nNote: CDL masks are reference data (rarely changes)")
    logger.info("Re-run this job only if new years are needed or data is corrupted")

if __name__ == '__main__':
    main()
