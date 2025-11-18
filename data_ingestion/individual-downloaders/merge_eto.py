"""Merge yearly ETo files into single consolidated file"""
import pandas as pd
import io
import logging
from google.cloud import storage
import google.auth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("=" * 70)
logger.info("MERGING ETo YEARLY FILES - 2016-2025")
logger.info("=" * 70)

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
storage_client = storage.Client(credentials=credentials, project=project)
bucket = storage_client.bucket("agriguard-ac215-data")

logger.info("✓ Initialized")

# List all yearly files
yearly_prefix = "data_raw_new/weather/eto/yearly/"
blobs = list(bucket.list_blobs(prefix=yearly_prefix))

yearly_files = [blob.name for blob in blobs if blob.name.endswith('.parquet')]
logger.info(f"Found {len(yearly_files)} yearly files")

if len(yearly_files) == 0:
    logger.error("No yearly files found!")
    exit(1)

# Load and concatenate all years
dfs = []
for file_path in sorted(yearly_files):
    year = file_path.split('_')[-1].replace('.parquet', '')
    logger.info(f"  Loading {year}...")
    blob = bucket.blob(file_path)
    df = pd.read_parquet(io.BytesIO(blob.download_as_bytes()))
    dfs.append(df)
    logger.info(f"    ✓ {len(df):,} records")

# Merge all dataframes
logger.info("Merging all years...")
merged_df = pd.concat(dfs, ignore_index=True)

# Remove duplicates and sort
merged_df = merged_df.drop_duplicates(subset=['date', 'fips'], keep='last')
merged_df = merged_df.sort_values(['date', 'fips']).reset_index(drop=True)

logger.info(f"Total records after merge: {len(merged_df):,}")
logger.info(f"Date range: {merged_df['date'].min()} to {merged_df['date'].max()}")
logger.info(f"Counties: {merged_df['fips'].nunique()}")

# Save merged file
output_path = "data_raw_new/weather/eto/iowa_corn_eto_20160501_20251031.parquet"
blob = bucket.blob(output_path)

buffer = io.BytesIO()
merged_df.to_parquet(buffer, index=False)
buffer.seek(0)
blob.upload_from_file(buffer, content_type='application/octet-stream')

logger.info("=" * 70)
logger.info("✅ MERGE COMPLETE!")
logger.info(f"📊 Total records: {len(merged_df):,}")
logger.info(f"📅 Date range: {merged_df['date'].min()} to {merged_df['date'].max()}")
logger.info(f"📍 gs://agriguard-ac215-data/{output_path}")
logger.info("=" * 70)
