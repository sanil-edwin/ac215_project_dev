import pandas as pd
import numpy as np
from google.cloud import storage
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCleaner:
    def __init__(self):
        self.bucket_name = 'agriguard-ac215-data'
        self.raw_path = f'gs://{self.bucket_name}/data_raw_new'
        self.clean_path = f'gs://{self.bucket_name}/data_clean'
        
    def run(self):
        """Main cleaning pipeline"""
        logger.info("Starting data cleaning pipeline...")
        
        # 1. Create daily clean data
        logger.info("Creating daily clean data...")
        daily_df = self.create_daily_clean_data()
        logger.info(f"Daily clean data created: {len(daily_df):,} rows")
        
        # 2. Create weekly clean data
        logger.info("Creating weekly clean data...")
        weekly_df = self.create_weekly_clean_data(daily_df)
        logger.info(f"Weekly clean data created: {len(weekly_df):,} rows")
        
        # 3. Create climatology
        logger.info("Computing climatology...")
        self.create_climatology(daily_df)
        
        # 4. Create metadata
        logger.info("Creating metadata...")
        self.create_metadata(daily_df, weekly_df)
        
        logger.info("✅ Data cleaning pipeline complete!")
        
    def create_daily_clean_data(self):
        """Load and merge all indicators into daily table"""
        
        # Load raw data
        logger.info("Loading NDVI...")
        ndvi = pd.read_parquet(f'{self.raw_path}/modis/ndvi/iowa_corn_ndvi_20160501_20251031.parquet')
        
        logger.info("Loading LST...")
        lst = pd.read_parquet(f'{self.raw_path}/modis/lst/iowa_corn_lst_20160501_20251031.parquet')
        
        logger.info("Loading VPD...")
        vpd = pd.read_parquet(f'{self.raw_path}/weather/vpd/iowa_corn_vpd_20160501_20251031.parquet')
        
        logger.info("Loading ETo...")
        eto = pd.read_parquet(f'{self.raw_path}/weather/eto/iowa_corn_eto_20160501_20251031.parquet')
        
        logger.info("Loading Precipitation...")
        pr = pd.read_parquet(f'{self.raw_path}/weather/pr/iowa_corn_pr_20160501_20251031.parquet')
        
        # Create complete date × county grid (ONLY growing season: May-Oct for each year)
        dates = []
        for year in range(2016, 2026):  # 2016 through 2025
            season_dates = pd.date_range(f'{year}-05-01', f'{year}-10-31', freq='D')
            dates.extend(season_dates)
        dates = pd.DatetimeIndex(dates)
        counties = sorted(ndvi['fips'].unique())
        
        logger.info(f"Creating grid: {len(dates)} dates × {len(counties)} counties = {len(dates) * len(counties):,} rows")
        
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
        
        # Compute week of season (Week 1 = May 1-7)
        season_start = pd.to_datetime(df['year'].astype(str) + '-05-01')
        df['week_of_season'] = ((df['date'] - season_start).dt.days // 7) + 1
        
        # Merge indicators - CONVERT DATE COLUMNS TO DATETIME FIRST
        logger.info("Merging NDVI...")
        ndvi_clean = ndvi[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'ndvi_mean', 'std': 'ndvi_std'}
        )
        ndvi_clean['date'] = pd.to_datetime(ndvi_clean['date'])
        df = df.merge(ndvi_clean, on=['date', 'fips'], how='left')
        
        logger.info("Merging LST...")
        lst_clean = lst[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'lst_mean', 'std': 'lst_std'}
        )
        lst_clean['date'] = pd.to_datetime(lst_clean['date'])
        df = df.merge(lst_clean, on=['date', 'fips'], how='left')
        
        logger.info("Merging VPD...")
        vpd_clean = vpd[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'vpd_mean', 'std': 'vpd_std'}
        )
        vpd_clean['date'] = pd.to_datetime(vpd_clean['date'])
        df = df.merge(vpd_clean, on=['date', 'fips'], how='left')
        
        logger.info("Merging ETo...")
        eto_clean = eto[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'eto_mean', 'std': 'eto_std'}
        )
        eto_clean['date'] = pd.to_datetime(eto_clean['date'])
        df = df.merge(eto_clean, on=['date', 'fips'], how='left')
        
        logger.info("Merging Precipitation...")
        pr_clean = pr[['date', 'fips', 'mean', 'std']].rename(
            columns={'mean': 'pr_mean', 'std': 'pr_std'}
        )
        pr_clean['date'] = pd.to_datetime(pr_clean['date'])
        df = df.merge(pr_clean, on=['date', 'fips'], how='left')
        
        # Handle NDVI gaps (forward-fill up to 16 days)
        logger.info("Filling NDVI gaps...")
        df = self._fill_ndvi_gaps(df)
        
        # Handle outliers
        logger.info("Removing outliers...")
        df = self._remove_outliers(df)
        
        # Add derived metrics
        logger.info("Computing derived metrics...")
        df['water_deficit'] = df['eto_mean'] - df['pr_mean']
        df = self._compute_days_since_rain(df)
        df = self._compute_seasonal_cumulative_precip(df)
        
        # Add quality flags
        logger.info("Adding quality flags...")
        df = self._add_quality_flags(df)
        
        # Add growth phase
        df = self._add_growth_phase(df)
        
        # Save
        output_path = f'{self.clean_path}/daily/iowa_corn_daily_20160501_20251031.parquet'
        logger.info(f"Saving to {output_path}...")
        df.to_parquet(output_path, index=False)
        
        return df
    
    def _fill_ndvi_gaps(self, df):
        """Forward-fill NDVI up to 16 days"""
        df = df.sort_values(['fips', 'date'])
        
        # Track original NDVI dates
        df['ndvi_source_date'] = df['date'].where(df['ndvi_mean'].notna())
        
        # Forward fill within each county
        for fips in df['fips'].unique():
            mask = df['fips'] == fips
            df.loc[mask, 'ndvi_mean'] = df.loc[mask, 'ndvi_mean'].fillna(method='ffill', limit=16)
            df.loc[mask, 'ndvi_std'] = df.loc[mask, 'ndvi_std'].fillna(method='ffill', limit=16)
            df.loc[mask, 'ndvi_source_date'] = df.loc[mask, 'ndvi_source_date'].fillna(method='ffill', limit=16)
        
        # Compute age
        df['ndvi_age_days'] = (df['date'] - pd.to_datetime(df['ndvi_source_date'])).dt.days
        df['ndvi_age_days'] = df['ndvi_age_days'].fillna(-1).astype(int)
        
        return df
    
    def _remove_outliers(self, df):
        """Clip extreme values"""
        for col in ['ndvi_mean', 'lst_mean', 'vpd_mean', 'eto_mean', 'pr_mean']:
            if col in df.columns:
                p01 = df[col].quantile(0.001)
                p99 = df[col].quantile(0.999)
                df[col] = df[col].clip(p01, p99)
        return df
    
    def _compute_days_since_rain(self, df):
        """Compute days since last significant rain (>2mm)"""
        df = df.sort_values(['fips', 'date'])
        df['rain_event'] = (df['pr_mean'] > 2).astype(int)
        
        days_since = []
        for fips in df['fips'].unique():
            county_df = df[df['fips'] == fips].copy()
            county_df['days_since_rain'] = 0
            
            days_counter = 0
            for idx, row in county_df.iterrows():
                if row['rain_event'] == 1:
                    days_counter = 0
                else:
                    days_counter += 1
                county_df.loc[idx, 'days_since_rain'] = days_counter
            
            days_since.append(county_df['days_since_rain'])
        
        df['days_since_rain'] = pd.concat(days_since).astype(int)
        df = df.drop('rain_event', axis=1)
        
        return df
    
    def _compute_seasonal_cumulative_precip(self, df):
        """Cumulative precipitation since May 1"""
        df = df.sort_values(['fips', 'date'])
        
        for fips in df['fips'].unique():
            for year in df['year'].unique():
                mask = (df['fips'] == fips) & (df['year'] == year)
                df.loc[mask, 'cumulative_precip_season'] = df.loc[mask, 'pr_mean'].fillna(0).cumsum()
        
        return df
    
    def _add_quality_flags(self, df):
        """Add quality flags for each indicator"""
        # NDVI quality
        df['ndvi_quality'] = 'good'
        df.loc[df['ndvi_age_days'] > 10, 'ndvi_quality'] = 'fair'
        df.loc[df['ndvi_age_days'] > 20, 'ndvi_quality'] = 'poor'
        df.loc[df['ndvi_mean'].isna(), 'ndvi_quality'] = 'missing'
        
        # Other indicators (simple missing check)
        for indicator in ['lst', 'vpd', 'eto', 'pr']:
            col = f'{indicator}_mean'
            quality_col = f'{indicator}_quality'
            df[quality_col] = 'good'
            df.loc[df[col].isna(), quality_col] = 'missing'
        
        return df
    
    def _add_growth_phase(self, df):
        """Label growth phase based on date"""
        def get_phase(row):
            month = row['month']
            day = row['date'].day
            
            if month == 5 or (month == 6 and day <= 20):
                return 'emergence_vegetative'
            elif (month == 6 and day > 20) or (month == 7 and day <= 31):
                return 'pollination'
            elif month == 8 or month == 9:
                return 'grain_fill'
            else:
                return 'maturity'
        
        df['growth_phase'] = df.apply(get_phase, axis=1)
        return df
    
    def create_weekly_clean_data(self, daily_df):
        """Aggregate daily to weekly"""
        daily_df['week_start'] = daily_df['date'] - pd.to_timedelta(daily_df['date'].dt.dayofweek, unit='D')
        
        agg_dict = {
            'county_name': 'first',
            'year': 'first',
            'week_of_season': 'first',
            'growth_phase': 'first',
            
            # Indicators - mean
            'ndvi_mean': 'mean',
            'lst_mean': 'mean',
            'vpd_mean': 'mean',
            'eto_mean': 'mean',
            'pr_mean': 'sum',  # Total weekly precip
            'water_deficit': 'mean',
            
            # NDVI freshness
            'ndvi_source_date': 'first',
            'ndvi_age_days': 'mean',
        }
        
        weekly = daily_df.groupby(['fips', 'week_start']).agg(agg_dict).reset_index()
        
        # Rename columns
        weekly = weekly.rename(columns={
            'pr_mean': 'pr_sum',
        })
        
        # Add NDVI freshness flag
        weekly['ndvi_freshness'] = 'fresh'
        weekly.loc[weekly['ndvi_age_days'] > 7, 'ndvi_freshness'] = 'stale'
        
        # Add additional weekly stats
        weekly_stats = daily_df.groupby(['fips', 'week_start']).agg({
            'lst_mean': 'max',
            'vpd_mean': 'max',
            'eto_mean': 'sum',
        }).reset_index()
        
        weekly_stats = weekly_stats.rename(columns={
            'lst_mean': 'lst_max',
            'vpd_mean': 'vpd_max',
            'eto_mean': 'eto_sum',
        })
        
        weekly = weekly.merge(weekly_stats, on=['fips', 'week_start'], how='left')
        
        # Calculate heat stress days
        heat_days = daily_df[daily_df['lst_mean'] > 32].groupby(['fips', 'week_start']).size().reset_index(name='lst_days_above_32C')
        weekly = weekly.merge(heat_days, on=['fips', 'week_start'], how='left')
        weekly['lst_days_above_32C'] = weekly['lst_days_above_32C'].fillna(0).astype(int)
        
        # Calculate rain days
        rain_days = daily_df[daily_df['pr_mean'] > 1].groupby(['fips', 'week_start']).size().reset_index(name='pr_days')
        weekly = weekly.merge(rain_days, on=['fips', 'week_start'], how='left')
        weekly['pr_days'] = weekly['pr_days'].fillna(0).astype(int)
        
        # Calculate water deficit sum
        deficit_sum = daily_df.groupby(['fips', 'week_start'])['water_deficit'].sum().reset_index(name='water_deficit_sum')
        weekly = weekly.merge(deficit_sum, on=['fips', 'week_start'], how='left')
        weekly = weekly.rename(columns={'water_deficit': 'water_deficit_mean'})
        
        # Calculate completeness
        completeness = daily_df.groupby(['fips', 'week_start']).apply(
            lambda x: x[['ndvi_mean', 'lst_mean', 'vpd_mean', 'eto_mean', 'pr_mean']].notna().all(axis=1).mean()
        ).reset_index(name='completeness')
        weekly = weekly.merge(completeness, on=['fips', 'week_start'], how='left')
        
        # Quality score
        weekly['quality_score'] = 'good'
        weekly.loc[weekly['completeness'] < 0.8, 'quality_score'] = 'fair'
        weekly.loc[weekly['completeness'] < 0.6, 'quality_score'] = 'poor'
        
        # Save
        output_path = f'{self.clean_path}/weekly/iowa_corn_weekly_20160501_20251031.parquet'
        logger.info(f"Saving to {output_path}...")
        weekly.to_parquet(output_path, index=False)
        
        return weekly
    
    def create_climatology(self, daily_df):
        """Compute historical normals by DOY"""
        # Use only complete years (2016-2024) for climatology
        # AND only growing season (May-Oct = DOY 121-304)
        clim_df = daily_df[
            (daily_df['year'] <= 2024) & 
            (daily_df['doy'] >= 121) & 
            (daily_df['doy'] <= 304)
        ].copy()
        
        climatology = clim_df.groupby(['fips', 'doy']).agg({
            'ndvi_mean': ['median', 'std', lambda x: x.quantile(0.1), lambda x: x.quantile(0.9)],
            'lst_mean': ['median', 'std', lambda x: x.quantile(0.9)],
            'vpd_mean': ['median', 'std'],
            'eto_mean': ['median', 'std'],
            'pr_mean': ['median', 'std'],
        }).reset_index()
        
        # Flatten columns
        climatology.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in climatology.columns.values]
        
        # Rename
        climatology = climatology.rename(columns={
            'ndvi_mean_median': 'ndvi_climatology_median',
            'ndvi_mean_std': 'ndvi_climatology_std',
            'ndvi_mean_<lambda_0>': 'ndvi_climatology_p10',
            'ndvi_mean_<lambda_1>': 'ndvi_climatology_p90',
            'lst_mean_median': 'lst_climatology_median',
            'lst_mean_std': 'lst_climatology_std',
            'lst_mean_<lambda>': 'lst_climatology_p90',
            'vpd_mean_median': 'vpd_climatology_median',
            'vpd_mean_std': 'vpd_climatology_std',
            'eto_mean_median': 'eto_climatology_median',
            'eto_mean_std': 'eto_climatology_std',
            'pr_mean_median': 'pr_climatology_median',
            'pr_mean_std': 'pr_climatology_std',
        })
        
        # Save
        output_path = f'{self.clean_path}/climatology/daily_normals_2016_2024.parquet'
        logger.info(f"Saving climatology to {output_path}...")
        climatology.to_parquet(output_path, index=False)
        
        return climatology
    
    def create_metadata(self, daily_df, weekly_df):
        """Create data quality report"""
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'date_range': {
                'start': daily_df['date'].min().strftime('%Y-%m-%d'),
                'end': daily_df['date'].max().strftime('%Y-%m-%d'),
            },
            'daily_records': int(len(daily_df)),
            'weekly_records': int(len(weekly_df)),
            'counties': int(daily_df['fips'].nunique()),
            'data_quality': {
                'ndvi': {
                    'completeness': float((daily_df['ndvi_mean'].notna().sum() / len(daily_df)) * 100),
                    'avg_age_days': float(daily_df[daily_df['ndvi_age_days'] >= 0]['ndvi_age_days'].mean()),
                },
                'lst': {
                    'completeness': float((daily_df['lst_mean'].notna().sum() / len(daily_df)) * 100),
                },
                'vpd': {
                    'completeness': float((daily_df['vpd_mean'].notna().sum() / len(daily_df)) * 100),
                },
                'eto': {
                    'completeness': float((daily_df['eto_mean'].notna().sum() / len(daily_df)) * 100),
                },
                'pr': {
                    'completeness': float((daily_df['pr_mean'].notna().sum() / len(daily_df)) * 100),
                },
            }
        }
        
        # Save as JSON
        import json
        output_path = f'{self.clean_path}/metadata/data_quality_report.json'
        logger.info(f"Saving metadata to {output_path}...")
        
        client = storage.Client()
        bucket = client.bucket(self.bucket_name)
        blob = bucket.blob('data_clean/metadata/data_quality_report.json')
        blob.upload_from_string(json.dumps(metadata, indent=2))
        
        return metadata

if __name__ == '__main__':
    cleaner = DataCleaner()
    cleaner.run()
