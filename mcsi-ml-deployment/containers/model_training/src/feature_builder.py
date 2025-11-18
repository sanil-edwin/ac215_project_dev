"""
Corn Yield Feature Engineering Pipeline

Builds ~150 ML-ready features per county-year from raw agricultural data.

Features include:
- Temporal aggregations by growth period
- Stress indicators (threshold-based)
- Historical anomalies
- Interaction features

Author: AgriGuard Team
Date: November 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CornYieldFeatureBuilder:
    """
    Build ML-ready features from raw corn indicators
    
    Creates ~150 features per county-year for yield prediction.
    """
    
    def __init__(self, bucket_name='agriguard-ac215-data'):
        """
        Initialize feature builder
        
        Args:
            bucket_name: GCS bucket containing data
        """
        self.bucket_name = bucket_name
        
        # Growth period definitions
        self.GROWTH_PERIODS = {
            'emergence': {'start_doy': 121, 'end_doy': 151, 'name': 'emergence'},
            'vegetative': {'start_doy': 152, 'end_doy': 195, 'name': 'vegetative'},
            'pollination': {'start_doy': 196, 'end_doy': 227, 'name': 'pollination'},
            'grain_fill': {'start_doy': 228, 'end_doy': 258, 'name': 'grain_fill'},
            'maturity': {'start_doy': 259, 'end_doy': 304, 'name': 'maturity'},
        }
        
        # Stress thresholds
        self.WATER_DEFICIT_THRESHOLDS = [2, 4, 6]  # mm/day
        self.LST_THRESHOLDS = [32, 35, 38]  # °C
        self.NDVI_ANOMALY_THRESHOLDS = [-0.10, -0.20, -0.30]
        self.PRECIP_THRESHOLDS = [0.1, 5, 25]  # mm/day
        
    def load_data(self, year_start=2016, year_end=2024) -> Dict[str, pd.DataFrame]:
        """
        Load all required data from GCS
        
        Args:
            year_start: Start year (inclusive)
            year_end: End year (inclusive)
            
        Returns:
            Dictionary of dataframes
        """
        logger.info(f"Loading data for {year_start}-{year_end}...")
        
        # Load yields (target variable)
        yields = pd.read_csv(
            f'gs://{self.bucket_name}/data_raw/yields/'
            f'iowa_corn_yields_2010_2024.csv'
        )
        yields = yields[
            (yields['year'] >= year_start) & 
            (yields['year'] <= year_end)
        ]
        logger.info(f"Loaded {len(yields)} yield records")
        
        # Load Water Deficit
        water_deficit = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/weather/water_deficit/'
            f'iowa_corn_water_deficit_20160501_20251031.parquet'
        )
        water_deficit['date'] = pd.to_datetime(water_deficit['date'])
        water_deficit['year'] = water_deficit['date'].dt.year
        water_deficit = water_deficit[
            water_deficit['year'].between(year_start, year_end)
        ]
        logger.info(f"Loaded {len(water_deficit)} water deficit records")
        
        # Load LST
        lst = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/modis/lst/'
            f'iowa_corn_lst_20160501_20251031.parquet'
        )
        lst['date'] = pd.to_datetime(lst['date'])
        lst['year'] = lst['date'].dt.year
        lst = lst[lst['year'].between(year_start, year_end)]
        logger.info(f"Loaded {len(lst)} LST records")
        
        # Load NDVI
        ndvi = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/modis/ndvi/'
            f'iowa_corn_ndvi_20160501_20251031.parquet'
        )
        ndvi['date'] = pd.to_datetime(ndvi['date'])
        ndvi['year'] = ndvi['date'].dt.year
        ndvi = ndvi[ndvi['year'].between(year_start, year_end)]
        logger.info(f"Loaded {len(ndvi)} NDVI records")
        
        # Load VPD
        vpd = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/weather/vpd/'
            f'iowa_corn_vpd_20160501_20251031.parquet'
        )
        vpd['date'] = pd.to_datetime(vpd['date'])
        vpd['year'] = vpd['date'].dt.year
        vpd = vpd[vpd['year'].between(year_start, year_end)]
        logger.info(f"Loaded {len(vpd)} VPD records")
        
        # Load ETo
        eto = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/weather/eto/'
            f'iowa_corn_eto_20160501_20251031.parquet'
        )
        eto['date'] = pd.to_datetime(eto['date'])
        eto['year'] = eto['date'].dt.year
        eto = eto[eto['year'].between(year_start, year_end)]
        logger.info(f"Loaded {len(eto)} ETo records")
        
        # Load Precipitation
        precip = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/weather/pr/'
            f'iowa_corn_pr_20160501_20251031.parquet'
        )
        precip['date'] = pd.to_datetime(precip['date'])
        precip['year'] = precip['date'].dt.year
        precip = precip[precip['year'].between(year_start, year_end)]
        logger.info(f"Loaded {len(precip)} precipitation records")
        
        return {
            'yields': yields,
            'water_deficit': water_deficit,
            'lst': lst,
            'ndvi': ndvi,
            'vpd': vpd,
            'eto': eto,
            'precip': precip
        }
    
    def filter_by_period(
        self, 
        df: pd.DataFrame, 
        year: int, 
        period: Dict
    ) -> pd.DataFrame:
        """
        Filter dataframe to specific growth period
        
        Args:
            df: Input dataframe with 'date' column
            year: Year to filter
            period: Growth period definition
            
        Returns:
            Filtered dataframe
        """
        df = df[df['year'] == year].copy()
        df['doy'] = df['date'].dt.dayofyear
        
        return df[
            (df['doy'] >= period['start_doy']) & 
            (df['doy'] <= period['end_doy'])
        ]
    
    def build_period_features(
        self,
        data: Dict[str, pd.DataFrame],
        county_fips: str,
        year: int
    ) -> Dict[str, float]:
        """
        Build features for all growth periods
        
        Args:
            data: Dictionary of dataframes
            county_fips: County FIPS code
            year: Year to process
            
        Returns:
            Dictionary of features
        """
        features = {}
        
        # Process each growth period
        for period_name, period_def in self.GROWTH_PERIODS.items():
            # Water Deficit features
            wd_period = self.filter_by_period(
                data['water_deficit'][data['water_deficit']['fips'] == county_fips],
                year,
                period_def
            )
            if len(wd_period) > 0:
                features[f'{period_name}_water_deficit_mean'] = wd_period['water_deficit'].mean()
                features[f'{period_name}_water_deficit_max'] = wd_period['water_deficit'].max()
                features[f'{period_name}_water_deficit_sum'] = wd_period['water_deficit'].sum()
                features[f'{period_name}_water_deficit_std'] = wd_period['water_deficit'].std()
                
                # Stress threshold features
                features[f'{period_name}_days_deficit_gt_2mm'] = (
                    wd_period['water_deficit'] > 2
                ).sum()
                features[f'{period_name}_days_deficit_gt_4mm'] = (
                    wd_period['water_deficit'] > 4
                ).sum()
                features[f'{period_name}_days_deficit_gt_6mm'] = (
                    wd_period['water_deficit'] > 6
                ).sum()
            else:
                features[f'{period_name}_water_deficit_mean'] = np.nan
                features[f'{period_name}_water_deficit_max'] = np.nan
                features[f'{period_name}_water_deficit_sum'] = np.nan
                features[f'{period_name}_water_deficit_std'] = np.nan
                features[f'{period_name}_days_deficit_gt_2mm'] = 0
                features[f'{period_name}_days_deficit_gt_4mm'] = 0
                features[f'{period_name}_days_deficit_gt_6mm'] = 0
            
            # LST features
            lst_period = self.filter_by_period(
                data['lst'][data['lst']['fips'] == county_fips],
                year,
                period_def
            )
            if len(lst_period) > 0:
                features[f'{period_name}_lst_mean'] = lst_period['mean'].mean()
                features[f'{period_name}_lst_max'] = lst_period['mean'].max()
                features[f'{period_name}_lst_std'] = lst_period['mean'].std()
                
                # Heat stress thresholds
                features[f'{period_name}_days_lst_gt_32C'] = (
                    lst_period['mean'] > 32
                ).sum()
                features[f'{period_name}_days_lst_gt_35C'] = (
                    lst_period['mean'] > 35
                ).sum()
                features[f'{period_name}_days_lst_gt_38C'] = (
                    lst_period['mean'] > 38
                ).sum()
            else:
                features[f'{period_name}_lst_mean'] = np.nan
                features[f'{period_name}_lst_max'] = np.nan
                features[f'{period_name}_lst_std'] = np.nan
                features[f'{period_name}_days_lst_gt_32C'] = 0
                features[f'{period_name}_days_lst_gt_35C'] = 0
                features[f'{period_name}_days_lst_gt_38C'] = 0
            
            # NDVI features
            ndvi_period = self.filter_by_period(
                data['ndvi'][data['ndvi']['fips'] == county_fips],
                year,
                period_def
            )
            if len(ndvi_period) > 0:
                features[f'{period_name}_ndvi_mean'] = ndvi_period['mean'].mean()
                features[f'{period_name}_ndvi_max'] = ndvi_period['mean'].max()
                features[f'{period_name}_ndvi_min'] = ndvi_period['mean'].min()
                features[f'{period_name}_ndvi_std'] = ndvi_period['mean'].std()
            else:
                features[f'{period_name}_ndvi_mean'] = np.nan
                features[f'{period_name}_ndvi_max'] = np.nan
                features[f'{period_name}_ndvi_min'] = np.nan
                features[f'{period_name}_ndvi_std'] = np.nan
            
            # Precipitation features
            precip_period = self.filter_by_period(
                data['precip'][data['precip']['fips'] == county_fips],
                year,
                period_def
            )
            if len(precip_period) > 0:
                features[f'{period_name}_precip_sum'] = precip_period['mean'].sum()
                features[f'{period_name}_precip_mean'] = precip_period['mean'].mean()
                features[f'{period_name}_precip_max'] = precip_period['mean'].max()
                features[f'{period_name}_days_no_rain'] = (
                    precip_period['mean'] < 0.1
                ).sum()
                features[f'{period_name}_days_heavy_rain'] = (
                    precip_period['mean'] > 25
                ).sum()
            else:
                features[f'{period_name}_precip_sum'] = np.nan
                features[f'{period_name}_precip_mean'] = np.nan
                features[f'{period_name}_precip_max'] = np.nan
                features[f'{period_name}_days_no_rain'] = 0
                features[f'{period_name}_days_heavy_rain'] = 0
            
            # ETo features
            eto_period = self.filter_by_period(
                data['eto'][data['eto']['fips'] == county_fips],
                year,
                period_def
            )
            if len(eto_period) > 0:
                features[f'{period_name}_eto_mean'] = eto_period['mean'].mean()
                features[f'{period_name}_eto_sum'] = eto_period['mean'].sum()
                features[f'{period_name}_eto_max'] = eto_period['mean'].max()
            else:
                features[f'{period_name}_eto_mean'] = np.nan
                features[f'{period_name}_eto_sum'] = np.nan
                features[f'{period_name}_eto_max'] = np.nan
            
            # VPD features
            vpd_period = self.filter_by_period(
                data['vpd'][data['vpd']['fips'] == county_fips],
                year,
                period_def
            )
            if len(vpd_period) > 0:
                features[f'{period_name}_vpd_mean'] = vpd_period['mean'].mean()
                features[f'{period_name}_vpd_max'] = vpd_period['mean'].max()
            else:
                features[f'{period_name}_vpd_mean'] = np.nan
                features[f'{period_name}_vpd_max'] = np.nan
        
        return features
    
    def build_interaction_features(
        self,
        base_features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Build interaction features from base features
        
        Args:
            base_features: Dictionary of base features
            
        Returns:
            Dictionary of interaction features
        """
        interaction_features = {}
        
        # Water × Heat stress interactions
        for period in self.GROWTH_PERIODS.keys():
            wd_key = f'{period}_water_deficit_mean'
            lst_key = f'{period}_lst_mean'
            
            if wd_key in base_features and lst_key in base_features:
                if not (np.isnan(base_features[wd_key]) or 
                        np.isnan(base_features[lst_key])):
                    interaction_features[f'{period}_water_heat_stress'] = (
                        base_features[wd_key] * base_features[lst_key]
                    )
        
        # Critical period combinations
        if ('pollination_water_deficit_mean' in base_features and
            'pollination_lst_mean' in base_features):
            poll_wd = base_features['pollination_water_deficit_mean']
            poll_lst = base_features['pollination_lst_mean']
            if not (np.isnan(poll_wd) or np.isnan(poll_lst)):
                interaction_features['pollination_combined_stress'] = (
                    poll_wd * 0.6 + (poll_lst - 30) * 0.4
                )
        
        # NDVI × Water stress
        for period in self.GROWTH_PERIODS.keys():
            ndvi_key = f'{period}_ndvi_mean'
            wd_key = f'{period}_water_deficit_mean'
            
            if ndvi_key in base_features and wd_key in base_features:
                if not (np.isnan(base_features[ndvi_key]) or 
                        np.isnan(base_features[wd_key])):
                    interaction_features[f'{period}_ndvi_water_interaction'] = (
                        (1 - base_features[ndvi_key]) * base_features[wd_key]
                    )
        
        return interaction_features
    
    def build_historical_features(
        self,
        data: Dict[str, pd.DataFrame],
        county_fips: str,
        year: int
    ) -> Dict[str, float]:
        """
        Build features based on historical baselines
        
        Args:
            data: Dictionary of dataframes
            county_fips: County FIPS code
            year: Current year
            
        Returns:
            Dictionary of historical features
        """
        historical_features = {}
        
        # Get previous years' yields for this county
        prev_yields = data['yields'][
            (data['yields']['fips'] == county_fips) &
            (data['yields']['year'] < year) &
            (data['yields']['year'] >= year - 5)
        ]
        
        if len(prev_yields) > 0:
            historical_features['yield_5yr_mean'] = prev_yields['yield_bu_per_acre'].mean()
            historical_features['yield_5yr_std'] = prev_yields['yield_bu_per_acre'].std()
            historical_features['yield_5yr_trend'] = self._calculate_trend(
                prev_yields['year'].values,
                prev_yields['yield_bu_per_acre'].values
            )
        else:
            historical_features['yield_5yr_mean'] = np.nan
            historical_features['yield_5yr_std'] = np.nan
            historical_features['yield_5yr_trend'] = np.nan
        
        # Previous year yield
        prev_year = data['yields'][
            (data['yields']['fips'] == county_fips) &
            (data['yields']['year'] == year - 1)
        ]
        if len(prev_year) > 0:
            historical_features['yield_prev_year'] = prev_year['yield_bu_per_acre'].iloc[0]
        else:
            historical_features['yield_prev_year'] = np.nan
        
        return historical_features
    
    def _calculate_trend(self, x: np.ndarray, y: np.ndarray) -> float:
        """Calculate linear trend (slope) from x, y data"""
        if len(x) < 2:
            return 0.0
        
        # Simple linear regression
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    def build_temporal_features(self, year: int) -> Dict[str, float]:
        """
        Build temporal features
        
        Args:
            year: Year
            
        Returns:
            Dictionary of temporal features
        """
        return {
            'year': year,
            'year_since_2016': year - 2016,
            'is_drought_year': 1 if year in [2012, 2018] else 0  # Known drought years
        }
    
    def build_features_for_county_year(
        self,
        data: Dict[str, pd.DataFrame],
        county_fips: str,
        year: int
    ) -> Dict[str, float]:
        """
        Build complete feature set for one county-year
        
        Args:
            data: Dictionary of dataframes
            county_fips: County FIPS code
            year: Year
            
        Returns:
            Dictionary of all features
        """
        logger.info(f"Building features for {county_fips} - {year}")
        
        # Initialize feature dictionary
        features = {
            'fips': county_fips,
            'year': year
        }
        
        # Build different feature groups
        period_features = self.build_period_features(data, county_fips, year)
        features.update(period_features)
        
        interaction_features = self.build_interaction_features(period_features)
        features.update(interaction_features)
        
        historical_features = self.build_historical_features(data, county_fips, year)
        features.update(historical_features)
        
        temporal_features = self.build_temporal_features(year)
        features.update(temporal_features)
        
        return features
    
    def build_all_features(
        self,
        year_start: int = 2016,
        year_end: int = 2024,
        save_to_gcs: bool = True
    ) -> pd.DataFrame:
        """
        Build features for all counties and years
        
        Args:
            year_start: Start year
            year_end: End year
            save_to_gcs: Whether to save to GCS
            
        Returns:
            DataFrame with all features
        """
        logger.info("="*60)
        logger.info("STARTING FEATURE ENGINEERING")
        logger.info("="*60)
        
        # Load data
        data = self.load_data(year_start, year_end)
        
        # Get unique county-year combinations from yields
        county_years = data['yields'][['fips', 'year']].drop_duplicates()
        logger.info(f"Building features for {len(county_years)} county-year combinations")
        
        # Build features for each county-year
        all_features = []
        for idx, row in county_years.iterrows():
            try:
                features = self.build_features_for_county_year(
                    data,
                    row['fips'],
                    row['year']
                )
                all_features.append(features)
                
                if (idx + 1) % 50 == 0:
                    logger.info(f"Processed {idx + 1}/{len(county_years)} county-years")
            
            except Exception as e:
                logger.error(f"Error processing {row['fips']} - {row['year']}: {e}")
        
        # Convert to DataFrame
        df_features = pd.DataFrame(all_features)
        
        # Merge with yields (target variable)
        df_features = df_features.merge(
            data['yields'][['fips', 'year', 'yield_bu_per_acre', 'county_name']],
            on=['fips', 'year'],
            how='left'
        )
        
        # Save to GCS
        if save_to_gcs:
            output_path = (
                f'gs://{self.bucket_name}/processed/features/'
                f'corn_yield_features_{year_start}_{year_end}.parquet'
            )
            df_features.to_parquet(output_path, index=False)
            logger.info(f"Saved features to {output_path}")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("FEATURE ENGINEERING COMPLETE")
        logger.info("="*60)
        logger.info(f"Total records: {len(df_features)}")
        logger.info(f"Total features: {len(df_features.columns)}")
        logger.info(f"Feature completeness: {(1 - df_features.isnull().sum().sum() / df_features.size) * 100:.1f}%")
        logger.info("\nFeature summary:")
        logger.info(f"  - Period features: ~{len([c for c in df_features.columns if any(p in c for p in self.GROWTH_PERIODS.keys())])}")
        logger.info(f"  - Interaction features: ~{len([c for c in df_features.columns if 'interaction' in c or 'combined' in c])}")
        logger.info(f"  - Historical features: ~{len([c for c in df_features.columns if '5yr' in c or 'prev' in c])}")
        logger.info(f"  - Temporal features: ~{len([c for c in df_features.columns if 'year' in c])}")
        logger.info("="*60 + "\n")
        
        return df_features


# Example usage
if __name__ == "__main__":
    # Initialize feature builder
    builder = CornYieldFeatureBuilder()
    
    # Build features for 2016-2024
    features_df = builder.build_all_features(
        year_start=2016,
        year_end=2024,
        save_to_gcs=True
    )
    
    print(f"\nFeature matrix shape: {features_df.shape}")
    print(f"Sample features:")
    print(features_df.head())
    print(f"\nTarget variable (yield) statistics:")
    print(features_df['yield_bu_per_acre'].describe())
