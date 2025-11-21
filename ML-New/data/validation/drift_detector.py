"""
Drift Detector
Detects data distribution shifts and anomalies
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect data drift and distribution changes"""
    
    def __init__(self, baseline_period_days=30):
        """
        Initialize drift detector
        
        Args:
            baseline_period_days: Days to use for baseline statistics
        """
        self.baseline_period_days = baseline_period_days
    
    def detect_temporal_drift(self, df, column, window_days=7):
        """
        Detect drift over time periods
        
        Args:
            df: DataFrame with 'date' and column to check
            column: Column to monitor
            window_days: Window size for rolling statistics
            
        Returns:
            dict: Drift metrics
        """
        if 'date' not in df.columns or column not in df.columns:
            logger.error(f"Missing 'date' or '{column}' column")
            return {}
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        df_sorted = df.sort_values('date')
        
        # Calculate rolling statistics
        rolling_mean = df_sorted[column].rolling(window=window_days).mean()
        rolling_std = df_sorted[column].rolling(window=window_days).std()
        
        # Compare recent vs baseline
        recent = df_sorted.tail(window_days)[column]
        overall_mean = df_sorted[column].mean()
        overall_std = df_sorted[column].std()
        
        # Calculate z-score of recent mean
        recent_mean = recent.mean()
        z_score = (recent_mean - overall_mean) / overall_std if overall_std > 0 else 0
        
        has_drift = abs(z_score) > 2  # More than 2 std devs
        
        report = {
            'column': column,
            'recent_mean': float(recent_mean),
            'overall_mean': float(overall_mean),
            'z_score': float(z_score),
            'has_drift': bool(has_drift),
        }
        
        if has_drift:
            logger.warning(f"⚠️  Drift detected in {column}: z={z_score:.2f}")
        else:
            logger.info(f"✅ No drift detected in {column}")
        
        return report
    
    def detect_county_drift(self, df, column, expected_mean=None, threshold_std=2):
        """
        Detect anomalies in county-level data
        
        Args:
            df: DataFrame with 'fips' and column
            column: Column to monitor
            expected_mean: Expected mean value (if None, uses overall mean)
            threshold_std: Number of std deviations for anomaly
            
        Returns:
            dict: Counties with anomalies
        """
        if 'fips' not in df.columns or column not in df.columns:
            logger.error(f"Missing 'fips' or '{column}' column")
            return {}
        
        county_stats = df.groupby('fips')[column].agg(['mean', 'std', 'count'])
        
        if expected_mean is None:
            expected_mean = df[column].mean()
        
        overall_std = df[column].std()
        
        # Find counties with anomalous means
        anomalies = {}
        
        for fips, row in county_stats.iterrows():
            county_mean = row['mean']
            z_score = (county_mean - expected_mean) / overall_std if overall_std > 0 else 0
            
            if abs(z_score) > threshold_std:
                anomalies[fips] = {
                    'mean': float(county_mean),
                    'z_score': float(z_score),
                    'count': int(row['count']),
                }
        
        if anomalies:
            logger.warning(f"⚠️  Anomalies detected in {len(anomalies)} counties")
        else:
            logger.info("✅ No county-level anomalies detected")
        
        return anomalies
    
    def detect_missing_data_drift(self, df, columns=None):
        """
        Detect changes in missing data patterns
        
        Args:
            df: DataFrame to check
            columns: Specific columns (None = all)
            
        Returns:
            dict: Missing data statistics
        """
        if columns is None:
            columns = df.columns
        
        report = {}
        
        for col in columns:
            if col in df.columns:
                missing_pct = (df[col].isna().sum() / len(df)) * 100
                
                if missing_pct > 10:  # Flag if >10% missing
                    report[col] = float(missing_pct)
                    logger.warning(f"⚠️  High missing rate in {col}: {missing_pct:.1f}%")
        
        if not report:
            logger.info("✅ Missing data patterns normal")
        
        return report
    
    def generate_drift_report(self, df, columns=None):
        """
        Generate comprehensive drift report
        
        Args:
            df: DataFrame to analyze
            columns: Columns to check
            
        Returns:
            dict: Complete drift analysis
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'temporal_drift': {},
            'county_drift': {},
            'missing_drift': {},
        }
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns
        
        for col in columns:
            # Temporal drift
            temporal = self.detect_temporal_drift(df, col)
            if temporal:
                report['temporal_drift'][col] = temporal
            
            # County drift
            county = self.detect_county_drift(df, col)
            if county:
                report['county_drift'][col] = county
        
        # Missing data drift
        report['missing_drift'] = self.detect_missing_data_drift(df, columns)
        
        logger.info(f"Drift report generated at {report['timestamp']}")
        
        return report
