"""Configuration package for LM Studio Bridge Enhanced."""

# Import all constants
import os

# Import config_main functionality
import sys

from .constants import *

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_main import Config, LMStudioConfig, MCPConfig, get_config, reset_config

# Make everything available from config package
__all__ = [
    'get_config',
    'Config',
    'LMStudioConfig',
    'MCPConfig',
    'reset_config',
]
