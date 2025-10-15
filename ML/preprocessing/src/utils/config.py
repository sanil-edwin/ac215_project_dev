"""
Configuration management utilities
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/feature_config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    if not os.path.exists(config_path):
        # Try relative to script location
        script_dir = Path(__file__).parent.parent.parent
        config_path = script_dir / config_path
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    logger.info(f"Loaded configuration from {config_path}")
    return config


def get_growth_stage(day_of_year: int, config: Dict[str, Any]) -> str:
    """
    Determine growth stage from day of year
    
    Args:
        day_of_year: Day of year (1-365)
        config: Configuration dictionary
        
    Returns:
        Growth stage name
    """
    stages = config['growth_stages']
    
    for stage_name, stage_info in stages.items():
        if stage_info['start_doy'] <= day_of_year <= stage_info['end_doy']:
            return stage_name
    
    return 'unknown'


def classify_anomaly(z_score: float, config: Dict[str, Any]) -> str:
    """
    Classify anomaly severity from z-score
    
    Args:
        z_score: Standardized anomaly value
        config: Configuration dictionary
        
    Returns:
        Anomaly classification
    """
    thresholds = config['anomaly_thresholds']
    
    abs_z = abs(z_score)
    
    if abs_z <= thresholds['normal']['max']:
        return 'normal'
    elif abs_z <= thresholds['mild']['max']:
        return 'mild'
    elif abs_z <= thresholds['moderate']['max']:
        return 'moderate'
    else:
        return 'severe'


def get_env_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables
    
    Returns:
        Environment configuration dictionary
    """
    return {
        'gcs_bucket': os.getenv('GCS_BUCKET_NAME', 'agriguard-ac215-data'),
        'gcp_project': os.getenv('GCP_PROJECT_ID', 'agriguard-ac215'),
        'temp_dir': os.getenv('TEMP_DIR', './temp'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
        'year': int(os.getenv('YEAR', '2024')),
        'start_year': int(os.getenv('START_YEAR', '2017')),
        'end_year': int(os.getenv('END_YEAR', '2023')),
    }
