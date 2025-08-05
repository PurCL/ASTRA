"""
Configuration management for the Temporal Explorator system.

This module provides configuration utilities and default settings
for the temporal explorator system.
"""

from .default_config import DEFAULT_CONFIG, get_config, merge_config

__all__ = [
    "DEFAULT_CONFIG",
    "get_config",
    "merge_config"
] 