"""
Multi-Factor Corn Stress Index (MCSI) Calculator

Calculates county-level corn stress from:
- Water stress (45% weight) - from Water Deficit
- Heat stress (35% weight) - from LST
- Vegetation stress (20% weight) - from NDVI anomaly

Output: 0-100 stress score per county per week
- 0-30: Low stress
- 30-60: Moderate stress  
- 60-100: High stress

Author: AgriGuard Team
Date: November 2025
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCSICalculator:
    """
    Multi-Factor Corn Stress Index Calculator
    
    Combines water, heat, and vegetation stress into a single
    interpretable stress index for corn fields.
    """
    
    def __init__(self, bucket_name='agriguard-ac215-data'):
        """
        Initialize MCSI calculator
        
        Args:
            bucket_name: GCS bucket containing data
        """
        self.bucket_name = bucket_name
        
        # Component weights
        self.WEIGHTS = {
            'water': 0.45,
            'heat': 0.35,
            'vegetation': 0.20
        }
        
        # Growth stage multipliers
        self.GROWTH_STAGE_MULTIPLIERS = {
            'emergence': 0.8,      # May 1-31
            'vegetative': 1.2,     # June 1 - July 14
            'pollination': 1.5,    # July 15 - Aug 15 (CRITICAL)
            'grain_fill': 1.3,     # Aug 16 - Sep 15
            'maturity': 0.7        # Sep 16 - Oct 31
        }
        
        # Stress thresholds
        self.WATER_DEFICIT_SEVERE = 6.0  # mm/day
        self.WATER_DEFICIT_MODERATE = 4.0
        self.WATER_DEFICIT_MILD = 2.0
        
        self.LST_CRITICAL = 38.0  # °C
        self.LST_SEVERE = 35.0
        self.LST_MODERATE = 32.0
        
        self.NDVI_SEVERE_ANOMALY = -0.20
        self.NDVI_MODERATE_ANOMALY = -0.10
        
    def load_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """
        Load required data from GCS
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary of dataframes for each indicator
        """
        logger.info(f"Loading data from {start_date} to {end_date}")
        
        # Load Water Deficit
        water_deficit = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/weather/water_deficit/'
            f'iowa_corn_water_deficit_20160501_20251031.parquet'
        )
        water_deficit['date'] = pd.to_datetime(water_deficit['date'])
        water_deficit = water_deficit[
            (water_deficit['date'] >= start_date) & 
            (water_deficit['date'] <= end_date)
        ]
        
        # Load LST
        lst = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/modis/lst/'
            f'iowa_corn_lst_20160501_20251031.parquet'
        )
        lst['date'] = pd.to_datetime(lst['date'])
        lst = lst[
            (lst['date'] >= start_date) & 
            (lst['date'] <= end_date)
        ]
        
        # Load NDVI
        ndvi = pd.read_parquet(
            f'gs://{self.bucket_name}/data_raw_new/modis/ndvi/'
            f'iowa_corn_ndvi_20160501_20251031.parquet'
        )
        ndvi['date'] = pd.to_datetime(ndvi['date'])
        ndvi = ndvi[
            (ndvi['date'] >= start_date) & 
            (ndvi['date'] <= end_date)
        ]
        
        logger.info(f"Loaded {len(water_deficit)} water deficit records")
        logger.info(f"Loaded {len(lst)} LST records")
        logger.info(f"Loaded {len(ndvi)} NDVI records")
        
        return {
            'water_deficit': water_deficit,
            'lst': lst,
            'ndvi': ndvi
        }
    
    def calculate_water_stress(
        self, 
        water_deficit: pd.DataFrame, 
        county_fips: str,
        start_date: str,
        end_date: str
    ) -> float:
        """
        Calculate water stress component (0-100)
        
        Based on cumulative water deficit over the period.
        
        Args:
            water_deficit: Water deficit dataframe
            county_fips: County FIPS code
            start_date: Period start
            end_date: Period end
            
        Returns:
            Water stress score (0-100)
        """
        # Filter to county and date range
        county_data = water_deficit[
            (water_deficit['fips'] == county_fips) &
            (water_deficit['date'] >= start_date) &
            (water_deficit['date'] <= end_date)
        ]
        
        if len(county_data) == 0:
            logger.warning(f"No water deficit data for {county_fips}")
            return 0.0
        
        # Calculate cumulative deficit
        cumulative_deficit = county_data['water_deficit'].clip(lower=0).sum()
        
        # Days with severe stress
        severe_days = (county_data['water_deficit'] > self.WATER_DEFICIT_SEVERE).sum()
        moderate_days = (
            (county_data['water_deficit'] > self.WATER_DEFICIT_MODERATE) &
            (county_data['water_deficit'] <= self.WATER_DEFICIT_SEVERE)
        ).sum()
        
        # Normalize to 0-100
        # Severe stress if cumulative deficit > 150mm or 10+ severe days
        stress_score = min(100, (
            (cumulative_deficit / 150) * 40 +  # Cumulative component
            (severe_days / 10) * 40 +           # Severe days component
            (moderate_days / 20) * 20           # Moderate days component
        ))
        
        return stress_score
    
    def calculate_heat_stress(
        self,
        lst: pd.DataFrame,
        county_fips: str,
        start_date: str,
        end_date: str
    ) -> float:
        """
        Calculate heat stress component (0-100)
        
        Based on days exceeding temperature thresholds.
        
        Args:
            lst: LST dataframe
            county_fips: County FIPS code
            start_date: Period start
            end_date: Period end
            
        Returns:
            Heat stress score (0-100)
        """
        # Filter to county and date range
        county_data = lst[
            (lst['fips'] == county_fips) &
            (lst['date'] >= start_date) &
            (lst['date'] <= end_date)
        ]
        
        if len(county_data) == 0:
            logger.warning(f"No LST data for {county_fips}")
            return 0.0
        
        # Count days exceeding thresholds
        critical_days = (county_data['mean'] > self.LST_CRITICAL).sum()
        severe_days = (
            (county_data['mean'] > self.LST_SEVERE) &
            (county_data['mean'] <= self.LST_CRITICAL)
        ).sum()
        moderate_days = (
            (county_data['mean'] > self.LST_MODERATE) &
            (county_data['mean'] <= self.LST_SEVERE)
        ).sum()
        
        # Average temperature
        avg_temp = county_data['mean'].mean()
        
        # Normalize to 0-100
        # High stress if 5+ critical days or avg temp > 33°C
        stress_score = min(100, (
            (critical_days / 5) * 50 +        # Critical days (very high impact)
            (severe_days / 10) * 30 +         # Severe days
            (moderate_days / 20) * 10 +       # Moderate days
            max(0, (avg_temp - 30) / 5) * 10  # Overall high temperature
        ))
        
        return stress_score
    
    def calculate_vegetation_stress(
        self,
        ndvi: pd.DataFrame,
        county_fips: str,
        start_date: str,
        end_date: str,
        year: int
    ) -> float:
        """
        Calculate vegetation stress component (0-100)
        
        Based on NDVI anomaly from historical baseline.
        
        Args:
            ndvi: NDVI dataframe
            county_fips: County FIPS code
            start_date: Period start
            end_date: Period end
            year: Current year for baseline calculation
            
        Returns:
            Vegetation stress score (0-100)
        """
        # Current year data
        county_data = ndvi[
            (ndvi['fips'] == county_fips) &
            (ndvi['date'] >= start_date) &
            (ndvi['date'] <= end_date)
        ]
        
        if len(county_data) == 0:
            logger.warning(f"No NDVI data for {county_fips}")
            return 0.0
        
        # Historical baseline (previous 5 years)
        baseline_years = range(year - 5, year)
        baseline_data = ndvi[
            (ndvi['fips'] == county_fips) &
            (ndvi['date'].dt.year.isin(baseline_years)) &
            (ndvi['date'].dt.month.isin(county_data['date'].dt.month.unique()))
        ]
        
        if len(baseline_data) == 0:
            logger.warning(f"No baseline NDVI data for {county_fips}")
            # Use absolute NDVI if no baseline
            avg_ndvi = county_data['mean'].mean()
            if avg_ndvi < 0.40:
                return 80.0
            elif avg_ndvi < 0.60:
                return 40.0
            else:
                return 10.0
        
        # Calculate anomaly
        current_avg = county_data['mean'].mean()
        baseline_avg = baseline_data['mean'].mean()
        anomaly = current_avg - baseline_avg
        
        # Normalize to 0-100
        # High stress if anomaly < -0.20 (20% below normal)
        if anomaly <= self.NDVI_SEVERE_ANOMALY:
            stress_score = 80 + (abs(anomaly) - 0.20) / 0.10 * 20
        elif anomaly <= self.NDVI_MODERATE_ANOMALY:
            stress_score = 40 + (abs(anomaly) - 0.10) / 0.10 * 40
        elif anomaly < 0:
            stress_score = abs(anomaly) / 0.10 * 40
        else:
            stress_score = 0.0  # Above normal NDVI = no stress
        
        return min(100, stress_score)
    
    def get_growth_stage(self, date: datetime) -> str:
        """
        Determine growth stage from date
        
        Args:
            date: Date to check
            
        Returns:
            Growth stage name
        """
        doy = date.timetuple().tm_yday
        
        if 121 <= doy <= 151:  # May 1-31
            return 'emergence'
        elif 152 <= doy <= 195:  # June 1 - July 14
            return 'vegetative'
        elif 196 <= doy <= 227:  # July 15 - Aug 15
            return 'pollination'
        elif 228 <= doy <= 258:  # Aug 16 - Sep 15
            return 'grain_fill'
        elif 259 <= doy <= 304:  # Sep 16 - Oct 31
            return 'maturity'
        else:
            return 'off_season'
    
    def calculate_mcsi(
        self,
        county_fips: str,
        start_date: str,
        end_date: str,
        data: Dict[str, pd.DataFrame] = None
    ) -> Dict:
        """
        Calculate complete MCSI for a county and time period
        
        Args:
            county_fips: County FIPS code
            start_date: Period start (YYYY-MM-DD)
            end_date: Period end (YYYY-MM-DD)
            data: Optional pre-loaded data dictionary
            
        Returns:
            Dictionary with MCSI score and components
        """
        # Load data if not provided
        if data is None:
            data = self.load_data(start_date, end_date)
        
        # Parse dates
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        year = start.year
        
        # Calculate components
        water_stress = self.calculate_water_stress(
            data['water_deficit'], county_fips, start_date, end_date
        )
        
        heat_stress = self.calculate_heat_stress(
            data['lst'], county_fips, start_date, end_date
        )
        
        veg_stress = self.calculate_vegetation_stress(
            data['ndvi'], county_fips, start_date, end_date, year
        )
        
        # Determine growth stage multiplier
        # Use the most critical stage in the period
        growth_stage = self.get_growth_stage(start)
        multiplier = self.GROWTH_STAGE_MULTIPLIERS.get(growth_stage, 1.0)
        
        # Calculate weighted MCSI
        mcsi_base = (
            self.WEIGHTS['water'] * water_stress +
            self.WEIGHTS['heat'] * heat_stress +
            self.WEIGHTS['vegetation'] * veg_stress
        )
        
        mcsi_adjusted = min(100, mcsi_base * multiplier)
        
        # Determine stress level
        if mcsi_adjusted < 30:
            stress_level = 'Low'
            color = 'green'
        elif mcsi_adjusted < 60:
            stress_level = 'Moderate'
            color = 'yellow'
        else:
            stress_level = 'High'
            color = 'red'
        
        # Get county name
        county_name = data['water_deficit'][
            data['water_deficit']['fips'] == county_fips
        ]['county_name'].iloc[0] if len(data['water_deficit'][
            data['water_deficit']['fips'] == county_fips
        ]) > 0 else 'Unknown'
        
        return {
            'county_fips': county_fips,
            'county_name': county_name,
            'start_date': start_date,
            'end_date': end_date,
            'mcsi_score': round(mcsi_adjusted, 2),
            'stress_level': stress_level,
            'color': color,
            'components': {
                'water_stress': round(water_stress, 2),
                'heat_stress': round(heat_stress, 2),
                'vegetation_stress': round(veg_stress, 2)
            },
            'growth_stage': growth_stage,
            'growth_stage_multiplier': multiplier,
            'calculation_date': datetime.now().isoformat()
        }
    
    def calculate_all_counties(
        self,
        start_date: str,
        end_date: str,
        save_to_gcs: bool = True
    ) -> pd.DataFrame:
        """
        Calculate MCSI for all 99 Iowa counties
        
        Args:
            start_date: Period start (YYYY-MM-DD)
            end_date: Period end (YYYY-MM-DD)
            save_to_gcs: Whether to save results to GCS
            
        Returns:
            DataFrame with MCSI for all counties
        """
        logger.info(f"Calculating MCSI for all counties: {start_date} to {end_date}")
        
        # Load data once
        data = self.load_data(start_date, end_date)
        
        # Get unique counties
        counties = data['water_deficit']['fips'].unique()
        logger.info(f"Processing {len(counties)} counties")
        
        # Calculate MCSI for each county
        results = []
        for county_fips in counties:
            try:
                mcsi_result = self.calculate_mcsi(
                    county_fips, start_date, end_date, data
                )
                results.append(mcsi_result)
                
                if mcsi_result['stress_level'] == 'High':
                    logger.warning(
                        f"HIGH STRESS: {mcsi_result['county_name']} "
                        f"(MCSI: {mcsi_result['mcsi_score']})"
                    )
            except Exception as e:
                logger.error(f"Error processing {county_fips}: {e}")
        
        # Convert to DataFrame
        df_results = pd.DataFrame(results)
        
        # Save to GCS if requested
        if save_to_gcs:
            output_path = (
                f'gs://{self.bucket_name}/processed/mcsi/'
                f'mcsi_{start_date}_{end_date}.parquet'
            )
            df_results.to_parquet(output_path, index=False)
            logger.info(f"Saved results to {output_path}")
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("MCSI CALCULATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Period: {start_date} to {end_date}")
        logger.info(f"Counties processed: {len(df_results)}")
        logger.info(f"Average MCSI: {df_results['mcsi_score'].mean():.2f}")
        logger.info(f"\nStress Distribution:")
        logger.info(df_results['stress_level'].value_counts().to_string())
        logger.info(f"\nTop 5 Most Stressed Counties:")
        top_stressed = df_results.nlargest(5, 'mcsi_score')[
            ['county_name', 'mcsi_score', 'stress_level']
        ]
        logger.info(top_stressed.to_string(index=False))
        logger.info("="*60 + "\n")
        
        return df_results


# Example usage
if __name__ == "__main__":
    # Initialize calculator
    calculator = MCSICalculator()
    
    # Calculate MCSI for a specific week (most recent)
    from datetime import date, timedelta
    
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    # Process all counties
    results = calculator.calculate_all_counties(
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        save_to_gcs=True
    )
    
    print(f"\nProcessed {len(results)} counties")
    print(f"High stress counties: {(results['stress_level'] == 'High').sum()}")
