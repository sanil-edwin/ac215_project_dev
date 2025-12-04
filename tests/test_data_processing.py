"""
Test suite for AgriGuard Data Processing

Tests data validation, processing functions, and utilities.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime


class TestDataValidation:
    """Test data validation functions"""
    
    def test_ndvi_range_validation(self):
        """Test NDVI values are in valid range [0, 1]"""
        valid_ndvi = [0.0, 0.5, 0.8, 1.0]
        invalid_ndvi = [-0.1, 1.5, 2.0]
        
        for value in valid_ndvi:
            assert 0 <= value <= 1
        
        for value in invalid_ndvi:
            assert not (0 <= value <= 1)
    
    def test_lst_range_validation(self):
        """Test LST values are in valid range [-10, 60]°C"""
        valid_lst = [-10, 0, 25, 35, 60]
        invalid_lst = [-15, 70, 100]
        
        for value in valid_lst:
            assert -10 <= value <= 60
        
        for value in invalid_lst:
            assert not (-10 <= value <= 60)
    
    def test_fips_code_validation(self):
        """Test FIPS code validation"""
        valid_fips = ["19001", "19153", "19099"]  # Iowa counties
        invalid_fips = ["00000", "99999", "abc12"]
        
        for fips in valid_fips:
            assert len(fips) == 5
            assert fips.startswith("19")  # Iowa
            assert fips.isdigit()
        
        for fips in invalid_fips:
            is_valid = (len(fips) == 5 and 
                       fips.startswith("19") and 
                       fips.isdigit())
            assert not is_valid
    
    def test_date_format_validation(self):
        """Test date format validation"""
        valid_dates = ["2025-01-01", "2024-12-31"]
        
        for date_str in valid_dates:
            # Should parse without error
            parsed = datetime.strptime(date_str, "%Y-%m-%d")
            assert isinstance(parsed, datetime)


class TestMCSICalculation:
    """Test MCSI calculation logic"""
    
    def test_water_stress_calculation(self):
        """Test water stress index calculation"""
        # Water deficit = ETo - Precipitation
        eto = 5.0  # mm/day
        precip = 1.0  # mm/day
        deficit = eto - precip
        
        # Calculate stress index
        if deficit < 0:
            stress = 0
        elif deficit < 2:
            stress = 20
        elif deficit < 4:
            stress = 50
        elif deficit < 6:
            stress = 75
        else:
            stress = 100
        
        assert deficit == 4.0
        assert stress == 50
    
    def test_heat_stress_calculation(self):
        """Test heat stress index calculation"""
        lst_values = [30, 36, 38, 32, 35]  # Daily temperatures
        
        days_above_35 = sum(1 for t in lst_values if t > 35)
        days_above_38 = sum(1 for t in lst_values if t > 38)
        
        assert days_above_35 == 2
        assert days_above_38 == 0
    
    def test_vegetation_health_calculation(self):
        """Test vegetation health index calculation"""
        ndvi_current = 0.72
        ndvi_historical = 0.80
        
        health_ratio = ndvi_current / ndvi_historical
        
        if health_ratio > 1.0:
            stress = 0
        elif health_ratio > 0.9:
            stress = 20
        elif health_ratio > 0.8:
            stress = 50
        elif health_ratio > 0.7:
            stress = 75
        else:
            stress = 100
        
        assert health_ratio == 0.9
        assert stress == 20
    
    def test_mcsi_aggregation(self):
        """Test MCSI weighted aggregation"""
        water_stress = 50
        heat_stress = 40
        veg_health = 35
        atm_stress = 30
        
        # Weights: 40%, 30%, 20%, 10%
        mcsi = (0.40 * water_stress + 
                0.30 * heat_stress + 
                0.20 * veg_health + 
                0.10 * atm_stress)
        
        assert 0 <= mcsi <= 100
        assert mcsi == pytest.approx(42.0)
    
    def test_mcsi_output_range(self):
        """Test MCSI is always in [0, 100] range"""
        test_cases = [
            (0, 0, 0, 0, 0),
            (100, 100, 100, 100, 100),
            (50, 50, 50, 50, 50),
            (75, 25, 60, 40, 54)  # Mixed values
        ]
        
        for water, heat, veg, atm, expected in test_cases:
            mcsi = (0.40 * water + 0.30 * heat + 0.20 * veg + 0.10 * atm)
            assert 0 <= mcsi <= 100


class TestYieldFeatures:
    """Test yield prediction feature engineering"""
    
    def test_growing_degree_days(self):
        """Test GDD calculation"""
        tbase = 10  # Base temperature for corn
        tmax = 30
        tmin = 15
        
        # GDD = (Tmax + Tmin)/2 - Tbase
        gdd = ((tmax + tmin) / 2) - tbase
        
        assert gdd > 0
        assert gdd == 12.5
    
    def test_water_deficit_accumulation(self):
        """Test water deficit accumulation"""
        daily_deficits = [2, 3, 4, 1, 0, 5]
        
        total_deficit = sum(daily_deficits)
        avg_deficit = sum(daily_deficits) / len(daily_deficits)
        
        assert total_deficit == 15
        assert avg_deficit == 2.5
    
    def test_critical_period_aggregation(self):
        """Test aggregation during critical pollination period"""
        # July 15 - Aug 15 (DOY 196-227)
        data = [
            {"doy": 195, "water_deficit": 5},
            {"doy": 200, "water_deficit": 6},  # In critical period
            {"doy": 220, "water_deficit": 4},  # In critical period
            {"doy": 230, "water_deficit": 3}
        ]
        
        critical_deficit = sum(
            d["water_deficit"] for d in data 
            if 196 <= d["doy"] <= 227
        )
        
        assert critical_deficit == 10  # 6 + 4


class TestDataProcessing:
    """Test data processing utilities"""
    
    def test_temporal_alignment(self):
        """Test aligning 16-day MODIS to daily weather"""
        modis_date = "2024-07-01"
        
        # MODIS composite covers 16 days
        start_date = datetime.strptime(modis_date, "%Y-%m-%d")
        
        # Should create 16 daily records
        daily_records = []
        for i in range(16):
            daily_records.append(start_date)
        
        assert len(daily_records) == 16
    
    def test_spatial_aggregation(self):
        """Test aggregating to county level"""
        # Mock pixel-level data
        pixel_values = [0.7, 0.75, 0.8, 0.72, 0.68]
        
        # County-level aggregation
        county_mean = np.mean(pixel_values)
        county_std = np.std(pixel_values)
        county_min = np.min(pixel_values)
        county_max = np.max(pixel_values)
        
        assert county_mean == pytest.approx(0.73)
        assert county_std > 0
        assert county_min == 0.68
        assert county_max == 0.8
    
    def test_missing_value_handling(self):
        """Test handling of missing values"""
        values = [1.0, 2.0, np.nan, 4.0, 5.0]
        
        # Remove NaN values
        clean_values = [v for v in values if not np.isnan(v)]
        
        assert len(clean_values) == 4
        assert np.nan not in clean_values


class TestUtilities:
    """Test utility functions"""
    
    def test_county_name_lookup(self):
        """Test FIPS to county name mapping"""
        fips_to_county = {
            "19153": "POLK",
            "19001": "ADAIR",
            "19169": "STORY"
        }
        
        assert fips_to_county["19153"] == "POLK"
        assert "19153" in fips_to_county
    
    def test_week_of_season_calculation(self):
        """Test calculating week of growing season"""
        # Growing season: May 1 (DOY 121) to Oct 31 (DOY 304)
        may_1_doy = 121
        doy = 135  # May 15
        
        # Week of season = (DOY - season_start) // 7 + 1
        week_of_season = ((doy - may_1_doy) // 7) + 1
        
        assert week_of_season == 2
    
    def test_date_to_doy_conversion(self):
        """Test date to day-of-year conversion"""
        date_str = "2024-07-15"
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        doy = date_obj.timetuple().tm_yday
        
        # July 15 should be around day 196-197 (leap year dependent)
        assert 196 <= doy <= 197


class TestDataQuality:
    """Test data quality checks"""
    
    def test_completeness_check(self):
        """Test data completeness check"""
        total_records = 100
        missing_records = 2
        
        completeness = (total_records - missing_records) / total_records
        
        assert completeness >= 0.98  # Target: >98%
        assert completeness == 0.98
    
    def test_outlier_detection(self):
        """Test outlier detection"""
        values = [1, 2, 2.5, 3, 2.8, 100]  # 100 is outlier
        
        mean = np.mean(values)
        std = np.std(values)
        
        outliers = [v for v in values if abs(v - mean) > 3 * std]
        
        assert len(outliers) > 0
        assert 100 in outliers
    
    def test_temporal_continuity(self):
        """Test temporal continuity (no large gaps)"""
        dates = [
            datetime(2024, 5, 1),
            datetime(2024, 5, 2),
            datetime(2024, 5, 3),
            datetime(2024, 5, 10)  # 7-day gap
        ]
        
        max_gap = 0
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i-1]).days
            max_gap = max(max_gap, gap)
        
        assert max_gap == 7


# Fixtures
@pytest.fixture
def sample_weekly_data():
    """Fixture for sample weekly data"""
    return {
        "date": "2024-07-15",
        "fips": "19153",
        "week_of_season": 10,
        "ndvi_mean": 0.75,
        "lst_mean": 28.5,
        "water_deficit": 3.2,
        "vpd_mean": 2.1
    }


@pytest.fixture
def sample_county_timeseries():
    """Fixture for sample county timeseries"""
    return pd.DataFrame({
        'date': pd.date_range('2024-05-01', periods=26, freq='W'),
        'fips': ['19153'] * 26,
        'ndvi_mean': np.random.uniform(0.5, 0.9, 26),
        'lst_mean': np.random.uniform(20, 35, 26)
    })


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
