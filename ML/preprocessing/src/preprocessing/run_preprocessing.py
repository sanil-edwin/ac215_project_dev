"""
Main preprocessing orchestration script

Runs the complete preprocessing pipeline:
1. Compute baselines (if not exists)
2. Compute anomalies for target year

Usage:
    python run_preprocessing.py
    python run_preprocessing.py --year 2024
    python run_preprocessing.py --skip-baselines
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import argparse
import logging
from datetime import datetime

from preprocessing.compute_baselines import main as compute_baselines_main
from preprocessing.compute_anomalies import main as compute_anomalies_main
from utils.gcs_utils import get_gcs_manager
from utils.config import load_config, get_env_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_baselines_exist(gcs_manager, config) -> bool:
    """Check if baselines already exist in GCS"""
    products = list(config['products'].keys())
    
    for product in products:
        baseline_path = f"{config['output']['baselines_path']}/{product}_baseline_daily.parquet"
        if not gcs_manager.blob_exists(baseline_path):
            return False
    
    return True


def main():
    """Main preprocessing pipeline"""
    parser = argparse.ArgumentParser(description='AgriGuard Preprocessing Pipeline')
    parser.add_argument('--year', type=int, help='Target year for anomaly detection')
    parser.add_argument('--skip-baselines', action='store_true', 
                       help='Skip baseline computation (use existing)')
    parser.add_argument('--baselines-only', action='store_true',
                       help='Only compute baselines, skip anomalies')
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    logger.info("="*70)
    logger.info("  AGRIGUARD - PREPROCESSING PIPELINE")
    logger.info("="*70)
    logger.info(f"Started: {start_time}")
    
    # Load configuration
    config = load_config()
    env_config = get_env_config()
    
    # Override year if provided
    if args.year:
        os.environ['YEAR'] = str(args.year)
        env_config['year'] = args.year
    
    year = env_config['year']
    logger.info(f"\nConfiguration:")
    logger.info(f"  Target year: {year}")
    logger.info(f"  Baseline period: {env_config['start_year']}-{env_config['end_year']}")
    logger.info(f"  Products: {list(config['products'].keys())}")
    logger.info(f"  Skip baselines: {args.skip_baselines}")
    logger.info(f"  Baselines only: {args.baselines_only}")
    
    # Initialize GCS
    try:
        gcs_manager = get_gcs_manager()
        logger.info(f"\n✓ Connected to GCS: {gcs_manager.bucket_name}")
    except Exception as e:
        logger.error(f"Failed to connect to GCS: {e}")
        sys.exit(1)
    
    # Step 1: Compute Baselines
    if not args.skip_baselines:
        logger.info("\n" + "="*70)
        logger.info("  STEP 1: BASELINE COMPUTATION")
        logger.info("="*70)
        
        # Check if baselines exist
        if check_baselines_exist(gcs_manager, config):
            logger.info("Baselines already exist. Use --skip-baselines to skip this step.")
            logger.info("Recomputing baselines...")
        
        try:
            compute_baselines_main()
            logger.info("\n✓ Baseline computation complete")
        except Exception as e:
            logger.error(f"Baseline computation failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        logger.info("\n⏩ Skipping baseline computation")
    
    if args.baselines_only:
        logger.info("\n✓ Baselines-only mode complete")
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"\nTotal time: {duration}")
        return
    
    # Step 2: Compute Anomalies
    logger.info("\n" + "="*70)
    logger.info("  STEP 2: ANOMALY DETECTION")
    logger.info("="*70)
    
    try:
        compute_anomalies_main()
        logger.info("\n✓ Anomaly detection complete")
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "="*70)
    logger.info("  ✅ PREPROCESSING PIPELINE COMPLETE")
    logger.info("="*70)
    logger.info(f"Started: {start_time}")
    logger.info(f"Completed: {end_time}")
    logger.info(f"Duration: {duration}")
    logger.info(f"\nOutputs in GCS:")
    logger.info(f"  Baselines: gs://{gcs_manager.bucket_name}/{config['output']['baselines_path']}/")
    logger.info(f"  Anomalies: gs://{gcs_manager.bucket_name}/{config['output']['anomalies_path']}/")
    logger.info(f"\nAnomaly data includes:")
    logger.info(f"  - Z-scores and anomaly classifications")
    logger.info(f"  - Persistence metrics (7d, 14d, 21d, 30d)")
    logger.info(f"  - Rolling averages and trends")
    logger.info(f"  - Growth stage information")
    logger.info(f"\nNext steps:")
    logger.info(f"  - Container 3: Stress Detection")
    logger.info(f"  - Container 4: Yield Forecasting models")


if __name__ == "__main__":
    main()
