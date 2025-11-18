# Fix the path to use weekly aggregated data

with open('api_extended.py', 'r') as f:
    content = f.read()

# Replace the load function
old_load = '''def load_clean_data_from_gcs():
    """
    Load cleaned, ML-ready data from GCS
    Contains 824 county-year records with 150+ features
    """
    try:
        logger.info("Loading cleaned ML data from GCS...")
        client = storage.Client()
        bucket = client.bucket("agriguard-ac215-data")
        
        blob = bucket.blob("data_clean/aggregated_features_824_records.parquet")
        df = pd.read_parquet(pd.io.common.BytesIO(blob.download_as_bytes()))
        
        logger.info(f"✓ Loaded {len(df)} cleaned records with {len(df.columns)} features")
        logger.info(f"  Years: {df['year'].min()}-{df['year'].max()}")
        logger.info(f"  Counties: {df['county_fips'].nunique()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading cleaned data: {e}")
        return None'''

new_load = '''def load_clean_data_from_gcs():
    """
    Load weekly aggregated data from GCS
    Contains 26,928 weekly records (99 counties x ~27 weeks/year x 10 years)
    """
    try:
        logger.info("Loading weekly aggregated data from GCS...")
        client = storage.Client()
        bucket = client.bucket("agriguard-ac215-data")
        
        blob = bucket.blob("data_clean/weekly/iowa_corn_weekly_20160501_20251031.parquet")
        df = pd.read_parquet(pd.io.common.BytesIO(blob.download_as_bytes()))
        
        logger.info(f"✓ Loaded {len(df)} weekly records with {len(df.columns)} features")
        logger.info(f"  Years: {df['year'].min()}-{df['year'].max()}")
        logger.info(f"  Counties: {df['fips'].nunique()}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading weekly data: {e}")
        return None'''

content = content.replace(old_load, new_load)

with open('api_extended.py', 'w') as f:
    f.write(content)

print("✓ Fixed path to use weekly aggregated data")
