"""Configuration package for LM Studio Bridge Enhanced."""

# Import all constants
from .constants import *

# Import config_main functionality
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_main import get_config, Config, LMStudioConfig, MCPConfig, reset_config

# Make everything available from config package
__all__ = [
    'get_config',
    'Config',
    'LMStudioConfig',
    'MCPConfig',
    'reset_config',
]
