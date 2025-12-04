"""
Schema Validator
Validates data structure and column types
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validate parquet files match expected schema"""
    
    EXPECTED_SCHEMA = {
        'daily': {
            'date': 'object',
            'fips': 'object',
            'county_name': 'object',
            'year': 'int64',
            'month': 'int64',
            'doy': 'int64',
            'ndvi_mean': 'float64',
            'ndvi_std': 'float64',
            'lst_mean': 'float64',
            'lst_std': 'float64',
            'vpd_mean': 'float64',
            'eto_mean': 'float64',
            'pr_mean': 'float64',
            'water_deficit': 'float64',
        },
        'weekly': {
            'date': 'object',
            'week': 'int64',
            'fips': 'object',
            'county_name': 'object',
            'ndvi_mean': 'float64',
            'lst_mean': 'float64',
            'vpd_mean': 'float64',
            'eto_mean': 'float64',
            'pr_total': 'float64',
        }
    }
    
    def validate_schema(self, df, dataset_type='daily'):
        """
        Validate dataframe matches expected schema
        
        Args:
            df: DataFrame to validate
            dataset_type: 'daily' or 'weekly'
            
        Returns:
            tuple: (is_valid, errors)
        """
        errors = []
        expected = self.EXPECTED_SCHEMA.get(dataset_type, {})
        
        # Check required columns exist
        missing_cols = set(expected.keys()) - set(df.columns)
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
        
        # Check column types
        for col, expected_type in expected.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if actual_type != expected_type:
                    errors.append(f"Column '{col}': expected {expected_type}, got {actual_type}")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"✅ Schema validation passed for {dataset_type} data")
        else:
            logger.error(f"❌ Schema validation failed: {errors}")
        
        return is_valid, errors
    
    def validate_required_values(self, df, dataset_type='daily'):
        """
        Check for required non-null values
        
        Args:
            df: DataFrame to validate
            dataset_type: 'daily' or 'weekly'
            
        Returns:
            tuple: (is_valid, missing_counts)
        """
        required_cols = self.EXPECTED_SCHEMA.get(dataset_type, {}).keys()
        missing_counts = {}
        
        for col in required_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    missing_counts[col] = null_count
        
        # Allow some nulls but flag if >5%
        tolerance = len(df) * 0.05
        
        critical_missing = {
            col: count for col, count in missing_counts.items() 
            if count > tolerance
        }
        
        is_valid = len(critical_missing) == 0
        
        if is_valid:
            logger.info(f"✅ Required values validation passed")
        else:
            logger.warning(f"⚠️  Critical missing values: {critical_missing}")
        
        return is_valid, missing_counts
