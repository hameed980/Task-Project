"""
Utility module for structured logging and general configurations.
Ensures both file logging (in logs/ folder) and console logging exist.
"""

import logging
import os
import sys
import warnings
from datetime import datetime

# Suppress annoying third-party deprecation warnings in stdout/logs
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

def setup_logger(name: str = "etl_pipeline") -> logging.Logger:
    """Sets up a structured logger pointing to both console and a log file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Avoid duplicating handlers
        
    logger.setLevel(logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # File handler (JSON-friendly or clean text format)
    log_filename = f"etl_run_{datetime.now().strftime('%Y%m%d')}.log"
    file_path = os.path.join(log_dir, log_filename)
    
    file_formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}'
    )
    
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(module)s]: %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
