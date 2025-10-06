#!/usr/bin/env python3
"""Download USDA NASS County-Level Yield Data - CORN Only"""

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import requests
import click
from loguru import logger
import yaml
from typing import List
from datetime import datetime
import json

sys.path.append(str(Path(__file__).parent.parent))

from src.utils.gcs_utils import GCSManager
from src.utils.logging_utils import setup_logging


class YieldDataDownloader:
    def __init__(self, config_path: str = "configs/data_config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        bucket_name = os.getenv('GCS_BUCKET', self.config['gcs']['bucket'])
        self.gcs = GCSManager(bucket_name=bucket_name)
        
        self.api_key = os.getenv('USDA_NASS_API_KEY')
        self.base_url = self.config['usda_nass']['api_base_url']
        
        logger.info("? YieldDataDownloader initialized")
        logger.info(f"  Target: {self.config['iowa_state']['name']}")
        logger.info(f"  Crop: {self.config['usda_nass']['commodity']}")
    
    def download_county_yields(self, years: List[int]) -> pd.DataFrame:
        """Download real USDA NASS yield data for CORN"""
        
        if not self.api_key:
            logger.warning("No API key - generating sample data")
            return self.generate_sample_data(years)
        
        logger.info(f"?? Downloading REAL Iowa CORN yield data")
        logger.info(f"   Years: {years}")
        
        all_data = []
        
        for year in years:
            logger.info(f"?? Year {year}...")
            
            params = {
                'key': self.api_key,
                'source_desc': 'SURVEY',
                'sector_desc': 'CROPS',
                'group_desc': 'FIELD CROPS',
                'commodity_desc': 'CORN',
                'statisticcat_desc': 'YIELD',
                'agg_level_desc': 'COUNTY',
                'state_name': 'IOWA',
                'year': year,
                'format': 'JSON'
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=300)
                response.raise_for_status()
                
                data = response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    df_year = pd.DataFrame(data['data'])
                    all_data.append(df_year)
                    logger.success(f"   ? {len(data['data'])} records")
                else:
                    logger.warning(f"   ??  No data for {year}")
                    
            except Exception as e:
                logger.error(f"   ? Error: {str(e)}")
                continue
        
        if not all_data:
            logger.error("? No data downloaded!")
            return pd.DataFrame()
        
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.success(f"? Downloaded {len(combined_df)} total records")
        
        cleaned_df = self._clean_yield_data(combined_df)
        return cleaned_df
    
    def _clean_yield_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize yield data - CORN only"""
        
        logger.info("?? Cleaning data...")
        
        # Select relevant columns
        base_columns = ['year', 'state_name', 'county_name', 'commodity_desc', 'Value']
        optional_columns = ['state_fips_code', 'county_code', 'class_desc', 'unit_desc']
        
        columns_to_keep = [col for col in base_columns + optional_columns if col in df.columns]
        df = df[columns_to_keep].copy()
        
        # Convert yield to numeric
        df['Value_clean'] = df['Value'].astype(str).str.replace(',', '').str.replace(' ', '')
        df['yield_bu_per_acre'] = pd.to_numeric(df['Value_clean'], errors='coerce')
        
        # Rename columns
        df = df.rename(columns={'county_name': 'county', 'state_name': 'state'})
        
        # Remove rows with missing yields
        before = len(df)
        df = df.dropna(subset=['yield_bu_per_acre'])
        logger.info(f"Removed missing yields: {before} ? {len(df)} records")
        
        # Remove unrealistic yields
        before = len(df)
        df = df[(df['yield_bu_per_acre'] > 0) & (df['yield_bu_per_acre'] < 500)]
        logger.info(f"Removed unrealistic yields: {before} ? {len(df)} records")
        
        # Sort
        df = df.sort_values(['year', 'county'])
        
        logger.success(f"? Final cleaned data: {len(df)} records")
        
        return df
    
    def generate_sample_data(self, years: List[int]) -> pd.DataFrame:
        """Generate sample yield data for testing"""
        
        logger.warning("?? Generating SAMPLE data")
        
        counties = self.config.get('iowa_counties', ['Story', 'Hamilton', 'Wright'])
        
        data = []
        for year in years:
            for county in counties:
                base_yield = 175
                trend = (year - 2015) * 2.0
                county_effect = hash(county) % 30 - 15
                random_var = np.random.normal(0, 12)
                
                yield_val = base_yield + trend + county_effect + random_var
                yield_val = max(130, min(220, yield_val))
                
                data.append({
                    'year': year,
                    'state': 'IOWA',
                    'county': county,
                    'commodity_desc': 'CORN',
                    'yield_bu_per_acre': round(yield_val, 1)
                })
        
        df = pd.DataFrame(data)
        logger.success(f"? Generated {len(df)} sample records")
        return df
    
    def save_to_local(self, df: pd.DataFrame, filename: str) -> str:
        """Save DataFrame locally"""
        
        local_dir = "/app/data/raw/yields"
        os.makedirs(local_dir, exist_ok=True)
        
        local_path = os.path.join(local_dir, filename)
        df.to_csv(local_path, index=False)
        
        logger.success(f"?? Saved: {local_path}")
        
        metadata = {
            'filename': filename,
            'timestamp': datetime.now().isoformat(),
            'records': len(df),
            'years': sorted(df['year'].unique().tolist()),
            'counties': df['county'].nunique(),
            'state': 'IOWA',
            'crop': 'CORN',
            'avg_yield': float(df['yield_bu_per_acre'].mean()),
            'min_yield': float(df['yield_bu_per_acre'].min()),
            'max_yield': float(df['yield_bu_per_acre'].max())
        }
        
        metadata_path = local_path.replace('.csv', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return local_path


@click.command()
@click.option('--start-year', type=int, default=2020)
@click.option('--end-year', type=int, default=2024)
@click.option('--sample', is_flag=True)
@click.option('--skip-upload', is_flag=True)
@click.option('--verbose', is_flag=True)
def main(start_year, end_year, sample, skip_upload, verbose):
    """Download Iowa CORN Yield Data"""
    
    setup_logging(verbose=verbose)
    
    logger.info("="*70)
    logger.info("AgriGuard - Iowa CORN Yield Data Download")
    logger.info("="*70)
    
    downloader = YieldDataDownloader()
    years = list(range(start_year, end_year + 1))
    
    if sample:
        df = downloader.generate_sample_data(years)
    else:
        df = downloader.download_county_yields(years)
    
    if df.empty:
        logger.error("? No data!")
        sys.exit(1)
    
    filename = f"iowa_corn_yields_{start_year}_{end_year}.csv"
    local_path = downloader.save_to_local(df, filename)
    
    logger.info("\n" + "="*70)
    logger.info("?? SUMMARY")
    logger.info("="*70)
    logger.info(f"Records: {len(df):,}")
    logger.info(f"Years: {sorted(df['year'].unique().tolist())}")
    logger.info(f"Counties: {df['county'].nunique()}")
    logger.info(f"Avg Yield: {df['yield_bu_per_acre'].mean():.1f} bu/acre")
    logger.info(f"File: {local_path}")
    logger.info("="*70)
    logger.success("? Complete!")


if __name__ == "__main__":
    main()
