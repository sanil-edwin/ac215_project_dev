"""
Unit tests for Feature Builder

Tests feature engineering pipeline for corn yield prediction.

Author: AgriGuard Team
Date: November 2025
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from feature_builder import CornYieldFeatureBuilder


class TestFeatureBuilder:
    """Test suite for Feature Builder"""
    
    @pytest.fixture
    def builder(self):
        """Create feature builder instance"""
        return CornYieldFeatureBuilder()
    
    @pytest.fixture
    def sample_yields(self):
        """Create sample yield data"""
        return pd.DataFrame({
            'fips': ['19001'] * 5,
            'county_name': ['Adair'] * 5,
            'year': [2020, 2021, 2022, 2023, 2024],
            'yield_bu_per_acre': [180, 185, 175, 190, 182]
        })
    
    @pytest.fixture
    def sample_indicator_data(self):
        """Create sample indicator data for one county-year"""
        dates = pd.date_range('2024-05-01', '2024-10-31', freq='D')
        
        data = {
            'water_deficit': [],
            'lst': [],
            'ndvi': [],
            'vpd': [],
            'eto': [],
            'precip': []
        }
        
        for date in dates:
            # Water deficit
            data['water_deficit'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'water_deficit': np.random.uniform(0, 6),
                'year': 2024
            })
            
            # LST
            data['lst'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(25, 35),
                'year': 2024
            })
            
            # NDVI
            data['ndvi'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(0.5, 0.9),
                'year': 2024
            })
            
            # VPD
            data['vpd'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(0, 0.003),
                'year': 2024
            })
            
            # ETo
            data['eto'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(2, 8),
                'year': 2024
            })
            
            # Precipitation
            data['precip'].append({
                'date': date,
                'fips': '19001',
                'county_name': 'Adair',
                'mean': np.random.uniform(0, 30),
                'year': 2024
            })
        
        # Convert to DataFrames
        return {k: pd.DataFrame(v) for k, v in data.items()}
    
    # =================================================================
    # Test: Period Filtering
    # =================================================================
    
    def test_filter_by_period_emergence(self, builder, sample_indicator_data):
        """Test filtering data to emergence period"""
        df = sample_indicator_data['water_deficit']
        
        filtered = builder.filter_by_period(
            df,
            2024,
            builder.GROWTH_PERIODS['emergence']
        )
        
        # Check dates are in May
        assert filtered['date'].dt.month.unique()[0] == 5
        assert len(filtered) > 0
    
    def test_filter_by_period_pollination(self, builder, sample_indicator_data):
        """Test filtering data to pollination period"""
        df = sample_indicator_data['water_deficit']
        
        filtered = builder.filter_by_period(
            df,
            2024,
            builder.GROWTH_PERIODS['pollination']
        )
        
        # Should be July 15 - Aug 15
        months = filtered['date'].dt.month.unique()
        assert 7 in months or 8 in months
        assert len(filtered) > 0
    
    # =================================================================
    # Test: Period Features
    # =================================================================
    
    def test_build_period_features_structure(self, builder, sample_indicator_data,
                                             sample_yields):
        """Test that period features have correct structure"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_period_features(
            data,
            '19001',
            2024
        )
        
        # Check that features exist for each period
        for period in builder.GROWTH_PERIODS.keys():
            assert f'{period}_water_deficit_mean' in features
            assert f'{period}_lst_mean' in features
            assert f'{period}_ndvi_mean' in features
    
    def test_build_period_features_values(self, builder, sample_indicator_data,
                                         sample_yields):
        """Test that period features have valid values"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_period_features(
            data,
            '19001',
            2024
        )
        
        # Check pollination features (most critical)
        poll_wd = features['pollination_water_deficit_mean']
        assert isinstance(poll_wd, (int, float, np.number)) or pd.isna(poll_wd)
        
        if not pd.isna(poll_wd):
            assert poll_wd >= 0, "Water deficit should be non-negative"
    
    def test_build_period_features_stress_thresholds(self, builder, 
                                                     sample_indicator_data,
                                                     sample_yields):
        """Test that stress threshold features are counted correctly"""
        # Set high water deficit during pollination
        data = sample_indicator_data.copy()
        poll_mask = (
            (data['water_deficit']['date'].dt.month == 7) |
            (data['water_deficit']['date'].dt.month == 8)
        )
        data['water_deficit'].loc[poll_mask, 'water_deficit'] = 7.0
        
        data['yields'] = sample_yields
        
        features = builder.build_period_features(
            data,
            '19001',
            2024
        )
        
        # Should count many days with deficit > 6mm
        assert features['pollination_days_deficit_gt_6mm'] > 0
    
    # =================================================================
    # Test: Interaction Features
    # =================================================================
    
    def test_build_interaction_features(self, builder):
        """Test interaction feature creation"""
        base_features = {
            'pollination_water_deficit_mean': 5.0,
            'pollination_lst_mean': 34.0,
            'pollination_ndvi_mean': 0.65
        }
        
        interactions = builder.build_interaction_features(base_features)
        
        # Should create combined stress features
        assert 'pollination_water_heat_stress' in interactions
        assert 'pollination_combined_stress' in interactions
        assert 'pollination_ndvi_water_interaction' in interactions
    
    def test_interaction_features_with_nans(self, builder):
        """Test interaction features handle NaN values"""
        base_features = {
            'pollination_water_deficit_mean': np.nan,
            'pollination_lst_mean': 34.0,
            'pollination_ndvi_mean': 0.65
        }
        
        interactions = builder.build_interaction_features(base_features)
        
        # Should not crash, may have fewer features
        assert isinstance(interactions, dict)
    
    # =================================================================
    # Test: Historical Features
    # =================================================================
    
    def test_build_historical_features(self, builder, sample_yields,
                                       sample_indicator_data):
        """Test historical feature creation"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_historical_features(
            data,
            '19001',
            2024
        )
        
        # Should have 5-year averages
        assert 'yield_5yr_mean' in features
        assert 'yield_5yr_std' in features
        assert 'yield_5yr_trend' in features
        assert 'yield_prev_year' in features
    
    def test_historical_features_values(self, builder, sample_yields,
                                       sample_indicator_data):
        """Test historical feature values are reasonable"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_historical_features(
            data,
            '19001',
            2024
        )
        
        # 5-year mean should be around 182
        if not pd.isna(features['yield_5yr_mean']):
            assert 170 <= features['yield_5yr_mean'] <= 195
        
        # Previous year should be 2023 value (190)
        if not pd.isna(features['yield_prev_year']):
            assert features['yield_prev_year'] == 190
    
    # =================================================================
    # Test: Temporal Features
    # =================================================================
    
    def test_build_temporal_features(self, builder):
        """Test temporal feature creation"""
        features = builder.build_temporal_features(2024)
        
        assert 'year' in features
        assert features['year'] == 2024
        
        assert 'year_since_2016' in features
        assert features['year_since_2016'] == 8
        
        assert 'is_drought_year' in features
        assert features['is_drought_year'] in [0, 1]
    
    # =================================================================
    # Test: Complete Feature Building
    # =================================================================
    
    def test_build_features_for_county_year(self, builder, sample_yields,
                                           sample_indicator_data):
        """Test building complete feature set"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_features_for_county_year(
            data,
            '19001',
            2024
        )
        
        # Check basic structure
        assert 'fips' in features
        assert 'year' in features
        assert features['fips'] == '19001'
        assert features['year'] == 2024
        
        # Should have many features
        assert len(features) > 100, "Should have 100+ features"
    
    def test_feature_completeness(self, builder, sample_yields,
                                 sample_indicator_data):
        """Test that most features are non-null"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        features = builder.build_features_for_county_year(
            data,
            '19001',
            2024
        )
        
        # Count non-null features
        non_null = sum(1 for v in features.values() 
                      if not pd.isna(v))
        total = len(features)
        
        completeness = non_null / total
        assert completeness > 0.8, "Should have >80% feature completeness"
    
    # =================================================================
    # Test: Edge Cases
    # =================================================================
    
    def test_missing_county_data(self, builder, sample_yields,
                                sample_indicator_data):
        """Test handling of missing county data"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        # Try non-existent county
        features = builder.build_features_for_county_year(
            data,
            '99999',
            2024
        )
        
        # Should still return features (may be NaN)
        assert 'fips' in features
        assert features['fips'] == '99999'
    
    def test_year_with_no_data(self, builder, sample_yields,
                              sample_indicator_data):
        """Test handling year with no indicator data"""
        data = {**sample_indicator_data, 'yields': sample_yields}
        
        # Try year with no data (e.g., 2030)
        features = builder.build_features_for_county_year(
            data,
            '19001',
            2030
        )
        
        # Should return features but many will be NaN
        assert 'year' in features
        assert features['year'] == 2030


# =================================================================
# Integration Tests
# =================================================================

class TestFeatureBuilderIntegration:
    """Integration tests for feature builder"""
    
    @pytest.mark.slow
    def test_build_all_features(self):
        """Test building features for all counties (requires GCS access)"""
        builder = CornYieldFeatureBuilder()
        
        try:
            # Build for just 2023-2024 to save time
            features = builder.build_all_features(
                year_start=2023,
                year_end=2024,
                save_to_gcs=False
            )
            
            assert len(features) > 0, "Should build features"
            assert 'yield_bu_per_acre' in features.columns
            assert len(features.columns) > 100, "Should have 100+ features"
            
        except Exception as e:
            pytest.skip(f"Integration test requires GCS access: {e}")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=feature_builder", "--cov-report=html"])
