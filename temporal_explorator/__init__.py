"""
Temporal Explorator Module

A module for managing multi-turn conversations with AI models,
providing state management, action selection, and prompt generation.
"""

from .core.temporal_explorator import TemporalExplorator
from .core.state_mapper import StateMapper
from .core.action_selector import ActionSelector
from .core.prompt_generator import PromptGenerator
from .models.state import State
from .models.action import Action
from .entry import get_next_attack_prompt, create_explorer, get_explorer, reset_explorer

__version__ = "1.0.0"
__author__ = "Temporal Explorator Team"

__all__ = [
    "TemporalExplorator",
    "StateMapper", 
    "ActionSelector",
    "PromptGenerator",
    "State",
    "Action",
    "get_next_attack_prompt",
    "create_explorer",
    "get_explorer", 
    "reset_explorer"
] 