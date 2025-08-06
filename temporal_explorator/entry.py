"""
Entry point for the TemporalExplorator module.

This module provides the main interface for the temporal exploration system,
handling multi-turn conversations with state mapping, action selection, and prompt generation.
"""

from typing import List, Dict, Optional, Any

from .core.temporal_explorator import TemporalExplorator
from .utils.logger import logger, purcl_logger_adapter


# Global instance for backward compatibility
_explorer_instance: Optional[TemporalExplorator] = None


def get_next_attack_prompt(
    bt_id: str,
    session_id: str,
    chat_history: List[Dict[str, str]],
    config: Dict[str, Any],
    goal: str,
    save_dir: str = "sessions",
) -> str:
    """
    Backward compatible function for getting the next attack prompt.
    
    This function maintains the original interface while using the new
    TemporalExplorator class internally.
    
    Args:
        bt_id: Backend target ID
        session_id: Session identifier
        chat_history: List of chat messages
        config: Configuration dictionary
        goal: Optional goal for the session
        
    Returns:
        Generated prompt for the next turn
    """
    purcl_logger_adapter.info(f"Getting next attack prompt for session: {bt_id}_{session_id}")
    purcl_logger_adapter.debug(f"Chat history length: {len(chat_history)}")
    purcl_logger_adapter.debug(f"Goal: {goal}")
    purcl_logger_adapter.debug(f"Save directory: {save_dir}")
    
    global _explorer_instance
    
    # Initialize explorer if not already done
    if _explorer_instance is None:
        purcl_logger_adapter.info("Creating new TemporalExplorator instance")
        _explorer_instance = TemporalExplorator(config, save_dir)
    else:
        purcl_logger_adapter.debug("Using existing TemporalExplorator instance")
    
    result, state = _explorer_instance.process_turn(bt_id, session_id, chat_history, goal)
    purcl_logger_adapter.info(f"Generated prompt length: {len(result) if result else 0}")
    purcl_logger_adapter.info(f"State: {state}")
    return result, state


def create_explorer(config: Dict[str, Any], save_dir: str = "sessions") -> TemporalExplorator:
    """
    Create a new TemporalExplorator instance.
    
    Args:
        config: Configuration dictionary
        save_dir: Directory to save session files (default: "sessions")
        
    Returns:
        TemporalExplorator instance
    """
    purcl_logger_adapter.info(f"Creating new TemporalExplorator with save_dir: {save_dir}")
    purcl_logger_adapter.debug(f"Config keys: {list(config.keys())}")
    
    explorer = TemporalExplorator(config, save_dir)
    purcl_logger_adapter.info("TemporalExplorator created successfully")
    return explorer


def get_explorer() -> Optional[TemporalExplorator]:
    """
    Get the global explorer instance.
    
    Returns:
        Global TemporalExplorator instance or None if not initialized
    """
    if _explorer_instance is None:
        purcl_logger_adapter.debug("No global explorer instance found")
    else:
        purcl_logger_adapter.debug("Retrieved global explorer instance")
    return _explorer_instance


def reset_explorer() -> None:
    """Reset the global explorer instance."""
    global _explorer_instance
    purcl_logger_adapter.info("Resetting global explorer instance")
    _explorer_instance = None