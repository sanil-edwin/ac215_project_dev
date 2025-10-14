"""
Quick inspection of preprocessing outputs
Run this inside the Docker container or locally with dependencies installed
"""

import sys
import os
sys.path.insert(0, 'src')

from utils.gcs_utils import get_gcs_manager
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

def inspect_outputs():
    # Initialize GCS
    gcs = get_gcs_manager()
    
    print("\n" + "="*80)
    print("PREPROCESSING OUTPUTS INSPECTION")
    print("="*80)
    
    # 1. Baselines
    print("\n1. NDVI BASELINE DATA (Daily)")
    print("-"*80)
    baseline = gcs.download_dataframe("processed/baselines/ndvi_baseline_daily.parquet")
    print(f"Shape: {baseline.shape[0]:,} rows × {baseline.shape[1]} columns")
    print(f"\nColumns: {list(baseline.columns)}")
    print(f"\nFirst 10 rows:")
    print(baseline.head(10).to_string())
    
    # Sample a few specific records for illustration
    print(f"\n\nSample records from different counties:")
    sample = baseline.sample(min(5, len(baseline))).sort_values(['fips', 'doy'])
    print(sample.to_string())
    
    # 2. Baselines by Growth Stage
    print("\n\n2. NDVI BASELINE DATA (Growth Stages)")
    print("-"*80)
    baseline_stages = gcs.download_dataframe("processed/baselines/ndvi_baseline_stages.parquet")
    print(f"Shape: {baseline_stages.shape[0]:,} rows × {baseline_stages.shape[1]} columns")
    print(f"\nFirst 10 rows:")
    print(baseline_stages.head(10).to_string())
    
    # 3. Anomalies
    print("\n\n3. NDVI ANOMALY DATA (2025)")
    print("-"*80)
    anomalies = gcs.download_dataframe("processed/anomalies/ndvi_anomalies_2025.parquet")
    print(f"Shape: {anomalies.shape[0]:,} rows × {anomalies.shape[1]} columns")
    print(f"\nColumns: {list(anomalies.columns)}")
    print(f"\nFirst 10 rows:")
    print(anomalies.head(10).to_string())
    
    # 4. Anomaly Statistics
    print("\n\n4. ANOMALY DISTRIBUTION")
    print("-"*80)
    anomaly_counts = anomalies['anomaly_flag'].value_counts()
    total = len(anomalies)
    for flag, count in anomaly_counts.items():
        pct = 100 * count / total
        print(f"  {flag:12s}: {count:8,} ({pct:5.1f}%)")
    
    print("\n\n5. SUMMARY STATISTICS")
    print("-"*80)
    print(f"Date range: {anomalies['date'].min()} to {anomalies['date'].max()}")
    print(f"Counties covered: {anomalies['fips'].nunique()}")
    print(f"Bands: {anomalies['band'].unique().tolist()}")
    print(f"Growth stages: {anomalies['growth_stage'].unique().tolist()}")
    print(f"Total observations: {len(anomalies):,}")
    
    # 5. Z-score distribution
    print("\n\n6. Z-SCORE STATISTICS")
    print("-"*80)
    print(anomalies[['z_score', 'percentile', 'days_persistent_14d']].describe().to_string())
    
    # 6. Sample severe anomalies
    print("\n\n7. SAMPLE SEVERE STRESS EVENTS")
    print("-"*80)
    severe = anomalies[anomalies['anomaly_flag'] == 'severe'].head(10)
    if len(severe) > 0:
        print(severe[['fips', 'county_name', 'date', 'band', 'mean', 'z_score', 'days_persistent_14d']].to_string())
    else:
        print("No severe anomalies detected in 2025")
    
    # 7. Counties with most stress
    print("\n\n8. TOP 10 COUNTIES BY STRESS DAYS")
    print("-"*80)
    stressed = anomalies[anomalies['anomaly_flag'] != 'normal']
    if len(stressed) > 0:
        county_stress = stressed.groupby('county_name').size().sort_values(ascending=False).head(10)
        for i, (county, days) in enumerate(county_stress.items(), 1):
            print(f"  {i:2d}. {county:30s}: {days:5,} stress days")
    else:
        print("No stressed counties detected")
    
    print("\n" + "="*80)
    print("INSPECTION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    inspect_outputs()
