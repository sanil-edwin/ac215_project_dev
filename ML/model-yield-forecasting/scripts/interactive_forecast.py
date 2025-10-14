"""Interactive menu-driven yield forecasting tool - With NDVI + EVI."""

import sys
sys.path.append('/app')

from utils.data_loader import DataLoader
from utils.feature_engineering import RollingWindowFeatureEngineer
import pandas as pd
import numpy as np
import joblib
import json
from io import BytesIO
import logging
from datetime import datetime, timedelta

# Suppress info logs for cleaner UI
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class InteractiveForecast:
    """Interactive forecasting with menu selection."""
    
    def __init__(self):
        print("\n" + "="*70)
        print("IOWA CORN YIELD FORECASTING SYSTEM")
        print("With NDVI + EVI Multi-Sensor Fusion")
        print("="*70)
        print("\nLoading model and data...")
        
        self.loader = DataLoader()
        self.load_model()
        self.load_counties()
        
        print("✓ Model loaded successfully!")
        print("✓ County data loaded!")
    
    def load_model(self):
        """Load trained model from GCS."""
        # Load model
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_model_ndvi_evi.joblib")
        model_bytes = blob.download_as_bytes()
        self.model = joblib.load(BytesIO(model_bytes))
        
        # Load scaler
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_scaler_ndvi_evi.joblib")
        scaler_bytes = blob.download_as_bytes()
        self.scaler = joblib.load(BytesIO(scaler_bytes))
        
        # Load feature names
        blob = self.loader.bucket.blob("model_yield_forecasting/models/rolling_window_features_ndvi_evi.json")
        features_dict = json.loads(blob.download_as_string())
        self.feature_names = features_dict['features']
        
        # Load metrics for uncertainty
        blob = self.loader.bucket.blob("model_yield_forecasting/models/training_metrics_ndvi_evi.json")
        self.metrics = json.loads(blob.download_as_string())
    
    def load_counties(self):
        """Load county list from yield data."""
        yields_df = self.loader.load_yields()
        
        # Get unique counties with names
        county_info = yields_df[['fips', 'county']].drop_duplicates().sort_values('county')
        
        self.counties = []
        for _, row in county_info.iterrows():
            self.counties.append({
                'fips': row['fips'],
                'name': row['county'],
                'display': f"{row['county']} County (FIPS: {row['fips']})"
            })
    
    def display_counties(self):
        """Display county selection menu."""
        print("\n" + "="*70)
        print("SELECT A COUNTY")
        print("="*70)
        
        # Display in 2 columns
        half = len(self.counties) // 2
        
        for i in range(half):
            left_idx = i
            right_idx = i + half
            
            left = f"{left_idx + 1:2d}. {self.counties[left_idx]['name'][:25]:<25}"
            
            if right_idx < len(self.counties):
                right = f"{right_idx + 1:2d}. {self.counties[right_idx]['name'][:25]:<25}"
            else:
                right = ""
            
            print(f"  {left}  {right}")
        
        # Handle odd number of counties
        if len(self.counties) % 2 == 1:
            last_idx = len(self.counties) - 1
            print(f"  {last_idx + 1:2d}. {self.counties[last_idx]['name']}")
        
        print("\n  0. Exit")
        print("="*70)
    
    def select_county(self):
        """Let user select a county."""
        self.display_counties()
        
        while True:
            try:
                choice = input("\nEnter county number: ").strip()
                
                if choice == '0':
                    return None
                
                choice = int(choice)
                
                if 1 <= choice <= len(self.counties):
                    selected = self.counties[choice - 1]
                    print(f"\n✓ Selected: {selected['display']}")
                    return selected
                else:
                    print(f"Please enter a number between 0 and {len(self.counties)}")
            
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                return None
    
    def select_date(self):
        """Let user select a forecast date."""
        print("\n" + "="*70)
        print("SELECT FORECAST DATE")
        print("="*70)
        print("\nYou can choose from:")
        print("  1. Pre-defined dates (recommended)")
        print("  2. Custom date (YYYY-MM-DD)")
        print("  3. Compare multiple dates")
        print("  0. Back to county selection")
        print("="*70)
        
        while True:
            choice = input("\nYour choice: ").strip()
            
            if choice == '0':
                return None, None
            
            elif choice == '1':
                return self.select_predefined_date()
            
            elif choice == '2':
                return self.select_custom_date()
            
            elif choice == '3':
                return 'compare', None
            
            else:
                print("Please enter 0, 1, 2, or 3")
    
    def select_predefined_date(self):
        """Select from predefined dates."""
        print("\n" + "="*70)
        print("PRE-DEFINED FORECAST DATES (2025)")
        print("="*70)
        
        dates = [
            datetime(2025, 6, 15),
            datetime(2025, 6, 30),
            datetime(2025, 7, 15),
            datetime(2025, 7, 31),
            datetime(2025, 8, 15),
            datetime(2025, 8, 31),
            datetime(2025, 9, 15),
            datetime(2025, 9, 30),
        ]
        
        for i, date in enumerate(dates, 1):
            days_from_may1 = (date - datetime(2025, 5, 1)).days
            completeness = days_from_may1 / 153 * 100  # 153 days = May 1 to Sept 30
            print(f"  {i}. {date.strftime('%B %d, %Y')} (Data: {completeness:.0f}% complete)")
        
        print("\n  0. Back")
        print("="*70)
        
        while True:
            try:
                choice = input("\nSelect date number: ").strip()
                
                if choice == '0':
                    return None, None
                
                choice = int(choice)
                
                if 1 <= choice <= len(dates):
                    selected_date = dates[choice - 1]
                    print(f"\n✓ Selected: {selected_date.strftime('%B %d, %Y')}")
                    return 'single', selected_date
                else:
                    print(f"Please enter a number between 0 and {len(dates)}")
            
            except ValueError:
                print("Please enter a valid number")
    
    def select_custom_date(self):
        """Enter a custom date."""
        print("\n" + "="*70)
        print("CUSTOM DATE ENTRY")
        print("="*70)
        print("\nEnter a date between May 1 and September 30, 2025")
        print("Format: YYYY-MM-DD (e.g., 2025-07-20)")
        print("\nType 'back' to return to menu")
        print("="*70)
        
        while True:
            date_str = input("\nEnter date: ").strip()
            
            if date_str.lower() == 'back':
                return None, None
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Validate date range
                min_date = datetime(2025, 5, 1)
                max_date = datetime(2025, 9, 30)
                
                if min_date <= date <= max_date:
                    print(f"\n✓ Selected: {date.strftime('%B %d, %Y')}")
                    return 'single', date
                else:
                    print("Date must be between May 1 and September 30, 2025")
            
            except ValueError:
                print("Invalid format. Please use YYYY-MM-DD (e.g., 2025-07-20)")
    
    def predict(self, county: dict, forecast_date: datetime, year: int = 2025):
        """Generate prediction for county and date."""
        
        fips = county['fips']
        
        print("\n" + "="*70)
        print("GENERATING FORECAST...")
        print("="*70)
        print("Loading satellite data (ET, LST, NDVI, EVI)...")
        
        # Load satellite data
        et_df = self.loader.load_et_data()
        lst_df = self.loader.load_lst_data()
        ndvi_evi_df = self.loader.load_ndvi_data()
        
        # Initialize feature engineer
        engineer = RollingWindowFeatureEngineer(et_df, lst_df, ndvi_evi_df)
        
        print(f"Creating features for {forecast_date.strftime('%B %d, %Y')}...")
        
        # Create features
        features_df = engineer.create_features_for_date(year, forecast_date)
        
        if len(features_df) == 0:
            print("\n❌ Error: No features could be created for this date.")
            print("   There may not be enough satellite data available.")
            return None
        
        # Filter to specific county (with .copy() to avoid warnings)
        county_features = features_df[features_df['fips'] == fips].copy()
        
        if len(county_features) == 0:
            print(f"\n❌ Error: No data available for {county['name']} County.")
            return None
        
        # Align features
        for col in self.feature_names:
            if col not in county_features.columns:
                county_features[col] = 0
        
        X = county_features[self.feature_names].fillna(0)
        
        # Scale and predict
        X_scaled = self.scaler.transform(X)
        prediction = self.model.predict(X_scaled)[0]
        
        # Calculate uncertainty
        data_completeness = county_features['data_completeness'].values[0] if 'data_completeness' in county_features.columns else 0.5
        base_rmse = self.metrics['rmse']
        uncertainty = base_rmse * (1.5 - 0.5 * data_completeness)
        
        # Create result
        result = {
            'fips': fips,
            'county': county['name'],
            'forecast_date': forecast_date.strftime('%Y-%m-%d'),
            'year': year,
            'predicted_yield': round(prediction, 1),
            'uncertainty': round(uncertainty, 1),
            'lower_bound': round(prediction - uncertainty, 1),
            'upper_bound': round(prediction + uncertainty, 1),
            'data_completeness': round(data_completeness * 100, 1),
            'confidence': self._get_confidence_level(data_completeness)
        }
        
        # Display results
        self._display_results(result, county_features)
        
        return result
    
    def _get_confidence_level(self, completeness: float) -> str:
        """Determine confidence level."""
        if completeness >= 0.85:
            return "HIGH"
        elif completeness >= 0.60:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _display_results(self, result: dict, features: pd.DataFrame):
        """Display prediction results."""
        
        print("\n" + "="*70)
        print("PREDICTION RESULTS")
        print("="*70)
        print(f"")
        print(f"  County:          {result['county']} County")
        print(f"  FIPS Code:       {result['fips']}")
        print(f"  Forecast Date:   {datetime.strptime(result['forecast_date'], '%Y-%m-%d').strftime('%B %d, %Y')}")
        print(f"")
        print(f"  Predicted Yield: {result['predicted_yield']} bu/acre")
        print(f"  Uncertainty:     ± {result['uncertainty']} bu/acre")
        print(f"  Range:           {result['lower_bound']} - {result['upper_bound']} bu/acre")
        print(f"")
        print(f"  Data Completeness: {result['data_completeness']}%")
        print(f"  Confidence Level:  {result['confidence']}")
        print(f"")
        
        # Show key factors
        print("="*70)
        print("KEY FACTORS (Multi-Sensor)")
        print("="*70)
        
        if 'et_mean' in features.columns:
            et_val = features['et_mean'].values[0]
            print(f"  Evapotranspiration (ET):  {et_val:.2f} mm/day")
        
        if 'lst_mean' in features.columns:
            lst_val = features['lst_mean'].values[0]
            print(f"  Land Surface Temp (LST):  {lst_val:.2f} °C")
        
        if 'ndvi_mean' in features.columns:
            ndvi_val = features['ndvi_mean'].values[0]
            print(f"  NDVI (Vegetation Index):  {ndvi_val:.3f}")
        
        if 'evi_mean' in features.columns:
            evi_val = features['evi_mean'].values[0]
            print(f"  EVI (Enhanced VI):        {evi_val:.3f}")
        
        if 'et_deficit_days' in features.columns:
            deficit_days = int(features['et_deficit_days'].values[0])
            print(f"  Water Deficit Days:       {deficit_days}")
        
        if 'lst_heat_stress_days' in features.columns:
            heat_days = int(features['lst_heat_stress_days'].values[0])
            print(f"  Heat Stress Days:         {heat_days}")
        
        if 'ndvi_observations' in features.columns:
            ndvi_obs = int(features['ndvi_observations'].values[0])
            evi_obs = int(features['evi_observations'].values[0]) if 'evi_observations' in features.columns else 0
            print(f"  Satellite Observations:   {ndvi_obs + evi_obs} (NDVI+EVI)")
        
        print(f"")
        
        # Interpretation
        print("="*70)
        print("INTERPRETATION")
        print("="*70)
        
        if result['predicted_yield'] >= 195:
            yield_quality = "excellent"
            emoji = "🌟"
        elif result['predicted_yield'] >= 185:
            yield_quality = "good"
            emoji = "✓"
        elif result['predicted_yield'] >= 175:
            yield_quality = "average"
            emoji = "○"
        else:
            yield_quality = "below average"
            emoji = "⚠"
        
        print(f"  {emoji} The predicted yield of {result['predicted_yield']} bu/acre is {yield_quality}")
        print(f"     for {result['county']} County.")
        print(f"")
        
        if result['confidence'] == "HIGH":
            print(f"  ✓ High confidence: We have data from most of the growing season.")
            print(f"    This forecast should be quite reliable.")
        elif result['confidence'] == "MEDIUM":
            print(f"  ○ Medium confidence: We have substantial data, but the forecast")
            print(f"    will improve as more of the growing season completes.")
        else:
            print(f"  ⚠ Low confidence: This is an early-season forecast with high")
            print(f"    uncertainty. The estimate will improve significantly as the")
            print(f"    season progresses.")
        
        print(f"")
        print(f"  ℹ  Model uses: ET (water stress) + LST (heat stress) +")
        print(f"     NDVI (early season) + EVI (dense canopy)")
        print(f"")
        print("="*70)
    
    def compare_dates(self, county: dict):
        """Compare predictions across multiple dates."""
        
        dates = [
            datetime(2025, 6, 15),
            datetime(2025, 7, 15),
            datetime(2025, 8, 15),
            datetime(2025, 9, 15),
        ]
        
        print("\n" + "="*70)
        print(f"FORECAST EVOLUTION: {county['name']} County")
        print("="*70)
        print("\nGenerating forecasts for 4 dates throughout the season...")
        
        results = []
        for date in dates:
            result = self.predict(county, date)
            if result:
                results.append(result)
                input("\nPress Enter to continue...")
        
        if not results:
            return
        
        # Display comparison
        print("\n" + "="*70)
        print("FORECAST COMPARISON")
        print("="*70)
        print(f"\n{county['name']} County - How predictions evolve over time:\n")
        print(f"{'Date':<18} {'Yield':<14} {'Uncertainty':<16} {'Confidence':<12}")
        print(f"{'-'*18} {'-'*14} {'-'*16} {'-'*12}")
        
        for r in results:
            date_formatted = datetime.strptime(r['forecast_date'], '%Y-%m-%d').strftime('%B %d')
            print(f"{date_formatted:<18} {r['predicted_yield']:<14.1f} ±{r['uncertainty']:<15.1f} {r['confidence']:<12}")
        
        print(f"\n{'='*70}")
        print("OBSERVATION:")
        print(f"  Notice how uncertainty decreases from ±{results[0]['uncertainty']:.1f} to")
        print(f"  ±{results[-1]['uncertainty']:.1f} bu/acre as the season progresses!")
        print(f"")
        print(f"  The model adapts predictions based on:")
        print(f"  • Early season: NDVI tracks vegetation emergence")
        print(f"  • Mid-late season: EVI tracks dense canopy health")
        print("="*70)
    
    def run(self):
        """Main interactive loop."""
        
        while True:
            print("\n")
            
            # Select county
            county = self.select_county()
            if county is None:
                print("\nThank you for using the Iowa Corn Yield Forecasting System!")
                print("Goodbye! 🌽\n")
                break
            
            # Select date
            mode, date = self.select_date()
            if mode is None:
                continue
            
            # Generate prediction
            if mode == 'compare':
                self.compare_dates(county)
            elif mode == 'single' and date:
                self.predict(county, date)
            
            # Ask to continue
            print("\n" + "="*70)
            choice = input("Make another prediction? (y/n): ").strip().lower()
            if choice != 'y':
                print("\nThank you for using the Iowa Corn Yield Forecasting System!")
                print("Goodbye! 🌽\n")
                break


def main():
    """Entry point."""
    try:
        app = InteractiveForecast()
        app.run()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye! 🌽\n")
    except Exception as e:
        print(f"\n\nError: {e}")
        print("Please try again or contact support.\n")


if __name__ == "__main__":
    main()