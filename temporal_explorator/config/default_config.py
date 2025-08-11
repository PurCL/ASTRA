"""
Default configuration for the Temporal Explorator system.

This module contains default configuration values for all components
of the temporal explorator system.
"""

from typing import Dict, Any

# Default configuration for the entire system
DEFAULT_CONFIG: Dict[str, Any] = {
    # State mapper configuration
    "state_mapper": {
        "model_url": "http://54.202.245.166:8010/v1",
        "model_api_key": "reverse-training",
        "model_name": "llama-3.1-70b-inst-judge",
        "temperature": 0.7,
        "max_tokens": 1024,
        "max_retries": 5
    },
    
    # Action selector configuration
    "action_selector": {
        "action_selection_strategy": "deterministic",
    },
    
    # Prompt generator configuration
    "prompt_generator": {
        "mutator_model_url": "http://54.202.245.166:8010/v1",
        "mutator_model_api_key": "reverse-training",
        "mutator_model_name_or_path": "llama-3.1-70b-inst-judge",
        "mutator_model_temperature": 0.7,
        "mutator_model_max_tokens": 1024,
        "mutator_model_max_retries": 5
    },
    # Logging configuration
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "/data4/user/shen447/amazon_code_challenge/astra-share/temporal_explorator/log/temporal_explorator.log"
    }
}

def get_config() -> Dict[str, Any]:
    """
    Get the default configuration.
    
    Returns:
        Default configuration dictionary
    """
    return DEFAULT_CONFIG.copy()

def merge_config(user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge user configuration with default configuration.
    
    Args:
        user_config: User-provided configuration
        
    Returns:
        Merged configuration dictionary
    """
    import copy
    merged_config = copy.deepcopy(DEFAULT_CONFIG)
    
    def deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                deep_merge(base[key], value)
            else:
                base[key] = value
    
    deep_merge(merged_config, user_config)
    return merged_config 