"""
Google Cloud Storage utilities for AgriGuard project
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union
import geopandas as gpd
from google.cloud import storage
from google.api_core import exceptions

logger = logging.getLogger(__name__)


class GCSManager:
    """Manager for Google Cloud Storage operations"""
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS Manager
        
        Args:
            bucket_name: Name of the GCS bucket
            project_id: GCP project ID (optional, will use default if not provided)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        
        # Initialize storage client
        if project_id:
            self.client = storage.Client(project=project_id)
        else:
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(bucket_name)
        
        logger.info(f"Initialized GCS Manager for bucket: {bucket_name}")
    
    def blob_exists(self, blob_path: str) -> bool:
        """
        Check if a blob exists in the bucket
        
        Args:
            blob_path: Path to the blob in the bucket
            
        Returns:
            True if blob exists, False otherwise
        """
        blob = self.bucket.blob(blob_path)
        return blob.exists()
    
    def upload_file(self, local_path: str, gcs_path: str) -> str:
        """
        Upload a file to GCS
        
        Args:
            local_path: Local file path
            gcs_path: Destination path in GCS bucket
            
        Returns:
            GCS URI of uploaded file
        """
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded {local_path} to {uri}")
        return uri
    
    def upload_geodataframe(self, gdf: gpd.GeoDataFrame, gcs_path: str, 
                           format: str = 'geojson') -> str:
        """
        Upload a GeoDataFrame to GCS
        
        Args:
            gdf: GeoDataFrame to upload
            gcs_path: Destination path in GCS bucket
            format: Output format ('geojson' or 'gpkg')
            
        Returns:
            GCS URI of uploaded file
        """
        # Save to temporary file
        temp_path = Path(f"/tmp/{Path(gcs_path).name}")
        
        if format.lower() == 'geojson':
            gdf.to_file(temp_path, driver='GeoJSON')
        elif format.lower() == 'gpkg':
            gdf.to_file(temp_path, driver='GPKG')
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Upload
        uri = self.upload_file(str(temp_path), gcs_path)
        
        # Clean up
        temp_path.unlink()
        
        return uri
    
    def download_file(self, gcs_path: str, local_path: str) -> str:
        """
        Download a file from GCS
        
        Args:
            gcs_path: Path to blob in GCS bucket
            local_path: Local destination path
            
        Returns:
            Local file path
        """
        blob = self.bucket.blob(gcs_path)
        
        # Create parent directories if they don't exist
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        blob.download_to_filename(local_path)
        logger.info(f"Downloaded gs://{self.bucket_name}/{gcs_path} to {local_path}")
        return local_path
    
    def list_blobs(self, prefix: str = "") -> list:
        """
        List all blobs with a given prefix
        
        Args:
            prefix: Prefix to filter blobs
            
        Returns:
            List of blob names
        """
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]
    
    def delete_blob(self, gcs_path: str) -> None:
        """
        Delete a blob from GCS
        
        Args:
            gcs_path: Path to blob in GCS bucket
        """
        blob = self.bucket.blob(gcs_path)
        blob.delete()
        logger.info(f"Deleted gs://{self.bucket_name}/{gcs_path}")


def get_gcs_manager() -> GCSManager:
    """
    Get GCS manager from environment variables
    
    Environment variables:
        GCS_BUCKET_NAME: Name of the GCS bucket
        GCP_PROJECT_ID: GCP project ID (optional)
        GOOGLE_APPLICATION_CREDENTIALS: Path to service account key (optional)
    
    Returns:
        Initialized GCSManager
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME environment variable not set")
    
    project_id = os.getenv("GCP_PROJECT_ID")
    
    return GCSManager(bucket_name=bucket_name, project_id=project_id)
