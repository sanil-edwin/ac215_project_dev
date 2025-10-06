"""Google Cloud Storage utilities"""
from google.cloud import storage
from loguru import logger
from pathlib import Path
import os


class GCSManager:
    """Manage Google Cloud Storage operations"""
    
    def __init__(self, bucket_name: str):
        """
        Initialize GCS Manager
        
        Args:
            bucket_name: GCS bucket name
        """
        self.bucket_name = bucket_name
        
        try:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"? GCS Manager initialized: gs://{bucket_name}")
        except Exception as e:
            logger.warning(f"??  GCS initialization warning: {str(e)}")
            logger.warning("Continuing without GCS (local mode)")
            self.client = None
            self.bucket = None
    
    def upload_file(self, source_path: str, destination_blob_name: str):
        """
        Upload a file to GCS
        
        Args:
            source_path: Local file path
            destination_blob_name: Destination path in GCS
        """
        if not self.bucket:
            logger.warning(f"??  GCS not available, skipping upload: {destination_blob_name}")
            return
        
        try:
            blob = self.bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_path)
            logger.success(f"??  Uploaded to GCS: gs://{self.bucket_name}/{destination_blob_name}")
        except Exception as e:
            logger.error(f"? GCS upload failed: {str(e)}")
    
    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists in the bucket"""
        if not self.bucket:
            return False
        
        blob = self.bucket.blob(blob_name)
        return blob.exists()
