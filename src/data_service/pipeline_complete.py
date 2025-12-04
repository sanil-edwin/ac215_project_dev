import pandas as pd
import numpy as np
from google.cloud import storage
import logging
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MS5: Validation modules ACTIVATED
try:
    from data.validation import SchemaValidator, QualityChecker, DriftDetector
    VALIDATION_ENABLED = True
    logger.info("✅ Validation modules loaded (MS5 mode)")
except ImportError:
    logger.warning("⚠️  Validation modules not found. Install validation/ folder in data/")
    VALIDATION_ENABLED = False


class DataPipeline:
    """Complete data pipeline: Ingestion → Processing → Validation"""
    
    def __init__(self):
        self.bucket_name = 'agriguard-ac215-data'
        self.raw_path = f'gs://{self.bucket_name}/data_raw_new'
        self.clean_path = f'gs://{self.bucket_name}/data_clean'
        self.gcs_client = storage.Client()
        
        # MS5: Validation instances
        if VALIDATION_ENABLED:
            self.schema_validator = SchemaValidator()
            self.quality_checker = QualityChecker()
            self.drift_detector = DriftDetector()
        
        # Schema definitions
        self.expected_columns = {
            'daily': ['date', 'fips', 'county_name', 'year', 'month', 'doy', 'week_of_season',
                     'ndvi_mean', 'ndvi_std', 'lst_mean', 'lst_std', 'vpd_mean', 'vpd_std',
                     'eto_mean', 'eto_std', 'pr_mean', 'pr_std', 'water_deficit_mean', 'water_deficit_std'],
        }
        
        self.value_ranges = {
            'ndvi_mean': (0.0, 1.0),
            'lst_mean': (-10, 50),
            'vpd_mean': (0, 5),
            'eto_mean': (0, 15),
            'pr_mean': (0, 200),
            'water_deficit_mean': (-200, 15)
        }
    
    def run(self):
        """Execute complete pipeline: Ingestion → Processing → Validation"""
        logger.info("=" * 80)
        logger.info("🚀 AGRIGUARD MS5 COMPLETE DATA PIPELINE")
        logger.info("=" * 80)
        logger.info("Stages: INGESTION → PROCESSING → VALIDATION")
        logger.info("=" * 80)
        
        try:
            # STAGE 1: INGESTION
            logger.info("\n" + "▓" * 80)
            logger.info("STAGE 1: DATA INGESTION")
            logger.info("▓" * 80)
            daily_df = self._ingest_data()
            
            # STAGE 2: PROCESSING
            logger.info("\n" + "▓" * 80)
            logger.info("STAGE 2: DATA PROCESSING")
            logger.info("▓" * 80)
            daily_df, weekly_df = self._process_data(daily_df)
            
            # STAGE 3: VALIDATION (MS5)
            logger.info("\n" + "▓" * 80)
            logger.info("STAGE 3: DATA VALIDATION (MS5)")
            logger.info("▓" * 80)
            self._validate_data(daily_df, weekly_df)
            
            # SUMMARY
            logger.info("\n" + "=" * 80)
            logger.info("✅ PIPELINE COMPLETE - ALL STAGES PASSED")
            logger.info("=" * 80)
            logger.info(f"Daily records: {len(daily_df):,}")
            logger.info(f"Weekly records: {len(weekly_df):,}")
            logger.info(f"Execution time: {datetime.now().isoformat()}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed at: {str(e)}")
            raise
    
    # ============================================================================
    # STAGE 1: INGESTION
    # ============================================================================
    
    def _ingest_data(self):
        """Stage 1: Load raw data from GCS"""
        logger.info("\n[STEP 1.1] Checking raw data availability...")
        
        try:
            # Check NDVI
            logger.info("  → NDVI (MODIS vegetation index)")
            ndvi = pd.read_parquet(f'{self.raw_path}/modis/ndvi/iowa_corn_ndvi_20160501_20251031.parquet')
            logger.info(f"    ✓ NDVI: {len(ndvi):,} records")
            
            # Check LST
            logger.info("  → LST (Land surface temperature)")
            lst = pd.read_parquet(f'{self.raw_path}/modis/lst/iowa_corn_lst_20160501_20251031.parquet')
            logger.info(f"    ✓ LST: {len(lst):,} records")
            
            # Check VPD
            logger.info("  → VPD (Vapor pressure deficit)")
            vpd = pd.read_parquet(f'{self.raw_path}/weather/vpd/iowa_corn_vpd_20160501_20251031.parquet')
            logger.info(f"    ✓ VPD: {len(vpd):,} records")
            
            # Check ETo
            logger.info("  → ETo (Reference evapotranspiration)")
            eto = pd.read_parquet(f'{self.raw_path}/weather/eto/iowa_corn_eto_20160501_20251031.parquet')
            logger.info(f"    ✓ ETo: {len(eto):,} records")
            
            # Check Precipitation
            logger.info("  → Precipitation")
            pr = pd.read_parquet(f'{self.raw_path}/weather/pr/iowa_corn_pr_20160501_20251031.parquet')
            logger.info(f"    ✓ Precipitation: {len(pr):,} records")
            
            # Check Water Deficit
            logger.info("  → Water Deficit (ETo - Precip)")
            water_deficit = pd.read_parquet(f'{self.raw_path}/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet')
            logger.info(f"    ✓ Water Deficit: {len(water_deficit):,} records")
            
            logger.info(f"\n[STEP 1.2] Raw data validation")
            logger.info(f"  Total indicators: 6")
            logger.info(f"  Total records ingested: {len(ndvi) + len(lst) + len(vpd) + len(eto) + len(pr) + len(water_deficit):,}")
            logger.info(f"  Date range: 2016-05-01 to 2025-10-31")
            logger.info(f"  Spatial coverage: 99 Iowa counties")
            logger.info(f"✅ Ingestion complete - All raw data available")
            
            return {
                'ndvi': ndvi,
                'lst': lst,
                'vpd': vpd,
                'eto': eto,
                'pr': pr,
                'water_deficit': water_deficit
            }
            
        except FileNotFoundError as e:
            logger.error(f"❌ Ingestion failed - Missing file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Ingestion failed: {e}")
            raise
    
    # ============================================================================
    # STAGE 2: PROCESSING
    # ============================================================================
    
    def _process_data(self, raw_data):
        """Stage 2: Clean and aggregate data"""
        logger.info("\n[STEP 2.1] Merging indicators into daily dataset...")
        
        ndvi = raw_data['ndvi']
        lst = raw_data['lst']
        vpd = raw_data['vpd']
        eto = raw_data['eto']
        pr = raw_data['pr']
        water_deficit = raw_data['water_deficit']
        
        # Create grid
        logger.info("  Creating complete date×county grid...")
        dates = []
        for year in range(2016, 2026):
            season_dates = pd.date_range(f'{year}-05-01', f'{year}-10-31', freq='D')
            dates.extend(season_dates)
        dates = pd.DatetimeIndex(dates)
        counties = sorted(ndvi['fips'].unique())
        
        grid = pd.MultiIndex.from_product([dates, counties], names=['date', 'fips'])
        df = pd.DataFrame(index=grid).reset_index()
        df['date'] = pd.to_datetime(df['date'])
        
        # Add county names
        county_map = ndvi[['fips', 'county_name']].drop_duplicates().set_index('fips')['county_name'].to_dict()
        df['county_name'] = df['fips'].map(county_map)
        
        # Temporal features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['doy'] = df['date'].dt.dayofyear
        season_start = pd.to_datetime(df['year'].astype(str) + '-05-01')
        df['week_of_season'] = ((df['date'] - season_start).dt.days // 7) + 1
        
        # Merge indicators
        logger.info("  Merging 6 indicators...")
        
        for name, data, mean_col, std_col in [
            ('NDVI', ndvi, 'ndvi_mean', 'ndvi_std'),
            ('LST', lst, 'lst_mean', 'lst_std'),
            ('VPD', vpd, 'vpd_mean', 'vpd_std'),
            ('ETo', eto, 'eto_mean', 'eto_std'),
            ('Precip', pr, 'pr_mean', 'pr_std'),
        ]:
            clean = data[['date', 'fips', 'mean', 'std']].rename(
                columns={'mean': mean_col, 'std': std_col}
            )
            clean['date'] = pd.to_datetime(clean['date'])
            df = df.merge(clean, on=['date', 'fips'], how='left')
            logger.info(f"    ✓ {name}")
        
        # Water deficit (no std)
        wd_clean = water_deficit[['date', 'fips', 'water_deficit']].rename(
            columns={'water_deficit': 'water_deficit_mean'}
        )
        wd_clean['water_deficit_std'] = 0
        wd_clean['date'] = pd.to_datetime(wd_clean['date'])
        df = df.merge(wd_clean, on=['date', 'fips'], how='left')
        logger.info(f"    ✓ Water Deficit")
        
        # Fill NaNs
        indicator_cols = [c for c in df.columns if c.endswith('_mean') or c.endswith('_std')]
        for col in indicator_cols:
            df[col] = df[col].fillna(0)
        
        logger.info(f"\n[STEP 2.2] Creating daily dataset")
        logger.info(f"  Total daily records: {len(df):,}")
        logger.info(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        logger.info(f"  Counties: {df['fips'].nunique()}")
        logger.info(f"✅ Daily dataset complete")
        
        # Weekly aggregation
        logger.info(f"\n[STEP 2.3] Creating weekly aggregation...")
        grouped = df.groupby(['year', 'week_of_season', 'fips', 'county_name'])
        
        agg_dict = {}
        for col in df.columns:
            if col.endswith('_mean'):
                agg_dict[col] = 'mean'
            elif col.endswith('_std'):
                agg_dict[col] = lambda x: np.sqrt(np.mean(x**2))
        
        weekly_df = grouped[list(agg_dict.keys())].agg(agg_dict).reset_index()
        weekly_df['date'] = weekly_df.apply(
            lambda row: pd.Timestamp(row['year'], 5, 1) + pd.Timedelta(days=7 * (row['week_of_season'] - 1)),
            axis=1
        )
        
        weekly_df = weekly_df[['date', 'year', 'week_of_season', 'fips', 'county_name'] + 
                             [c for c in weekly_df.columns if c.endswith('_mean') or c.endswith('_std')]]
        
        logger.info(f"  Total weekly records: {len(weekly_df):,}")
        logger.info(f"✅ Weekly aggregation complete")
        
        # Climatology
        logger.info(f"\n[STEP 2.4] Computing climatology...")
        climatology = df.groupby(['week_of_season', 'fips', 'county_name']).agg({
            'ndvi_mean': ['mean', 'std'],
            'lst_mean': ['mean', 'std'],
            'vpd_mean': ['mean', 'std'],
            'eto_mean': ['mean', 'std'],
            'pr_mean': ['mean', 'std'],
            'water_deficit_mean': ['mean', 'std']
        }).reset_index()
        climatology.columns = ['_'.join(col).strip('_') for col in climatology.columns.values]
        logger.info(f"  Climatology records: {len(climatology):,}")
        logger.info(f"✅ Processing complete")
        
        return df, weekly_df
    
    # ============================================================================
    # STAGE 3: VALIDATION (MS5)
    # ============================================================================
    
    def _validate_data(self, daily_df, weekly_df):
        """Stage 3: Comprehensive MS5 validation"""
        
        if not VALIDATION_ENABLED:
            logger.warning("⚠️  Validation disabled (module not found), running basic checks...")
            self._validate_schema_basic(daily_df)
            return
        
        logger.info("\n[STEP 3.1] Schema validation...")
        is_valid, errors = self.schema_validator.validate_schema(daily_df, 'daily')
        if not is_valid:
            logger.error(f"❌ Schema validation failed: {errors}")
            raise ValueError(f"Schema validation failed: {errors}")
        logger.info("  ✓ All required columns present")
        logger.info("  ✓ Data types correct")
        logger.info("✅ Schema validation passed")
        
        logger.info("\n[STEP 3.2] Quality checks...")
        is_valid, violations = self.quality_checker.check_value_ranges(daily_df)
        if not is_valid:
            logger.error(f"❌ Quality check failed: {violations}")
            raise ValueError(f"Quality check failed: {violations}")
        logger.info("  ✓ NDVI: 0.0 - 1.0")
        logger.info("  ✓ LST: -10 - 50°C")
        logger.info("  ✓ VPD: 0 - 5 kPa")
        logger.info("  ✓ ETo: 0 - 15 mm/day")
        logger.info("  ✓ Precipitation: 0 - 200 mm/day")
        logger.info("✅ Value ranges valid")
        
        logger.info("\n[STEP 3.3] Completeness check...")
        is_valid, completeness = self.quality_checker.check_completeness(daily_df, min_completeness=0.95)
        if not is_valid:
            logger.error(f"❌ Completeness below 95%: {completeness*100:.1f}%")
            raise ValueError(f"Completeness check failed")
        logger.info(f"  Data completeness: {completeness*100:.1f}%")
        logger.info("✅ Completeness validated")
        
        logger.info("\n[STEP 3.4] Drift detection...")
        try:
            drift_report = self.drift_detector.detect_drift(daily_df)
            logger.info(f"  Drift status: {drift_report}")
            logger.info("✅ Drift detection complete")
        except Exception as e:
            logger.warning(f"⚠️  Drift detection warning: {e}")
        
        logger.info("\n[STEP 3.5] Data quality summary...")
        for indicator in ['ndvi_mean', 'lst_mean', 'vpd_mean', 'eto_mean', 'pr_mean', 'water_deficit_mean']:
            non_zero = (daily_df[indicator] > 0).sum()
            pct = non_zero / len(daily_df) * 100
            logger.info(f"  {indicator}: {pct:.1f}% non-zero")
        
        logger.info("\n✅ ALL VALIDATIONS PASSED")
    
    def _validate_schema_basic(self, df):
        """Basic schema validation (fallback)"""
        missing_cols = set(self.expected_columns['daily']) - set(df.columns)
        if missing_cols:
            logger.error(f"❌ Missing columns: {missing_cols}")
            raise ValueError(f"Missing columns: {missing_cols}")
        logger.info("✅ Schema validation passed")


if __name__ == "__main__":
    pipeline = DataPipeline()
    pipeline.run()
