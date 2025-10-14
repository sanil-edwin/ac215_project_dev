"""Data loading utilities for yield forecasting."""

import pandas as pd
from google.cloud import storage
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataLoader:
    """Load and prepare data from GCS bucket."""
    
    def __init__(self, bucket_name: str = "agriguard-ac215-data"):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def load_yields(self) -> pd.DataFrame:
        """Load annual yield data."""
        logger.info("Loading yield data...")
        blob = self.bucket.blob("raw/yields/iowa_corn_yields_2017_2025.csv")
        content = blob.download_as_bytes()
        df = pd.read_csv(BytesIO(content))
        
        # Clean and standardize
        df['fips'] = df['fips'].astype(str).str.zfill(5)
        df = df.rename(columns={'yield_bu_per_acre': 'yield'})
        
        logger.info(f"Loaded {len(df)} yield records")
        return df[['year', 'fips', 'county', 'yield']]
    
    def load_et_data(self) -> pd.DataFrame:
        """Load MODIS ET data."""
        logger.info("Loading ET data...")
        blob = self.bucket.blob("processed/modis/et/iowa_counties_et_20170501_20251012.parquet")
        content = blob.download_as_bytes()
        df = pd.read_parquet(BytesIO(content))
        
        # Ensure date column
        if 'date' not in df.columns and 'time' in df.columns:
            df['date'] = pd.to_datetime(df['time'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"Loaded {len(df)} ET records")
        return df
    
    def load_lst_data(self) -> pd.DataFrame:
        """Load MODIS LST data from all parquet files in the folder."""
        logger.info("Loading LST data...")
        
        # List all parquet files in LST folder
        blobs = list(self.bucket.list_blobs(prefix="processed/modis/lst/"))
        parquet_blobs = [b for b in blobs if b.name.endswith('.parquet')]
        
        if not parquet_blobs:
            logger.warning("No LST parquet files found")
            return pd.DataFrame()
        
        dfs = []
        for blob in parquet_blobs:
            content = blob.download_as_bytes()
            df = pd.read_parquet(BytesIO(content))
            dfs.append(df)
        
        df = pd.concat(dfs, ignore_index=True)
        
        # Ensure date column
        if 'date' not in df.columns and 'time' in df.columns:
            df['date'] = pd.to_datetime(df['time'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"Loaded {len(df)} LST records from {len(parquet_blobs)} files")
        return df
    
    def load_ndvi_data(self) -> pd.DataFrame:
        """Load MODIS NDVI data."""
        logger.info("Loading NDVI data...")
        blob = self.bucket.blob("processed/modis/ndvi/iowa_counties_ndvi_20170501_20251012.parquet")
        content = blob.download_as_bytes()
        df = pd.read_parquet(BytesIO(content))
        
        # Ensure date column
        if 'date' not in df.columns and 'time' in df.columns:
            df['date'] = pd.to_datetime(df['time'])
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        logger.info(f"Loaded {len(df)} NDVI records")
        return df
    
    def save_to_gcs(self, df: pd.DataFrame, path: str):
        """Save DataFrame to GCS as parquet."""
        logger.info(f"Saving to gs://{self.bucket_name}/{path}")
        blob = self.bucket.blob(path)
        
        # Convert to parquet bytes
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        
        blob.upload_from_file(buffer, content_type='application/octet-stream')
        logger.info(f"Saved successfully")
