import os

GCS_BUCKET = os.getenv("GCS_BUCKET", "agriguard-ac215-data")
GCS_RAW_PATH = f"gs://{GCS_BUCKET}/data_raw_new"
GCS_CLEAN_PATH = f"gs://{GCS_BUCKET}/data_clean"
GCS_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "agriguard-ac215")

INDICATORS = {
    "ndvi": f"{GCS_RAW_PATH}/modis/ndvi/iowa_corn_ndvi_20160501_20251031.parquet",
    "lst": f"{GCS_RAW_PATH}/modis/lst/iowa_corn_lst_20160501_20251031.parquet",
    "et": f"{GCS_RAW_PATH}/modis/et/iowa_corn_et_20160501_20251031.parquet",
    "vpd": f"{GCS_RAW_PATH}/weather/vpd/iowa_corn_vpd_20160501_20251031.parquet",
    "eto": f"{GCS_RAW_PATH}/weather/eto/iowa_corn_eto_20160501_20251031.parquet",
    "pr": f"{GCS_RAW_PATH}/weather/pr/iowa_corn_pr_20160501_20251031.parquet",
    "water_deficit": f"{GCS_RAW_PATH}/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet",
}

OUTPUT_PATHS = {
    "daily_clean": f"{GCS_CLEAN_PATH}/daily/iowa_corn_clean_daily_20160501_20251031.parquet",
    "weekly_clean": f"{GCS_CLEAN_PATH}/weekly/iowa_corn_clean_weekly_20160501_20251031.parquet",
    "climatology": f"{GCS_CLEAN_PATH}/climatology/iowa_corn_climatology.parquet",
    "metadata": f"{GCS_CLEAN_PATH}/metadata/data_metadata.json",
}

AGGREGATION_METHODS = ["mean", "std", "min", "max"]
MISSING_VALUE_THRESHOLD = 0.3
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
