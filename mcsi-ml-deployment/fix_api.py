import re

with open('src/api.py', 'r') as f:
    content = f.read()

# Add GCS download logic after imports
gcs_code = '''
from google.cloud import storage
import os

def download_models_from_gcs():
    """Download models from GCS to local directory"""
    bucket_name = "agriguard-ac215-data"
    model_path = os.getenv("MODEL_PATH", "models/corn_yield_model/")
    local_dir = Path('./models')
    local_dir.mkdir(exist_ok=True)
    
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        for blob in bucket.list_blobs(prefix=model_path):
            if blob.name.endswith(('.txt', '.pkl', '.json')):
                filename = blob.name.split('/')[-1]
                local_path = local_dir / filename
                blob.download_to_filename(local_path)
                logger.info(f"Downloaded {filename}")
    except Exception as e:
        logger.error(f"Error downloading models: {e}")
        raise
'''

# Insert after imports (after line ~25)
content = content.replace(
    'logging.basicConfig(level=logging.INFO)',
    'logging.basicConfig(level=logging.INFO)\n' + gcs_code
)

# Add download call in load_models function
content = content.replace(
    'logger.info("Loading models...")',
    'logger.info("Loading models...")\n    download_models_from_gcs()'
)

with open('src/api.py', 'w') as f:
    f.write(content)

print("Fixed!")
