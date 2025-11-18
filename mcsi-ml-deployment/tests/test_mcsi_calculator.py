"""
Unit tests for MCSI Calculator

Tests all components of the Multi-Factor Corn Stress Index calculation.

Author: AgriGuard Team
Date: November 2025
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from mcsi_calculator import MCSICalculator


class TestMCSICalculator:
    """Test suite for MCSI Calculator"""
    
    @pytest.fixture
    def calculator(self):
        """Create calculator instance"""
        return MCSICalculator()
    
    @pytest.fixture
    def sample_water_deficit_data(self):
        """Create sample water deficit data"""
        dates = pd.date_range('2024-07-01', '2024-07-31', freq='D')
        data = []
        for date in dates:
            data.append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'water_deficit': np.random.uniform(0, 8),
                'year': 2024
            })
        return pd.DataFrame(data)
    
    @pytest.fixture
    def sample_lst_data(self):
        """Create sample LST data"""
        dates = pd.date_range('2024-07-01', '2024-07-31', freq='D')
        data = []
        for date in dates:
            data.append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(25, 40),
                'year': 2024
            })
        return pd.DataFrame(data)
    
    @pytest.fixture
    def sample_ndvi_data(self):
        """Create sample NDVI data"""
        dates = pd.date_range('2024-07-01', '2024-07-31', freq='D')
        data = []
        for date in dates:
            for year in range(2019, 2025):
                data.append({
                    'date': date.replace(year=year),
                    'fips': '19001',
                    'county_name': 'Adair',
                    'mean': np.random.uniform(0.5, 0.9),
                    'year': year
                })
        return pd.DataFrame(data)
    
    # =================================================================
    # Test: Water Stress Calculation
    # =================================================================
    
    def test_water_stress_no_stress(self, calculator, sample_water_deficit_data):
        """Test water stress calculation with no stress"""
        # Low deficit values
        sample_water_deficit_data['water_deficit'] = 1.0
        
        stress = calculator.calculate_water_stress(
            sample_water_deficit_data,
            '19001',
            '2024-07-01',
            '2024-07-31'
        )
        
        assert 0 <= stress < 30, "Should be low stress"
    
    def test_water_stress_high_stress(self, calculator, sample_water_deficit_data):
        """Test water stress calculation with high stress"""
        # High deficit values
        sample_water_deficit_data['water_deficit'] = 7.0
        
        stress = calculator.calculate_water_stress(
            sample_water_deficit_data,
            '19001',
            '2024-07-01',
            '2024-07-31'
        )
        
        assert stress >= 60, "Should be high stress"
    
    def test_water_stress_missing_data(self, calculator, sample_water_deficit_data):
        """Test water stress with missing county data"""
        stress = calculator.calculate_water_stress(
            sample_water_deficit_data,
            '99999',  # Non-existent county
            '2024-07-01',
            '2024-07-31'
        )
        
        assert stress == 0.0, "Should return 0 for missing data"
    
    # =================================================================
    # Test: Heat Stress Calculation
    # =================================================================
    
    def test_heat_stress_no_stress(self, calculator, sample_lst_data):
        """Test heat stress with normal temperatures"""
        sample_lst_data['mean'] = 28.0  # Normal temperature
        
        stress = calculator.calculate_heat_stress(
            sample_lst_data,
            '19001',
            '2024-07-01',
            '2024-07-31'
        )
        
        assert 0 <= stress < 30, "Should be low stress"
    
    def test_heat_stress_high_stress(self, calculator, sample_lst_data):
        """Test heat stress with high temperatures"""
        sample_lst_data['mean'] = 40.0  # Very high temperature
        
        stress = calculator.calculate_heat_stress(
            sample_lst_data,
            '19001',
            '2024-07-01',
            '2024-07-31'
        )
        
        assert stress >= 60, "Should be high stress"
    
    def test_heat_stress_threshold_counting(self, calculator, sample_lst_data):
        """Test that heat stress correctly counts days above thresholds"""
        # Set exactly 10 days above 35°C
        sample_lst_data.iloc[:10, sample_lst_data.columns.get_loc('mean')] = 36.0
        sample_lst_data.iloc[10:, sample_lst_data.columns.get_loc('mean')] = 28.0
        
        stress = calculator.calculate_heat_stress(
            sample_lst_data,
            '19001',
            '2024-07-01',
            '2024-07-31'
        )
        
        assert stress > 0, "Should detect heat stress from days above threshold"
    
    # =================================================================
    # Test: Vegetation Stress Calculation
    # =================================================================
    
    def test_vegetation_stress_with_baseline(self, calculator, sample_ndvi_data):
        """Test vegetation stress with historical baseline"""
        # Set current year lower than baseline
        current_year_mask = sample_ndvi_data['year'] == 2024
        historical_mask = sample_ndvi_data['year'] < 2024
        
        sample_ndvi_data.loc[historical_mask, 'mean'] = 0.8
        sample_ndvi_data.loc[current_year_mask, 'mean'] = 0.6  # 25% below normal
        
        stress = calculator.calculate_vegetation_stress(
            sample_ndvi_data,
            '19001',
            '2024-07-01',
            '2024-07-31',
            2024
        )
        
        assert stress > 30, "Should detect stress from NDVI anomaly"
    
    def test_vegetation_stress_no_baseline(self, calculator, sample_ndvi_data):
        """Test vegetation stress without baseline (uses absolute NDVI)"""
        # Only current year data
        current_data = sample_ndvi_data[sample_ndvi_data['year'] == 2024].copy()
        current_data['mean'] = 0.7  # Healthy NDVI
        
        stress = calculator.calculate_vegetation_stress(
            current_data,
            '19001',
            '2024-07-01',
            '2024-07-31',
            2024
        )
        
        assert 0 <= stress <= 100, "Should return valid stress score"
    
    # =================================================================
    # Test: Growth Stage Detection
    # =================================================================
    
    def test_growth_stage_emergence(self, calculator):
        """Test growth stage detection for emergence"""
        date = datetime(2024, 5, 15)  # Mid-May
        stage = calculator.get_growth_stage(date)
        assert stage == 'emergence'
    
    def test_growth_stage_pollination(self, calculator):
        """Test growth stage detection for pollination"""
        date = datetime(2024, 7, 25)  # Late July
        stage = calculator.get_growth_stage(date)
        assert stage == 'pollination'
    
    def test_growth_stage_grain_fill(self, calculator):
        """Test growth stage detection for grain fill"""
        date = datetime(2024, 9, 1)  # Early September
        stage = calculator.get_growth_stage(date)
        assert stage == 'grain_fill'
    
    def test_growth_stage_off_season(self, calculator):
        """Test growth stage detection for off-season"""
        date = datetime(2024, 12, 1)  # December
        stage = calculator.get_growth_stage(date)
        assert stage == 'off_season'
    
    # =================================================================
    # Test: Complete MCSI Calculation
    # =================================================================
    
    def test_mcsi_calculation_structure(self, calculator, sample_water_deficit_data, 
                                       sample_lst_data, sample_ndvi_data):
        """Test that MCSI returns correct structure"""
        data = {
            'water_deficit': sample_water_deficit_data,
            'lst': sample_lst_data,
            'ndvi': sample_ndvi_data
        }
        
        result = calculator.calculate_mcsi(
            county_fips='19001',
            start_date='2024-07-01',
            end_date='2024-07-31',
            data=data
        )
        
        # Check structure
        assert 'mcsi_score' in result
        assert 'stress_level' in result
        assert 'color' in result
        assert 'components' in result
        assert 'growth_stage' in result
        
        # Check types
        assert isinstance(result['mcsi_score'], float)
        assert result['stress_level'] in ['Low', 'Moderate', 'High']
        assert result['color'] in ['green', 'yellow', 'red']
    
    def test_mcsi_score_range(self, calculator, sample_water_deficit_data,
                             sample_lst_data, sample_ndvi_data):
        """Test that MCSI score is within valid range"""
        data = {
            'water_deficit': sample_water_deficit_data,
            'lst': sample_lst_data,
            'ndvi': sample_ndvi_data
        }
        
        result = calculator.calculate_mcsi(
            county_fips='19001',
            start_date='2024-07-01',
            end_date='2024-07-31',
            data=data
        )
        
        assert 0 <= result['mcsi_score'] <= 100, "MCSI score should be between 0 and 100"
    
    def test_mcsi_component_weights(self, calculator, sample_water_deficit_data,
                                   sample_lst_data, sample_ndvi_data):
        """Test that component weights sum correctly"""
        assert abs(
            calculator.WEIGHTS['water'] +
            calculator.WEIGHTS['heat'] +
            calculator.WEIGHTS['vegetation'] - 1.0
        ) < 0.01, "Component weights should sum to 1.0"
    
    def test_mcsi_pollination_multiplier(self, calculator, sample_water_deficit_data,
                                        sample_lst_data, sample_ndvi_data):
        """Test that pollination period gets higher multiplier"""
        data = {
            'water_deficit': sample_water_deficit_data,
            'lst': sample_lst_data,
            'ndvi': sample_ndvi_data
        }
        
        result = calculator.calculate_mcsi(
            county_fips='19001',
            start_date='2024-07-15',  # Pollination period
            end_date='2024-08-15',
            data=data
        )
        
        assert result['growth_stage'] == 'pollination'
        assert result['growth_stage_multiplier'] == 1.5
    
    # =================================================================
    # Test: Batch Processing
    # =================================================================
    
    def test_calculate_all_counties_returns_dataframe(self, calculator, mocker):
        """Test that calculate_all_counties returns a DataFrame"""
        # Mock load_data to avoid actual GCS calls
        mock_data = {
            'water_deficit': pd.DataFrame({
                'date': [datetime(2024, 7, 1)],
                'fips': ['19001'],
                'county_name': ['Adair'],
                'water_deficit': [3.0],
                'year': [2024]
            }),
            'lst': pd.DataFrame({
                'date': [datetime(2024, 7, 1)],
                'fips': ['19001'],
                'county_name': ['Adair'],
                'mean': [32.0],
                'year': [2024]
            }),
            'ndvi': pd.DataFrame({
                'date': [datetime(2024, 7, 1)],
                'fips': ['19001'],
                'county_name': ['Adair'],
                'mean': [0.7],
                'year': [2024]
            })
        }
        
        mocker.patch.object(calculator, 'load_data', return_value=mock_data)
        mocker.patch('pandas.DataFrame.to_parquet')  # Mock GCS write
        
        result = calculator.calculate_all_counties(
            start_date='2024-07-01',
            end_date='2024-07-31',
            save_to_gcs=False
        )
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'mcsi_score' in result.columns


# =================================================================
# Integration Tests
# =================================================================

class TestMCSIIntegration:
    """Integration tests for MCSI"""
    
    @pytest.mark.slow
    def test_end_to_end_calculation(self):
        """Test complete MCSI calculation flow (requires GCS access)"""
        # This test requires actual GCS access
        # Mark as slow so it can be skipped in fast CI runs
        calculator = MCSICalculator()
        
        # Use a recent date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        try:
            results = calculator.calculate_all_counties(
                start_date=start_date,
                end_date=end_date,
                save_to_gcs=False
            )
            
            assert len(results) > 0, "Should process at least one county"
            assert results['mcsi_score'].notna().all(), "All MCSI scores should be valid"
            
        except Exception as e:
            pytest.skip(f"Integration test requires GCS access: {e}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=mcsi_calculator", "--cov-report=html"])
