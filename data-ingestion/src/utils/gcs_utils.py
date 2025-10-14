"""
Google Cloud Storage utility functions for AgriGuard
Handles uploads, downloads, and file operations with GCS
"""

import os
import io
import logging
from pathlib import Path
from typing import Union, List, Optional
from google.cloud import storage
from google.cloud.exceptions import NotFound
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GCSManager:
    """Manager for Google Cloud Storage operations"""
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """
        Initialize GCS manager
        
        Args:
            bucket_name: Name of GCS bucket
            credentials_path: Path to service account JSON key (optional if using env var)
        """
        if credentials_path:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        
        logger.info(f"Initialized GCS Manager for bucket: {bucket_name}")
    
    def upload_file(self, local_path: str, gcs_path: str) -> str:
        """Upload a file to GCS"""
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {local_path} → {gcs_uri}")
        return gcs_uri
    
    def upload_dataframe(self, df: pd.DataFrame, gcs_path: str, format: str = 'csv') -> str:
        """Upload a pandas DataFrame directly to GCS"""
        blob = self.bucket.blob(gcs_path)
        
        if format == 'csv':
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            blob.upload_from_string(buffer.getvalue(), content_type='text/csv')
        elif format == 'parquet':
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)
            blob.upload_from_file(buffer, content_type='application/octet-stream')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded DataFrame ({len(df)} rows) → {gcs_uri}")
        return gcs_uri
    
    def upload_geodataframe(self, gdf: gpd.GeoDataFrame, gcs_path: str, 
                           format: str = 'geojson') -> str:
        """Upload a GeoDataFrame to GCS"""
        blob = self.bucket.blob(gcs_path)
        
        if format == 'geojson':
            # Convert to GeoJSON string
            geojson_str = gdf.to_json()
            blob.upload_from_string(geojson_str, content_type='application/geo+json')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded GeoDataFrame ({len(gdf)} features) → {gcs_uri}")
        return gcs_uri
    
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """
        Download a file from GCS to local path
        
        Args:
            gcs_path: Source path in GCS (without gs://bucket/)
            local_path: Destination local path
            
        Returns:
            Local file path
        """
        # Ensure directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        blob = self.bucket.blob(gcs_path)
        blob.download_to_filename(local_path)
        
        logger.info(f"Downloaded gs://{self.bucket_name}/{gcs_path} → {local_path}")
        return local_path
    
    def download_dataframe(self, gcs_path: str, format: str = 'csv') -> pd.DataFrame:
        """
        Download and read a DataFrame from GCS
        
        Args:
            gcs_path: Source path in GCS
            format: File format ('csv', 'parquet', 'json')
            
        Returns:
            DataFrame
        """
        blob = self.bucket.blob(gcs_path)
        
        if format == 'csv':
            data = blob.download_as_text()
            df = pd.read_csv(io.StringIO(data))
        elif format == 'parquet':
            data = blob.download_as_bytes()
            df = pd.read_parquet(io.BytesIO(data))
        elif format == 'json':
            data = blob.download_as_text()
            df = pd.read_json(io.StringIO(data), lines=True)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Downloaded DataFrame from {gcs_path} ({len(df)} rows)")
        return df

    def list_blobs(self, prefix: str = "", suffix: str = "") -> List[str]:
        """List all blobs in bucket with optional prefix/suffix filter"""
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        
        blob_names = [blob.name for blob in blobs]
        
        if suffix:
            blob_names = [name for name in blob_names if name.endswith(suffix)]
        
        logger.info(f"Found {len(blob_names)} blobs with prefix '{prefix}' and suffix '{suffix}'")
        return blob_names
    
    def blob_exists(self, gcs_path: str) -> bool:
        """Check if a blob exists in GCS"""
        blob = self.bucket.blob(gcs_path)
        return blob.exists()


def get_gcs_manager() -> GCSManager:
    """Factory function to create GCS manager from environment variables"""
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME environment variable not set")
    
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    return GCSManager(bucket_name, credentials_path)
