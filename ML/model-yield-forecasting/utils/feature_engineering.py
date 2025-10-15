"""Feature engineering for any-date yield forecasting - With NDVI + EVI."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class RollingWindowFeatureEngineer:
    """Create features for ANY date during the growing season."""
    
    def __init__(self, et_data: pd.DataFrame, lst_data: pd.DataFrame, ndvi_evi_data: pd.DataFrame):
        """Initialize with ET, LST, and NDVI/EVI data."""
        self.et_data = et_data.copy()
        self.lst_data = lst_data.copy()
        self.ndvi_evi_data = ndvi_evi_data.copy()  # Contains both NDVI and EVI
        
        # Prepare data (split NDVI and EVI)
        self._prepare_data()
        
        logger.info("Rolling window feature engineer initialized")
        logger.info(f"ET data shape: {self.et_data.shape}")
        logger.info(f"LST data shape: {self.lst_data.shape}")
        logger.info(f"NDVI data shape: {self.ndvi_data.shape}")
        logger.info(f"EVI data shape: {self.evi_data.shape}")
    
    def _prepare_data(self):
        """Prepare and filter data for feature engineering."""
        
        # Ensure FIPS is string with proper formatting
        for df in [self.et_data, self.lst_data, self.ndvi_evi_data]:
            if 'fips' in df.columns:
                df['fips'] = df['fips'].astype(str).str.zfill(5)
        
        # Filter ET data to only ET band (not PET)
        if 'band' in self.et_data.columns:
            self.et_data = self.et_data[self.et_data['band'] == 'ET'].copy()
            logger.info(f"Filtered to ET band: {len(self.et_data)} records")
        
        # For LST, use LST_Day (daytime temperatures)
        if 'band' in self.lst_data.columns:
            self.lst_data = self.lst_data[self.lst_data['band'] == 'LST_Day'].copy()
            logger.info(f"Filtered to LST_Day band: {len(self.lst_data)} records")
        
        # Split NDVI/EVI data into separate dataframes
        if 'band' in self.ndvi_evi_data.columns:
            self.ndvi_data = self.ndvi_evi_data[self.ndvi_evi_data['band'] == 'NDVI'].copy()
            self.evi_data = self.ndvi_evi_data[self.ndvi_evi_data['band'] == 'EVI'].copy()
            logger.info(f"Filtered to NDVI band: {len(self.ndvi_data)} records")
            logger.info(f"Filtered to EVI band: {len(self.evi_data)} records")
        else:
            # If no band column, create empty dataframes
            self.ndvi_data = pd.DataFrame()
            self.evi_data = pd.DataFrame()
            logger.warning("No 'band' column in NDVI/EVI data")
        
        # Calculate anomalies
        self._calculate_anomalies()
    
    def _calculate_anomalies(self):
        """Calculate anomalies for ET, LST, NDVI, and EVI data."""
        
        # ET anomalies
        if 'mean' in self.et_data.columns and 'fips' in self.et_data.columns and len(self.et_data) > 0:
            county_means = self.et_data.groupby('fips')['mean'].transform('mean')
            self.et_data['et_anomaly'] = self.et_data['mean'] - county_means
            logger.info("Calculated ET anomalies")
        
        # LST anomalies
        if 'mean' in self.lst_data.columns and 'fips' in self.lst_data.columns and len(self.lst_data) > 0:
            county_means = self.lst_data.groupby('fips')['mean'].transform('mean')
            self.lst_data['lst_anomaly'] = self.lst_data['mean'] - county_means
            logger.info("Calculated LST anomalies")
        
        # NDVI anomalies
        if 'mean' in self.ndvi_data.columns and 'fips' in self.ndvi_data.columns and len(self.ndvi_data) > 0:
            county_means = self.ndvi_data.groupby('fips')['mean'].transform('mean')
            self.ndvi_data['ndvi_anomaly'] = self.ndvi_data['mean'] - county_means
            logger.info("Calculated NDVI anomalies")
        
        # EVI anomalies
        if 'mean' in self.evi_data.columns and 'fips' in self.evi_data.columns and len(self.evi_data) > 0:
            county_means = self.evi_data.groupby('fips')['mean'].transform('mean')
            self.evi_data['evi_anomaly'] = self.evi_data['mean'] - county_means
            logger.info("Calculated EVI anomalies")
    
    def create_features_for_date(
        self, 
        year: int, 
        cutoff_date: datetime
    ) -> pd.DataFrame:
        """Create features for a specific cutoff date."""
        
        season_start = datetime(year, 5, 1)  # May 1
        
        if cutoff_date < season_start:
            logger.warning(f"Cutoff date {cutoff_date.date()} is before season start")
            return pd.DataFrame()
        
        logger.info(f"Creating features for {year}, cutoff: {cutoff_date.date()}")
        
        # Filter data up to cutoff date
        et_window = self.et_data[
            (self.et_data['date'] >= season_start) & 
            (self.et_data['date'] <= cutoff_date)
        ].copy()
        
        lst_window = self.lst_data[
            (self.lst_data['date'] >= season_start) & 
            (self.lst_data['date'] <= cutoff_date)
        ].copy()
        
        ndvi_window = self.ndvi_data[
            (self.ndvi_data['date'] >= season_start) & 
            (self.ndvi_data['date'] <= cutoff_date)
        ].copy()
        
        evi_window = self.evi_data[
            (self.evi_data['date'] >= season_start) & 
            (self.evi_data['date'] <= cutoff_date)
        ].copy()
        
        logger.info(f"  ET records: {len(et_window)}")
        logger.info(f"  LST records: {len(lst_window)}")
        logger.info(f"  NDVI records: {len(ndvi_window)}")
        logger.info(f"  EVI records: {len(evi_window)}")
        
        if len(et_window) == 0 and len(lst_window) == 0 and len(ndvi_window) == 0 and len(evi_window) == 0:
            logger.warning("No data available for this date range")
            return pd.DataFrame()
        
        # Get unique counties
        et_counties = set(et_window['fips'].unique()) if len(et_window) > 0 else set()
        lst_counties = set(lst_window['fips'].unique()) if len(lst_window) > 0 else set()
        ndvi_counties = set(ndvi_window['fips'].unique()) if len(ndvi_window) > 0 else set()
        evi_counties = set(evi_window['fips'].unique()) if len(evi_window) > 0 else set()
        
        fips_list = sorted(et_counties | lst_counties | ndvi_counties | evi_counties)
        
        logger.info(f"  Processing {len(fips_list)} counties")
        
        features_list = []
        
        for fips in fips_list:
            et_county = et_window[et_window['fips'] == fips] if len(et_window) > 0 else pd.DataFrame()
            lst_county = lst_window[lst_window['fips'] == fips] if len(lst_window) > 0 else pd.DataFrame()
            ndvi_county = ndvi_window[ndvi_window['fips'] == fips] if len(ndvi_window) > 0 else pd.DataFrame()
            evi_county = evi_window[evi_window['fips'] == fips] if len(evi_window) > 0 else pd.DataFrame()
            
            features = self._calculate_features(
                et_county, lst_county, ndvi_county, evi_county, year, fips, cutoff_date, season_start
            )
            features_list.append(features)
        
        df = pd.DataFrame(features_list)
        
        feature_cols = [c for c in df.columns if c not in ['year', 'fips', 'cutoff_date']]
        logger.info(f"  Created {len(feature_cols)} features for {len(df)} counties")
        
        return df
    
    def _calculate_features(
        self, 
        et_data: pd.DataFrame, 
        lst_data: pd.DataFrame,
        ndvi_data: pd.DataFrame,
        evi_data: pd.DataFrame,
        year: int,
        fips: str,
        cutoff_date: datetime,
        season_start: datetime
    ) -> Dict:
        """Calculate all features for a single county."""
        
        features = {
            'year': year,
            'fips': fips,
            'cutoff_date': cutoff_date.strftime('%Y-%m-%d')
        }
        
        # Temporal features
        days_since_start = (cutoff_date - season_start).days
        season_end = datetime(year, 9, 30)
        total_season_days = (season_end - season_start).days
        
        features['days_since_may1'] = days_since_start
        features['day_of_year'] = cutoff_date.timetuple().tm_yday
        features['data_completeness'] = days_since_start / total_season_days
        features['weeks_since_start'] = days_since_start / 7
        features['month'] = cutoff_date.month
        
        # Data availability
        features['has_et_data'] = 1 if len(et_data) > 0 else 0
        features['has_lst_data'] = 1 if len(lst_data) > 0 else 0
        features['has_ndvi_data'] = 1 if len(ndvi_data) > 0 else 0
        features['has_evi_data'] = 1 if len(evi_data) > 0 else 0
        features['et_observations'] = len(et_data)
        features['lst_observations'] = len(lst_data)
        features['ndvi_observations'] = len(ndvi_data)
        features['evi_observations'] = len(evi_data)
        
        # Calculate features from each data source
        if len(et_data) > 0:
            features.update(self._calculate_et_features(et_data))
        
        if len(lst_data) > 0:
            features.update(self._calculate_lst_features(lst_data))
        
        if len(ndvi_data) > 0:
            features.update(self._calculate_ndvi_features(ndvi_data))
        
        if len(evi_data) > 0:
            features.update(self._calculate_evi_features(evi_data))
        
        # Combined NDVI/EVI features
        if len(ndvi_data) > 0 and len(evi_data) > 0:
            features.update(self._calculate_combined_vi_features(ndvi_data, evi_data))
        
        # Monthly features
        features.update(self._get_monthly_features(et_data, lst_data, ndvi_data, evi_data, cutoff_date))
        
        # Growth stage features
        features.update(self._get_growth_stage_features(et_data, lst_data, ndvi_data, evi_data, cutoff_date))
        
        return features
    
    def _calculate_et_features(self, et_data: pd.DataFrame) -> Dict:
        """Calculate ET-based features."""
        features = {}
        
        if 'mean' not in et_data.columns:
            return features
        
        et_values = et_data['mean'].dropna()
        et_anomalies = et_data['et_anomaly'].dropna() if 'et_anomaly' in et_data.columns else et_values
        
        if len(et_values) > 0:
            features['et_mean'] = float(et_values.mean())
            features['et_median'] = float(et_values.median())
            features['et_std'] = float(et_values.std()) if len(et_values) > 1 else 0.0
            features['et_min'] = float(et_values.min())
            features['et_max'] = float(et_values.max())
            features['et_range'] = float(et_values.max() - et_values.min())
            
            if 'p25' in et_data.columns and 'p75' in et_data.columns:
                features['et_p25'] = float(et_data['p25'].mean())
                features['et_p75'] = float(et_data['p75'].mean())
            
            if len(et_anomalies) > 0:
                features['et_anomaly_mean'] = float(et_anomalies.mean())
                features['et_deficit_days'] = int((et_anomalies < -2.0).sum())
                features['et_severe_deficit_days'] = int((et_anomalies < -4.0).sum())
                features['et_surplus_days'] = int((et_anomalies > 2.0).sum())
                features['et_cumulative_deficit'] = float(et_anomalies[et_anomalies < 0].sum())
            
            if len(et_values) > 1:
                x = np.arange(len(et_values))
                trend_coef = np.polyfit(x, et_values, 1)
                features['et_trend'] = float(trend_coef[0])
            
            if len(et_values) >= 4:
                mid_point = len(et_values) // 2
                features['et_early_mean'] = float(et_values.iloc[:mid_point].mean())
                features['et_recent_mean'] = float(et_values.iloc[mid_point:].mean())
                features['et_early_vs_recent'] = features['et_recent_mean'] - features['et_early_mean']
            
            if 'std' in et_data.columns:
                features['et_spatial_variability'] = float(et_data['std'].mean())
        
        return features
    
    def _calculate_lst_features(self, lst_data: pd.DataFrame) -> Dict:
        """Calculate LST-based features."""
        features = {}
        
        if 'mean' not in lst_data.columns:
            return features
        
        lst_values = lst_data['mean'].dropna()
        lst_anomalies = lst_data['lst_anomaly'].dropna() if 'lst_anomaly' in lst_data.columns else pd.Series()
        
        if len(lst_values) > 0:
            features['lst_mean'] = float(lst_values.mean())
            features['lst_median'] = float(lst_values.median())
            features['lst_std'] = float(lst_values.std()) if len(lst_values) > 1 else 0.0
            features['lst_min'] = float(lst_values.min())
            features['lst_max'] = float(lst_values.max())
            features['lst_range'] = float(lst_values.max() - lst_values.min())
            
            if 'p25' in lst_data.columns and 'p75' in lst_data.columns:
                features['lst_p25'] = float(lst_data['p25'].mean())
                features['lst_p75'] = float(lst_data['p75'].mean())
            
            features['lst_heat_stress_days'] = int((lst_values > 30.0).sum())
            features['lst_extreme_heat_days'] = int((lst_values > 35.0).sum())
            features['lst_cold_stress_days'] = int((lst_values < 10.0).sum())
            
            if len(lst_anomalies) > 0:
                features['lst_anomaly_mean'] = float(lst_anomalies.mean())
                features['lst_hot_anomaly_days'] = int((lst_anomalies > 3.0).sum())
                features['lst_cold_anomaly_days'] = int((lst_anomalies < -3.0).sum())
            
            if len(lst_values) > 1:
                x = np.arange(len(lst_values))
                trend_coef = np.polyfit(x, lst_values, 1)
                features['lst_trend'] = float(trend_coef[0])
            
            if 'std' in lst_data.columns:
                features['lst_spatial_variability'] = float(lst_data['std'].mean())
        
        return features
    
    def _calculate_ndvi_features(self, ndvi_data: pd.DataFrame) -> Dict:
        """Calculate NDVI-based features."""
        features = {}
        
        if 'mean' not in ndvi_data.columns:
            return features
        
        ndvi_values = ndvi_data['mean'].dropna()
        ndvi_anomalies = ndvi_data['ndvi_anomaly'].dropna() if 'ndvi_anomaly' in ndvi_data.columns else pd.Series()
        
        if len(ndvi_values) > 0:
            features['ndvi_mean'] = float(ndvi_values.mean())
            features['ndvi_median'] = float(ndvi_values.median())
            features['ndvi_std'] = float(ndvi_values.std()) if len(ndvi_values) > 1 else 0.0
            features['ndvi_min'] = float(ndvi_values.min())
            features['ndvi_max'] = float(ndvi_values.max())
            features['ndvi_range'] = float(ndvi_values.max() - ndvi_values.min())
            
            if 'p25' in ndvi_data.columns and 'p75' in ndvi_data.columns:
                features['ndvi_p25'] = float(ndvi_data['p25'].mean())
                features['ndvi_p75'] = float(ndvi_data['p75'].mean())
            
            # Peak NDVI
            features['ndvi_peak'] = float(ndvi_values.max())
            if len(ndvi_data) > 0:
                peak_idx = ndvi_values.idxmax()
                peak_date = ndvi_data.loc[peak_idx, 'date']
                features['ndvi_peak_doy'] = peak_date.timetuple().tm_yday
            
            # Health indicators
            features['ndvi_healthy_days'] = int((ndvi_values > 0.6).sum())
            features['ndvi_stressed_days'] = int((ndvi_values < 0.4).sum())
            
            if len(ndvi_anomalies) > 0:
                features['ndvi_anomaly_mean'] = float(ndvi_anomalies.mean())
                features['ndvi_above_normal_days'] = int((ndvi_anomalies > 0.05).sum())
                features['ndvi_below_normal_days'] = int((ndvi_anomalies < -0.05).sum())
            
            if len(ndvi_values) > 1:
                x = np.arange(len(ndvi_values))
                trend_coef = np.polyfit(x, ndvi_values, 1)
                features['ndvi_trend'] = float(trend_coef[0])
            
            if len(ndvi_values) >= 4:
                mid_point = len(ndvi_values) // 2
                features['ndvi_early_mean'] = float(ndvi_values.iloc[:mid_point].mean())
                features['ndvi_recent_mean'] = float(ndvi_values.iloc[mid_point:].mean())
                features['ndvi_development'] = features['ndvi_recent_mean'] - features['ndvi_early_mean']
            
            if 'std' in ndvi_data.columns:
                features['ndvi_spatial_variability'] = float(ndvi_data['std'].mean())
        
        return features
    
    def _calculate_evi_features(self, evi_data: pd.DataFrame) -> Dict:
        """Calculate EVI-based features."""
        features = {}
        
        if 'mean' not in evi_data.columns:
            return features
        
        evi_values = evi_data['mean'].dropna()
        evi_anomalies = evi_data['evi_anomaly'].dropna() if 'evi_anomaly' in evi_data.columns else pd.Series()
        
        if len(evi_values) > 0:
            features['evi_mean'] = float(evi_values.mean())
            features['evi_median'] = float(evi_values.median())
            features['evi_std'] = float(evi_values.std()) if len(evi_values) > 1 else 0.0
            features['evi_min'] = float(evi_values.min())
            features['evi_max'] = float(evi_values.max())
            features['evi_range'] = float(evi_values.max() - evi_values.min())
            
            if 'p25' in evi_data.columns and 'p75' in evi_data.columns:
                features['evi_p25'] = float(evi_data['p25'].mean())
                features['evi_p75'] = float(evi_data['p75'].mean())
            
            # Peak EVI (important for dense canopy)
            features['evi_peak'] = float(evi_values.max())
            if len(evi_data) > 0:
                peak_idx = evi_values.idxmax()
                peak_date = evi_data.loc[peak_idx, 'date']
                features['evi_peak_doy'] = peak_date.timetuple().tm_yday
            
            # Health indicators (EVI thresholds different from NDVI)
            features['evi_healthy_days'] = int((evi_values > 0.4).sum())
            features['evi_stressed_days'] = int((evi_values < 0.2).sum())
            
            if len(evi_anomalies) > 0:
                features['evi_anomaly_mean'] = float(evi_anomalies.mean())
                features['evi_above_normal_days'] = int((evi_anomalies > 0.05).sum())
                features['evi_below_normal_days'] = int((evi_anomalies < -0.05).sum())
            
            if len(evi_values) > 1:
                x = np.arange(len(evi_values))
                trend_coef = np.polyfit(x, evi_values, 1)
                features['evi_trend'] = float(trend_coef[0])
            
            if len(evi_values) >= 4:
                mid_point = len(evi_values) // 2
                features['evi_early_mean'] = float(evi_values.iloc[:mid_point].mean())
                features['evi_recent_mean'] = float(evi_values.iloc[mid_point:].mean())
                features['evi_development'] = features['evi_recent_mean'] - features['evi_early_mean']
            
            if 'std' in evi_data.columns:
                features['evi_spatial_variability'] = float(evi_data['std'].mean())
        
        return features
    
    def _calculate_combined_vi_features(self, ndvi_data: pd.DataFrame, evi_data: pd.DataFrame) -> Dict:
        """Calculate combined NDVI/EVI features."""
        features = {}
        
        if 'mean' in ndvi_data.columns and 'mean' in evi_data.columns:
            ndvi_values = ndvi_data['mean'].dropna()
            evi_values = evi_data['mean'].dropna()
            
            if len(ndvi_values) > 0 and len(evi_values) > 0:
                ndvi_mean = ndvi_values.mean()
                evi_mean = evi_values.mean()
                
                # Ratio and difference (can indicate canopy structure)
                if evi_mean != 0:
                    features['ndvi_evi_ratio'] = float(ndvi_mean / evi_mean)
                features['ndvi_evi_diff'] = float(ndvi_mean - evi_mean)
                
                # Peak timing difference (NDVI peaks early, EVI peaks late)
                if len(ndvi_data) > 0 and len(evi_data) > 0:
                    ndvi_peak_idx = ndvi_values.idxmax()
                    evi_peak_idx = evi_values.idxmax()
                    ndvi_peak_doy = ndvi_data.loc[ndvi_peak_idx, 'date'].timetuple().tm_yday
                    evi_peak_doy = evi_data.loc[evi_peak_idx, 'date'].timetuple().tm_yday
                    features['peak_timing_diff'] = int(evi_peak_doy - ndvi_peak_doy)
        
        return features
    
    def _get_monthly_features(
        self, 
        et_data: pd.DataFrame, 
        lst_data: pd.DataFrame,
        ndvi_data: pd.DataFrame,
        evi_data: pd.DataFrame,
        cutoff_date: datetime
    ) -> Dict:
        """Calculate monthly aggregated features."""
        features = {}
        
        for month, month_name in [(5, 'may'), (6, 'june'), (7, 'july'), (8, 'aug'), (9, 'sept')]:
            if month > cutoff_date.month:
                continue
            
            # ET monthly
            if len(et_data) > 0 and 'mean' in et_data.columns:
                et_month = et_data[et_data['date'].dt.month == month]
                if len(et_month) > 0:
                    features[f'et_{month_name}_mean'] = float(et_month['mean'].mean())
            
            # LST monthly
            if len(lst_data) > 0 and 'mean' in lst_data.columns:
                lst_month = lst_data[lst_data['date'].dt.month == month]
                if len(lst_month) > 0:
                    features[f'lst_{month_name}_mean'] = float(lst_month['mean'].mean())
            
            # NDVI monthly
            if len(ndvi_data) > 0 and 'mean' in ndvi_data.columns:
                ndvi_month = ndvi_data[ndvi_data['date'].dt.month == month]
                if len(ndvi_month) > 0:
                    features[f'ndvi_{month_name}_mean'] = float(ndvi_month['mean'].mean())
            
            # EVI monthly
            if len(evi_data) > 0 and 'mean' in evi_data.columns:
                evi_month = evi_data[evi_data['date'].dt.month == month]
                if len(evi_month) > 0:
                    features[f'evi_{month_name}_mean'] = float(evi_month['mean'].mean())
        
        return features
    
    def _get_growth_stage_features(
        self, 
        et_data: pd.DataFrame, 
        lst_data: pd.DataFrame,
        ndvi_data: pd.DataFrame,
        evi_data: pd.DataFrame,
        cutoff_date: datetime
    ) -> Dict:
        """Calculate growth-stage specific features."""
        features = {}
        year = cutoff_date.year
        
        # Planting (May)
        if cutoff_date >= datetime(year, 5, 1) and len(ndvi_data) > 0 and 'mean' in ndvi_data.columns:
            planting_ndvi = ndvi_data[ndvi_data['date'].dt.month == 5]
            if len(planting_ndvi) > 0:
                features['planting_ndvi_mean'] = float(planting_ndvi['mean'].mean())
        
        # Vegetative (June - early July)
        if cutoff_date >= datetime(year, 6, 1) and len(ndvi_data) > 0 and 'mean' in ndvi_data.columns:
            veg_ndvi = ndvi_data[(ndvi_data['date'].dt.month >= 6) & (ndvi_data['date'].dt.month <= 7)]
            if len(veg_ndvi) > 0:
                features['vegetative_ndvi_max'] = float(veg_ndvi['mean'].max())
        
        # Reproductive (July 15 - Aug 15) - Critical for corn!
        if cutoff_date >= datetime(year, 7, 15):
            repro_end = min(cutoff_date, datetime(year, 8, 15))
            
            # EVI is better for reproductive stage (dense canopy)
            if len(evi_data) > 0 and 'mean' in evi_data.columns:
                repro_evi = evi_data[
                    (evi_data['date'] >= pd.Timestamp(year, 7, 15)) &
                    (evi_data['date'] <= repro_end)
                ]
                if len(repro_evi) > 0:
                    features['reproductive_evi_mean'] = float(repro_evi['mean'].mean())
                    features['reproductive_evi_max'] = float(repro_evi['mean'].max())
        
        # Grain fill (Aug 15 - Sept 30)
        if cutoff_date >= datetime(year, 8, 15):
            grain_end = min(cutoff_date, datetime(year, 9, 30))
            
            if len(evi_data) > 0 and 'mean' in evi_data.columns:
                grain_evi = evi_data[
                    (evi_data['date'] >= pd.Timestamp(year, 8, 15)) &
                    (evi_data['date'] <= grain_end)
                ]
                if len(grain_evi) > 0:
                    features['grain_fill_evi_mean'] = float(grain_evi['mean'].mean())
        
        return features
    
    def create_training_dataset(
        self, 
        years: List[int],
        forecast_dates: List[tuple] = None
    ) -> pd.DataFrame:
        """Create training dataset with multiple cutoff dates per year."""
        
        if forecast_dates is None:
            forecast_dates = [
                (6, 15), (6, 30),
                (7, 15), (7, 31),
                (8, 15), (8, 31),
                (9, 15), (9, 30)
            ]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Creating training dataset")
        logger.info(f"{'='*60}")
        logger.info(f"Years: {years}")
        logger.info(f"Forecast dates per year: {len(forecast_dates)}")
        
        all_samples = []
        
        for year in years:
            logger.info(f"\nProcessing year {year}...")
            
            for month, day in forecast_dates:
                cutoff_date = datetime(year, month, day)
                df = self.create_features_for_date(year, cutoff_date)
                
                if len(df) > 0:
                    all_samples.append(df)
        
        if not all_samples:
            logger.error("No training samples created!")
            return pd.DataFrame()
        
        result = pd.concat(all_samples, ignore_index=True)
        
        feature_cols = [c for c in result.columns 
                       if c not in ['year', 'fips', 'cutoff_date', 'yield']]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Training dataset created:")
        logger.info(f"  Total samples: {len(result)}")
        logger.info(f"  Years: {result['year'].nunique()}")
        logger.info(f"  Counties: {result['fips'].nunique()}")
        logger.info(f"  Features: {len(feature_cols)}")
        logger.info(f"  Cutoff dates: {result['cutoff_date'].nunique()}")
        logger.info(f"{'='*60}")
        
        return result