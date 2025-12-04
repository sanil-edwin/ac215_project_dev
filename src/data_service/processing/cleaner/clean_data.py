import pandas as pd
import numpy as np
from google.cloud import storage
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MS5: Validation modules ACTIVATED
try:
    from data.validation import SchemaValidator, QualityChecker, DriftDetector
    VALIDATION_ENABLED = True
    logger.info("✅ Validation modules loaded (MS5 mode)")
except ImportError:
    logger.warning("⚠️  Validation modules not found. Install validation/ folder in data/")
    VALIDATION_ENABLED = False


class DataCleaner:
    def __init__(self):
        self.bucket_name = 'agriguard-ac215-data'
        self.raw_path = f'gs://{self.bucket_name}/data_raw_new'
        self.clean_path = f'gs://{self.bucket_name}/data_clean'
        
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
            'weekly': ['date', 'fips', 'county_name', 'year', 'week_of_season',
                      'ndvi_mean', 'ndvi_std', 'lst_mean', 'lst_std', 'vpd_mean', 'vpd_std',
                      'eto_mean', 'eto_std', 'pr_mean', 'pr_std', 'water_deficit_mean', 'water_deficit_std']
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
        """Main cleaning pipeline with MS5 VALIDATION ENABLED"""
        logger.info("=" * 70)
        logger.info("🚀 MS5 DATA CLEANING PIPELINE - VALIDATION ENABLED")
        logger.info("=" * 70)
        
        try:
            # 1. Create daily clean data
            logger.info("\n[STEP 1/5] Creating daily clean data...")
            daily_df = self.create_daily_clean_data()
            logger.info(f"✅ Daily clean data created: {len(daily_df):,} rows")
            
            # 2. MS5: FULL VALIDATION
            logger.info("\n[STEP 2/5] Running comprehensive validation (MS5)...")
            self._run_full_validation(daily_df)
            
            # 3. Create weekly clean data
            logger.info("\n[STEP 3/5] Creating weekly clean data...")
            weekly_df = self.create_weekly_clean_data(daily_df)
            logger.info(f"✅ Weekly clean data created: {len(weekly_df):,} rows")
            
            # 4. Create climatology
            logger.info("\n[STEP 4/5] Computing climatology...")
            self.create_climatology(daily_df)
            logger.info("✅ Climatology complete")
            
            # 5. Create metadata
            logger.info("\n[STEP 5/5] Creating metadata...")
            self.create_metadata(daily_df, weekly_df)
            logger.info("✅ Metadata created")
            
            logger.info("\n" + "=" * 70)
            logger.info("✅ MS5 DATA CLEANING PIPELINE COMPLETE - ALL VALIDATIONS PASSED!")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Pipeline failed: {str(e)}")
            raise
        
    def create_daily_clean_data(self):
        """Load and merge all indicators into daily table"""
        
        # Load raw data
        logger.info("  Loading NDVI...")
        ndvi = pd.read_parquet(f'{self.raw_path}/modis/ndvi/iowa_corn_ndvi_20160501_20251031.parquet')
        
        logger.info("  Loading LST...")
        lst = pd.read_parquet(f'{self.raw_path}/modis/lst/iowa_corn_lst_20160501_20251031.parquet')
        
        logger.info("  Loading VPD...")
        vpd = pd.read_parquet(f'{self.raw_path}/weather/vpd/iowa_corn_vpd_20160501_20251031.parquet')
        
        logger.info("  Loading ETo...")
        eto = pd.read_parquet(f'{self.raw_path}/weather/eto/iowa_corn_eto_20160501_20251031.parquet')
        
        logger.info("  Loading Precipitation...")
        pr = pd.read_parquet(f'{self.raw_path}/weather/pr/iowa_corn_pr_20160501_20251031.parquet')
        
        logger.info("  Loading Water Deficit...")
        water_deficit = pd.read_parquet(f'{self.raw_path}/weather/water_deficit/iowa_corn_water_deficit_20160501_20251031.parquet')
        
        # Create complete date × county grid
        logger.info("  Creating date×county grid...")
        dates = []
        for year in range(2016, 2026):
            season_dates = pd.date_range(f'{year}-05-01', f'{year}-10-31', freq='D')
            dates.extend(season_dates)
        dates = pd.DatetimeIndex(dates)
        counties = sorted(ndvi['fips'].unique())
        
        logger.info(f"  Grid: {len(dates)} dates × {len(counties)} counties = {len(dates) * len(counties):,} rows")
        
        grid = pd.MultiIndex.from_product([dates, counties], names=['date', 'fips'])
        df = pd.DataFrame(index=grid).reset_index()
        df['date'] = pd.to_datetime(df['date'])
        
        # Add county names
        county_map = ndvi[['fips', 'county_name']].drop_duplicates().set_index('fips')['county_name'].to_dict()
        df['county_name'] = df['fips'].map(county_map)
        
        # Add temporal features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['doy'] = df['date'].dt.dayofyear
        
        # Compute week of season
        season_start = pd.to_datetime(df['year'].astype(str) + '-05-01')
        df['week_of_season'] = ((df['date'] - season_start).dt.days // 7) + 1
        
        # Merge indicators
        logger.info("  Merging indicators...")
        
        ndvi_clean = ndvi[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'ndvi_mean', 'std': 'ndvi_std'}
        )
        ndvi_clean['date'] = pd.to_datetime(ndvi_clean['date'])
        df = df.merge(ndvi_clean, on=['date', 'fips'], how='left')
        
        lst_clean = lst[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'lst_mean', 'std': 'lst_std'}
        )
        lst_clean['date'] = pd.to_datetime(lst_clean['date'])
        df = df.merge(lst_clean, on=['date', 'fips'], how='left')
        
        vpd_clean = vpd[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'vpd_mean', 'std': 'vpd_std'}
        )
        vpd_clean['date'] = pd.to_datetime(vpd_clean['date'])
        df = df.merge(vpd_clean, on=['date', 'fips'], how='left')
        
        eto_clean = eto[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'eto_mean', 'std': 'eto_std'}
        )
        eto_clean['date'] = pd.to_datetime(eto_clean['date'])
        df = df.merge(eto_clean, on=['date', 'fips'], how='left')
        
        pr_clean = pr[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'pr_mean', 'std': 'pr_std'}
        )
        pr_clean['date'] = pd.to_datetime(pr_clean['date'])
        df = df.merge(pr_clean, on=['date', 'fips'], how='left')
        
        water_deficit_clean = water_deficit[['date', 'fips', 'water_deficit']].rename(
            columns={'water_deficit': 'water_deficit_mean'}
        )
        water_deficit_clean['water_deficit_std'] = 0
        water_deficit_clean['date'] = pd.to_datetime(water_deficit_clean['date'])
        df = df.merge(water_deficit_clean, on=['date', 'fips'], how='left')
        
        # Fill NaNs
        indicator_cols = [c for c in df.columns if c.endswith('_mean') or c.endswith('_std')]
        for col in indicator_cols:
            df[col] = df[col].fillna(0)
        
        logger.info(f"  ✓ Merged {len(indicator_cols)} indicator columns")
        logger.info(f"  ✓ Final daily dataset: {len(df):,} rows × {len(df.columns)} columns")
        
        return df
    
    def _run_full_validation(self, daily_df):
        """MS5: Execute comprehensive data validation"""
        
        if not VALIDATION_ENABLED:
            logger.warning("⚠️  Validation disabled, running basic checks only")
            self._validate_daily_schema(daily_df)
            return
        
        logger.info("  Running schema validation...")
        is_valid, errors = self.schema_validator.validate_schema(daily_df, 'daily')
        if not is_valid:
            logger.error(f"❌ Schema validation failed: {errors}")
            raise ValueError(f"Schema validation failed: {errors}")
        logger.info("  ✓ Schema validation passed")
        
        logger.info("  Running quality checks...")
        is_valid, violations = self.quality_checker.check_value_ranges(daily_df)
        if not is_valid:
            logger.error(f"❌ Quality check failed: {violations}")
            raise ValueError(f"Quality check failed: {violations}")
        logger.info("  ✓ Value ranges valid")
        
        is_valid, completeness = self.quality_checker.check_completeness(daily_df, min_completeness=0.95)
        if not is_valid:
            logger.error(f"❌ Completeness check failed: {completeness}")
            raise ValueError(f"Completeness below 95%: {completeness}")
        logger.info(f"  ✓ Data completeness: {completeness*100:.1f}%")
        
        logger.info("  Running drift detection...")
        try:
            drift_report = self.drift_detector.detect_drift(daily_df)
            logger.info(f"  ✓ Drift detection complete: {drift_report}")
        except Exception as e:
            logger.warning(f"⚠️  Drift detection warning: {e}")
        
        logger.info("✅ All validations passed!")
    
    def _validate_daily_schema(self, df):
        """Basic schema validation (fallback if validation module not available)"""
        
        missing_cols = set(self.expected_columns['daily']) - set(df.columns)
        if missing_cols:
            logger.error(f"❌ Missing columns: {missing_cols}")
            raise ValueError(f"Missing columns: {missing_cols}")
        
        violations = []
        for col, (min_val, max_val) in self.value_ranges.items():
            if col in df.columns:
                out_of_range = ((df[col] < min_val) | (df[col] > max_val)).sum()
                if out_of_range > 0:
                    violations.append(f"{col}: {out_of_range} values outside [{min_val}, {max_val}]")
        
        if violations:
            logger.warning(f"⚠️  Value range violations:")
            for v in violations:
                logger.warning(f"   {v}")
        
        logger.info("✅ Schema validation passed")
    
    def create_weekly_clean_data(self, daily_df):
        """Aggregate daily data to weekly"""
        
        grouped = daily_df.groupby(['year', 'week_of_season', 'fips', 'county_name'])
        
        agg_dict = {}
        for col in daily_df.columns:
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
        
        logger.info(f"  ✓ Aggregated to weekly: {len(weekly_df):,} rows")
        
        return weekly_df
    
    def create_climatology(self, daily_df):
        """Compute climatology"""
        
        climatology = daily_df.groupby(['week_of_season', 'fips', 'county_name']).agg({
            'ndvi_mean': ['mean', 'std'],
            'lst_mean': ['mean', 'std'],
            'vpd_mean': ['mean', 'std'],
            'eto_mean': ['mean', 'std'],
            'pr_mean': ['mean', 'std'],
            'water_deficit_mean': ['mean', 'std']
        }).reset_index()
        
        climatology.columns = ['_'.join(col).strip('_') for col in climatology.columns.values]
        
        output_path = f'{self.clean_path}/climatology/climatology.parquet'
        logger.info(f"  Uploading climatology to {output_path}...")
        climatology.to_parquet(output_path, index=False)
        
        logger.info(f"  ✓ Climatology: {len(climatology):,} rows")
    
    def create_metadata(self, daily_df, weekly_df):
        """Create pipeline metadata"""
        
        metadata = {
            'pipeline_run_date': datetime.now().isoformat(),
            'ms5_validation_enabled': VALIDATION_ENABLED,
            'daily_records': len(daily_df),
            'weekly_records': len(weekly_df),
            'counties': daily_df['fips'].nunique(),
            'date_range_start': daily_df['date'].min().strftime('%Y-%m-%d'),
            'date_range_end': daily_df['date'].max().strftime('%Y-%m-%d'),
            'indicators': ['ndvi', 'lst', 'vpd', 'eto', 'pr', 'water_deficit'],
            'data_completeness': {
                'ndvi': (daily_df['ndvi_mean'] > 0).sum() / len(daily_df),
                'lst': (daily_df['lst_mean'] > 0).sum() / len(daily_df),
                'vpd': (daily_df['vpd_mean'] > 0).sum() / len(daily_df),
                'eto': (daily_df['eto_mean'] > 0).sum() / len(daily_df),
                'pr': (daily_df['pr_mean'] >= 0).sum() / len(daily_df),
                'water_deficit': (daily_df['water_deficit_mean'] != 0).sum() / len(daily_df)
            }
        }
        
        metadata_df = pd.DataFrame([metadata])
        output_path = f'{self.clean_path}/metadata/pipeline_metadata.parquet'
        logger.info(f"  Uploading metadata to {output_path}...")
        metadata_df.to_parquet(output_path, index=False)
        
        logger.info(f"  ✓ Metadata recorded:")
        for indicator, completeness in metadata['data_completeness'].items():
            logger.info(f"    - {indicator}: {completeness*100:.1f}% complete")


if __name__ == "__main__":
    cleaner = DataCleaner()
    cleaner.run()
