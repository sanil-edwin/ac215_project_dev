"""
Quality Checker
Checks for outliers, valid ranges, and data quality metrics
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class QualityChecker:
    """Check data quality and detect anomalies"""
    
    # Valid ranges for each indicator
    VALID_RANGES = {
        'ndvi_mean': (0, 1),
        'ndvi_std': (0, 0.5),
        'lst_mean': (-50, 60),  # Celsius
        'lst_std': (0, 20),
        'vpd_mean': (0, 5),  # kPa
        'eto_mean': (0, 15),  # mm/day
        'pr_mean': (0, 200),  # mm/day
        'water_deficit': (-200, 15),  # mm/day
    }
    
    def check_value_ranges(self, df):
        """
        Check if values fall within valid ranges
        
        Args:
            df: DataFrame to check
            
        Returns:
            tuple: (is_valid, violations)
        """
        violations = {}
        
        for col, (min_val, max_val) in self.VALID_RANGES.items():
            if col in df.columns:
                # Skip NaN values
                valid_data = df[col].dropna()
                
                out_of_range = (
                    (valid_data < min_val) | (valid_data > max_val)
                ).sum()
                
                if out_of_range > 0:
                    violations[col] = {
                        'count': out_of_range,
                        'pct': (out_of_range / len(valid_data)) * 100,
                        'min': valid_data.min(),
                        'max': valid_data.max(),
                    }
        
        is_valid = len(violations) == 0
        
        if is_valid:
            logger.info("✅ Value ranges validation passed")
        else:
            logger.warning(f"⚠️  Out-of-range values detected: {violations}")
        
        return is_valid, violations
    
    def detect_outliers(self, df, columns=None, threshold=3):
        """
        Detect outliers using IQR method
        
        Args:
            df: DataFrame to check
            columns: Specific columns to check (None = all numeric)
            threshold: Z-score threshold (default 3)
            
        Returns:
            dict: Outlier counts per column
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns
        
        outliers = {}
        
        for col in columns:
            if col in df.columns:
                data = df[col].dropna()
                
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_count = (
                    (data < lower_bound) | (data > upper_bound)
                ).sum()
                
                if outlier_count > 0:
                    outliers[col] = {
                        'count': outlier_count,
                        'pct': (outlier_count / len(data)) * 100,
                        'bounds': (lower_bound, upper_bound),
                    }
        
        if outliers:
            logger.warning(f"⚠️  Outliers detected: {outliers}")
        else:
            logger.info("✅ No outliers detected")
        
        return outliers
    
    def check_completeness(self, df, min_completeness=0.95):
        """
        Check data completeness (inverse of missing data)
        
        Args:
            df: DataFrame to check
            min_completeness: Minimum acceptable completeness (0-1)
            
        Returns:
            tuple: (is_valid, completeness_report)
        """
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isna().sum().sum()
        completeness = 1 - (missing_cells / total_cells)
        
        report = {
            'total_cells': total_cells,
            'missing_cells': missing_cells,
            'completeness': completeness,
            'by_column': df.isna().sum().to_dict(),
        }
        
        is_valid = completeness >= min_completeness
        
        if is_valid:
            logger.info(f"✅ Completeness check passed: {completeness*100:.1f}%")
        else:
            logger.warning(f"⚠️  Low completeness: {completeness*100:.1f}%")
        
        return is_valid, report
    
    def check_duplicates(self, df, key_cols=['date', 'fips']):
        """
        Check for duplicate rows
        
        Args:
            df: DataFrame to check
            key_cols: Columns that define uniqueness
            
        Returns:
            tuple: (is_valid, duplicate_count)
        """
        duplicates = df.duplicated(subset=key_cols).sum()
        is_valid = duplicates == 0
        
        if is_valid:
            logger.info("✅ No duplicates found")
        else:
            logger.warning(f"⚠️  Found {duplicates} duplicate rows")
        
        return is_valid, duplicates
