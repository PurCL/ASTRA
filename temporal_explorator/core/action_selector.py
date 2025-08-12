"""
Action selector module for determining the next action based on conversation state.

This module provides the ActionSelector class which maps conversation states
to appropriate actions for the temporal explorator system.
"""

from typing import Dict, Any, Optional
from enum import Enum

from rt.temporal_explorator.models.state import State
from rt.temporal_explorator.models.action import Action
from rt.logger import purcl_logger_adapter


class ActionSelectionStrategy(Enum):
    """Enumeration of different action selection strategies."""
    DETERMINISTIC = "deterministic"
    RANDOM = "random"
    WEIGHTED = "weighted"


class ActionSelector:
    """
    Selects the next action based on the current conversation state.
    
    This class implements a state machine that maps conversation states
    to appropriate actions for guiding the conversation toward the goal.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the ActionSelector.
        
        Args:
            config: Configuration dictionary containing action selection parameters
        """
        
        self.config = config or {}
        strategy_name = self.config.get('action_selection_strategy', 'deterministic')
        purcl_logger_adapter.debug(f"Action selection strategy: {strategy_name}")
        
        self.strategy = ActionSelectionStrategy(strategy_name)
        
        # Initialize action mapping
        purcl_logger_adapter.debug("Initializing action mapping...")
        self._action_mapping = self._initialize_action_mapping()
        
        # Initialize action weights for weighted selection
        self._action_weights = self.config.get('action_weights', {})
        purcl_logger_adapter.debug(f"Action weights: {self._action_weights}")
        
        purcl_logger_adapter.info("ActionSelector initialized successfully")
    
    def select(self, state: State, context: Optional[Dict[str, Any]] = None) -> Action:
        """
        Select the next action based on the current state.
        
        Args:
            state: Current conversation state
            context: Optional context information for action selection
            
        Returns:
            The selected action
            
        Raises:
            ValueError: If the state is invalid or no action can be determined
        """
        purcl_logger_adapter.info(f"Selecting action for state: {state}")
        purcl_logger_adapter.debug(f"Context: {context}")
        
        try:
            if state not in self._action_mapping:
                purcl_logger_adapter.error(f"Invalid state: {state}")
                raise ValueError(f"Invalid state: {state}")
            
            actions = self._action_mapping[state]
            purcl_logger_adapter.debug(f"Available actions for state {state}: {actions}")
            
            if not actions:
                purcl_logger_adapter.error(f"No actions defined for state: {state}")
                raise ValueError(f"No actions defined for state: {state}")
            
            selected_action = None
            if self.strategy == ActionSelectionStrategy.DETERMINISTIC:
                purcl_logger_adapter.debug("Using deterministic selection")
                selected_action = self._select_deterministic(actions)
            elif self.strategy == ActionSelectionStrategy.RANDOM:
                purcl_logger_adapter.debug("Using random selection")
                selected_action = self._select_random(actions)
            elif self.strategy == ActionSelectionStrategy.WEIGHTED:
                purcl_logger_adapter.debug("Using weighted selection")
                selected_action = self._select_weighted(actions, context)
            else:
                purcl_logger_adapter.error(f"Unknown action selection strategy: {self.strategy}")
                raise ValueError(f"Unknown action selection strategy: {self.strategy}")
            
            purcl_logger_adapter.info(f"Selected action: {selected_action}")
            return selected_action
                
        except Exception as e:
            purcl_logger_adapter.error(f"Error in action selection: {e}")
            # Return a safe default action
            purcl_logger_adapter.warning("Returning default action: SEND_SEED_PROMPT")
            return Action.SEND_SEED_PROMPT
    
    def _initialize_action_mapping(self) -> Dict[State, list]:
        """
        Initialize the mapping from states to possible actions.
        
        Returns:
            Dictionary mapping states to lists of possible actions
        """
        return {
            
            # States that require reasoning trace
            State.IRRELEVANT: [Action.ASK_FOR_REASONING_TRACE],
            State.REFUSAL: [Action.ASK_FOR_REASONING_TRACE],
            State.ANSWER_WITH_CODE_WITHOUT_GOAL: [Action.ASK_FOR_REASONING_TRACE],
            # States that require persuasion or alternative strategies
            State.VALID_REASONING_TRACE: [Action.PERSUASION],
            # States that require prompt refinement
            State.INVALID_REASONING_TRACE: [Action.REMOVE_IRRELEVANT_FACTOR],
            
            # States that require code generation
            State.ANSWER_WITH_NO_CODE: [Action.ASK_FOR_CODE],
            
            # Terminal states (no actions needed)
            State.JAILBROKEN: [],
            State.ABORT: []
        }
    
    def _select_deterministic(self, actions: list) -> Action:
        """
        Select the first action from the list (deterministic selection).
        
        Args:
            actions: List of possible actions
            
        Returns:
            The selected action
        """
        return actions[0]
    
    def _select_random(self, actions: list) -> Action:
        """
        Select a random action from the list.
        
        Args:
            actions: List of possible actions
            
        Returns:
            The selected action
        """
        import random
        return random.choice(actions)
    
    def _select_weighted(self, actions: list, context: Optional[Dict[str, Any]] = None) -> Action:
        """
        Select an action based on weights and context.
        
        Args:
            actions: List of possible actions
            context: Optional context information
            
        Returns:
            The selected action
        """
        import random
        
        # Get weights for the available actions
        weights = []
        for action in actions:
            weight = self._action_weights.get(action.value, 1.0)
            
            # Apply context-based weight adjustments
            if context:
                weight = self._adjust_weight_by_context(action, weight, context)
            
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return self._select_random(actions)
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Select based on weights
        return random.choices(actions, weights=normalized_weights)[0]
    
    def _adjust_weight_by_context(self, action: Action, base_weight: float, context: Dict[str, Any]) -> float:
        """
        Adjust action weight based on context information.
        
        Args:
            action: The action being considered
            base_weight: Base weight for the action
            context: Context information
            
        Returns:
            Adjusted weight
        """
        adjusted_weight = base_weight
        
        # Example context-based adjustments
        if 'conversation_turn' in context:
            turn_count = context['conversation_turn']
            # Reduce persuasion weight after multiple attempts
            if action == Action.PERSUASION and turn_count > 3:
                adjusted_weight *= 0.5
        
        if 'previous_actions' in context:
            previous_actions = context['previous_actions']
            # Reduce weight for recently used actions
            if action in previous_actions[-2:]:
                adjusted_weight *= 0.7
        
        return adjusted_weight
    
    def get_available_actions(self, state: State) -> list:
        """
        Get all available actions for a given state.
        
        Args:
            state: The conversation state
            
        Returns:
            List of available actions
        """
        return self._action_mapping.get(state, [])
    
    def add_action_mapping(self, state: State, actions: list) -> None:
        """
        Add or update action mapping for a state.
        
        Args:
            state: The conversation state
            actions: List of actions for this state
        """
        self._action_mapping[state] = actions
    
    def set_action_weights(self, weights: Dict[str, float]) -> None:
        """
        Set weights for action selection.
        
        Args:
            weights: Dictionary mapping action names to weights
        """
        self._action_weights.update(weights)
    
    def get_action_description(self, action: Action) -> str:
        """
        Get a human-readable description of an action.
        
        Args:
            action: The action to describe
            
        Returns:
            Description of the action
        """
        descriptions = {
            Action.SEND_SEED_PROMPT: "Send the initial seed prompt to the model",
            Action.ASK_FOR_REASONING_TRACE: "Request a detailed reasoning trace from the model",
            Action.PERSUASION: "Attempt to persuade the model to reconsider its position",
            Action.INTENTION_OBFUSCATION: "Obfuscate the true intention to bypass safety measures",
            Action.TASK_DECOMPOSITION: "Break down the task into smaller, less suspicious components",
            Action.REMOVE_IRRELEVANT_FACTOR: "Refine the prompt by removing irrelevant factors",
            Action.ASK_FOR_CODE: "Request specific code implementation from the model"
        }
        
        return descriptions.get(action, f"Unknown action: {action.value}")

