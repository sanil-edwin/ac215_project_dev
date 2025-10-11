"""
Handles uploading RAG pipeline artifacts to Google Cloud Storage.

Folder structure under gs://<bucket>/RAG_pipeline/:
- data/raw/          : Original PDF files
- data/processed/    : Extracted text files
- metadata/          : Per-document metadata JSON files
- logs/              : Ingestion run logs

! don't need indexes/ bc/ ChromaDB handles persistence
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict
from google.cloud import storage

log = logging.getLogger(__name__)


class GCSStorageManager:
    """
    Manages uploads to Google Cloud Storage with a predictable folder structure.
    """

    # Folder structure under base prefix (RAG_pipeline)
    FOLDERS = {
        "raw": "data/raw",               # Original PDFs
        "processed": "data/processed",   # Extracted text files
        "metadata": "metadata",          # Per-document metadata JSONs
        "logs": "logs",                  # Ingestion run logs
    }

    def __init__(self, bucket_name: str, base_prefix: str = "RAG_pipeline"):
        """
        Initialize GCS Storage Manager (set up characteristics of object instance)

        Args:
            bucket_name: Name of the GCS bucket (e.g., 'agriguard-ac215-data')
            base_prefix: Root folder inside the bucket (default: 'RAG_pipeline')
        """
        self.bucket_name = bucket_name
        self.base_prefix = base_prefix.strip("/")

        # Connects to Google Cloud Storage
        # Client uses GOOGLE_APPLICATION_CREDENTIALS env var
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

        log.info(f"Connected to GCS bucket: gs://{bucket_name}/{self.base_prefix}/")

    def _path(self, folder_key: str, filename: str) -> str:
        """
        Build the final GCS object path for a given folder key + filename.
        
        Args:
            folder_key: One of the keys in FOLDERS dict
            filename: Name of the file
            
        Returns:
            Full GCS path (e.g., "RAG_pipeline/data/raw/doc.pdf")
        """
        subdir = self.FOLDERS[folder_key].strip("/")
        return f"{self.base_prefix}/{subdir}/{filename}"

    def upload_file(self, local_path: str, folder_key: str, filename: str = None) -> str:
        """
        Upload a single local file to GCS.

        Args:
            local_path: Path to local file
            folder_key: One of the keys in FOLDERS (e.g., 'raw', 'processed')
            filename: Optional custom filename (defaults to basename of local_path)

        Returns:
            The gs:// URI of the uploaded object
        """
        if filename is None:
            filename = Path(local_path).name

        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        log.info(f"☁️  Uploaded file → {uri}")
        return uri

    def upload_json(self, data: dict, folder_key: str, filename: str) -> str:
        """
        Upload a Python dict as a JSON file to GCS.

        Args:
            data: Dictionary to serialize as JSON
            folder_key: One of the keys in FOLDERS
            filename: Name for the JSON file (should end in .json)

        Returns:
            The gs:// URI of the uploaded object
        """
        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(
            json.dumps(data, indent=2), 
            content_type="application/json"
        )
        
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        log.info(f"☁️  Uploaded JSON → {uri}")
        return uri

    def upload_string(self, content: str, folder_key: str, filename: str) -> str:
        """
        Upload string content to GCS.

        Args:
            content: String content to upload
            folder_key: One of the keys in FOLDERS
            filename: Name for the file

        Returns:
            The gs:// URI of the uploaded object
        """
        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_string(content, content_type="text/plain")
        
        uri = f"gs://{self.bucket_name}/{gcs_path}"
        log.info(f"☁️  Uploaded text → {uri}")
        return uri

    def file_exists(self, folder_key: str, filename: str) -> bool:
        """
        Check if a file exists in GCS.

        Args:
            folder_key: One of the keys in FOLDERS
            filename: Name of the file

        Returns:
            True if file exists, False otherwise
        """
        gcs_path = self._path(folder_key, filename)
        blob = self.bucket.blob(gcs_path)
        return blob.exists()

    def list_files(self, folder_key: str, prefix: str = "") -> List[str]:
        """
        List files in a GCS folder.

        Args:
            folder_key: One of the keys in FOLDERS
            prefix: Optional prefix to filter files

        Returns:
            List of filenames (not full paths)
        """
        folder_path = self.FOLDERS[folder_key].strip("/")
        full_prefix = f"{self.base_prefix}/{folder_path}/{prefix}"
        
        blobs = self.bucket.list_blobs(prefix=full_prefix)
        filenames = [Path(blob.name).name for blob in blobs]
        
        log.info(f"Found {len(filenames)} files in {folder_key}/{prefix}")
        return filenames


def main():
    """
    Test the GCS Storage Manager with 'python gcs_manger.py'
    """
    import tempfile
    
    # Initialize (requires GCS_BUCKET env var)
    bucket_name = os.getenv("GCS_BUCKET", "agriguard-ac215-data")
    gcs = GCSStorageManager(bucket_name)
    
    # Test upload file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content for GCS upload")
        temp_path = f.name
    
    try:
        uri = gcs.upload_file(temp_path, "processed", "test_upload.txt")
        print(f"Uploaded: {uri}")
        
        # Test upload JSON
        test_metadata = {
            "doc_id": "test123",
            "filename": "test.pdf",
            "uploaded_at": "2025-01-01T00:00:00"
        }
        uri = gcs.upload_json(test_metadata, "metadata", "test_metadata.json")
        print(f"Uploaded: {uri}")
        
        # Test file exists
        exists = gcs.file_exists("metadata", "test_metadata.json")
        print(f"File exists: {exists}")
        
        # Test list files
        files = gcs.list_files("metadata")
        print(f"Files in metadata: {files}")
        
    finally:
        # Cleanup
        os.unlink(temp_path)
        print("Test complete!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()