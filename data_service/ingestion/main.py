#!/usr/bin/env python3
"""
AgriGuard Data Ingestion - Unified Entry Point

Supports downloading from multiple sources:
- mask: USDA CDL corn masks
- yield: USDA NASS corn yields
- ndvi: MODIS NDVI satellite data
- lst: MODIS Land Surface Temperature
- vpd: gridMET Vapor Pressure Deficit
- eto: gridMET Reference Evapotranspiration
- precip: gridMET Precipitation

Usage:
    python main.py --download mask
    python main.py --download yield
    python main.py --download ndvi
    etc.
"""

import sys
import os
import argparse
import logging
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_mask_downloader():
    """Download USDA CDL corn masks."""
    logger.info("Starting mask downloader...")
    from downloaders import mask
    mask.main()


def run_yield_downloader():
    """Download USDA NASS corn yields."""
    logger.info("Starting yield downloader...")
    from downloaders import yield_ as yield_module
    yield_module.main()


def run_ndvi_downloader():
    """Download MODIS NDVI data."""
    logger.info("Starting NDVI downloader...")
    from downloaders import ndvi
    ndvi.main()


def run_lst_downloader():
    """Download MODIS LST data."""
    logger.info("Starting LST downloader...")
    from downloaders import lst
    lst.main()


def run_vpd_downloader():
    """Download gridMET VPD data."""
    logger.info("Starting VPD downloader...")
    from downloaders import vpd
    vpd.main()


def run_eto_downloader():
    """Download gridMET ETo data."""
    logger.info("Starting ETo downloader...")
    from downloaders import eto
    eto.main()


def run_precip_downloader():
    """Download gridMET Precipitation data."""
    logger.info("Starting Precipitation downloader...")
    from downloaders import precip
    precip.main()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='AgriGuard Data Ingestion Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --download mask
  python main.py --download yield
  python main.py --download ndvi
  
Environment variables can override parameters (see individual scripts).
        """
    )
    
    parser.add_argument(
        '--download',
        choices=['mask', 'yield', 'ndvi', 'lst', 'vpd', 'eto', 'precip'],
        required=True,
        help='Which data source to download from'
    )
    
    args = parser.parse_args()
    
    try:
        if args.download == 'mask':
            run_mask_downloader()
        elif args.download == 'yield':
            run_yield_downloader()
        elif args.download == 'ndvi':
            run_ndvi_downloader()
        elif args.download == 'lst':
            run_lst_downloader()
        elif args.download == 'vpd':
            run_vpd_downloader()
        elif args.download == 'eto':
            run_eto_downloader()
        elif args.download == 'precip':
            run_precip_downloader()
        else:
            parser.print_help()
            sys.exit(1)
            
        logger.info(f"✓ {args.download.upper()} download completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Error during {args.download} download: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
