"""Logging utilities for data ingestion"""
from loguru import logger
import sys


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration
    
    Args:
        verbose: If True, set to DEBUG level, otherwise INFO
    """
    logger.remove()
    
    level = "DEBUG" if verbose else "INFO"
    
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    return logger
