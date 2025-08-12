"""
Prompt generator module for generating prompts based on actions and session data.

This module provides the PromptGenerator class which creates appropriate prompts
for different actions in the temporal explorator system.
"""

from typing import List, Dict, Any, Optional
from openai import OpenAI
import traceback

from rt.temporal_explorator.models.state import State
from rt.temporal_explorator.models.action import Action
from rt.temporal_explorator.prompts.system_prompts import (
    ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT,
    ASK_FOR_CODE_SYSTEM_PROMPT,
    PERSUASION_SYSTEM_PROMPT,
    REMOVE_IRRELEVANT_FACTOR_SYSTEM_PROMPT
)
from rt.temporal_explorator.utils.chat_utils import query_model
from rt.logger import purcl_logger_adapter


class PromptGenerator:
    """
    Generates prompts based on actions and session data.
    
    This class provides a simplified interface for generating prompts
    for different actions in the temporal explorator system.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the PromptGenerator.
        
        Args:
            config: Configuration dictionary containing model parameters
        """
        
        self.config = config
        
        # Initialize model client for prompt generation
        model_url = config.get('mutator_model_url', 'http://localhost:8000/v1')
        model_api_key = config.get('mutator_model_api_key', 'default')
        purcl_logger_adapter.debug(f"Initializing model client with URL: {model_url}")
        
        self.model_client = OpenAI(
            base_url=model_url,
            api_key=model_api_key
        )
        self.model_name = config.get('mutator_model_name_or_path', 'gpt-3.5-turbo')
        self.temperature = config.get('mutator_model_temperature', 0.7)
        self.max_tokens = config.get('mutator_model_max_tokens', 500)
        self.max_retries = config.get('mutator_model_max_retries', 3)
        
    
    def generate_prompt(
        self,
        session_data: List[Dict[str, str]],
        action: Action,
        context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Generate a prompt based on the action and session data.
        
        Args:
            session_data: List of session data dictionaries
            action: The action to generate a prompt for
            context: Optional context information
            
        Returns:
            The generated prompt
            
        Raises:
            ValueError: If the action is not supported or session data is invalid
        """
        purcl_logger_adapter.info(f"Generating prompt for action: {action}")
        purcl_logger_adapter.debug(f"Session data length: {len(session_data)}")
        purcl_logger_adapter.debug(f"Context: {context}")
        
        try:
            if not session_data:
                purcl_logger_adapter.error("Session data cannot be empty")
                raise ValueError("Session data cannot be empty")
            
            # Direct method dispatch based on action
            if action == Action.PERSUASION:
                purcl_logger_adapter.debug("Generating persuasion prompt")
                result, reasoning = self._generate_persuasion_prompt(session_data)
            elif action == Action.REMOVE_IRRELEVANT_FACTOR:
                purcl_logger_adapter.debug("Generating remove irrelevant factor prompt")
                result, reasoning = self._generate_remove_irrelevant_factor_prompt(session_data)
            elif action == Action.ASK_FOR_REASONING_TRACE:
                purcl_logger_adapter.debug("Generating reasoning trace prompt")
                result, reasoning = self._generate_reasoning_trace_prompt(session_data)
            elif action == Action.ASK_FOR_CODE:
                purcl_logger_adapter.debug("Generating code prompt")
                result, reasoning = self._generate_code_prompt(session_data)
            else:
                purcl_logger_adapter.error(f"Unsupported action: {action}")
                raise ValueError(f"Unsupported action: {action}")
            
            purcl_logger_adapter.info(f"Generated prompt length: {len(result) if result else 0}")
            return result, reasoning
            
        except Exception as e:
            purcl_logger_adapter.error(f"Error in prompt generation: {e}")
            # add traceback
            purcl_logger_adapter.error(traceback.format_exc())
            # Return a safe default prompt
            purcl_logger_adapter.warning("Returning default prompt")
            return self._generate_default_prompt(session_data, action)
    
    def _generate_persuasion_prompt(self, session_data: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Generate a persuasion prompt.
        
        Args:
            session_data: List of session data dictionaries
            
        Returns:
            The persuasion prompt
        """
        goal = session_data[0]["goal"]
        seed_prompt = session_data[0]["prompt"]
        previous_response = session_data[-1]["response"]

        query = PERSUASION_SYSTEM_PROMPT.format(
            seed_prompt=seed_prompt,
            valid_trace=previous_response,
            goal=goal,
        )

        messages = [
            {"role": "user", "content": query},
        ]
        result_dict = query_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages,
            tag_names=["Prompt", "Reasoning"]
        )

        if result_dict is None or "Prompt" not in result_dict:
            purcl_logger_adapter.error(f"PersuasionMutator: Failed to get response or extract Prompt tag from model")
            return None, ""

        return result_dict["Prompt"], result_dict["Reasoning"]
    
    def _generate_remove_irrelevant_factor_prompt(self, session_data: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Generate a prompt for removing irrelevant factors.
        
        Args:
            session_data: List of session data dictionaries
            
        Returns:
            The refined prompt
        """
        goal = session_data[0]["goal"]
        seed_prompt = session_data[0]["prompt"]
        previous_response = session_data[-1]["response"]
        previous_state = session_data[-1]["state"]

        query = REMOVE_IRRELEVANT_FACTOR_SYSTEM_PROMPT.format(
            seed_prompt=seed_prompt,
            invalid_trace=previous_response,
            goal=goal,
        )
        messages = [
            {"role": "user", "content": query},
        ]
        result_dict = query_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages,
            tag_names=["Prompt", "Reasoning"]
        )

        if result_dict is None or "Prompt" not in result_dict:
            purcl_logger_adapter.error(f"RemoveIrrelevantFactorMutator: Failed to get response or extract Prompt tag from model")
            return None, ""
        
        return result_dict["Prompt"], result_dict["Reasoning"]
    
    def _generate_reasoning_trace_prompt(self, session_data: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Generate a prompt for requesting reasoning trace.
        
        Args:
            session_data: List of session data dictionaries
            
        Returns:
            The reasoning trace request prompt
        """
        goal = session_data[0]["goal"]
        previous_prompt = session_data[-1]["prompt"]
        previous_response = session_data[-1]["response"]
        previous_state = session_data[-1]["state"]

        query = ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT.format(
            user_request=previous_prompt,
            model_response=previous_response,
            goal=goal,
            state=previous_state,
        )
        messages = [
            {"role": "user", "content": query},
        ]
        result_dict = query_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages,
            tag_names=["Prompt", "Reasoning"]
        )

        if result_dict is None or "Prompt" not in result_dict:
            purcl_logger_adapter.error(f"AskForReasoningTraceMutator: Failed to get response or extract Prompt tag from model")
            return None, ""
        
        return result_dict["Prompt"], result_dict["Reasoning"]
    
    def _generate_code_prompt(self, session_data: List[Dict[str, str]]) -> tuple[str, str]:
        """
        Generate a prompt for requesting code implementation.
        
        Args:
            session_data: List of session data dictionaries
            
        Returns:
            The code request prompt
        """
        goal = session_data[0]["goal"]
        previous_prompt = session_data[-1]["prompt"]
        previous_response = session_data[-1]["response"]

        query = ASK_FOR_CODE_SYSTEM_PROMPT.format(
            user_request=previous_prompt,
            model_response=previous_response,
            goal=goal,
        )
        messages = [
            {"role": "user", "content": query},
        ]
        result_dict = query_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages,
            tag_names=["Prompt", "Reasoning"]
        )

        if result_dict is None or "Prompt" not in result_dict:
            purcl_logger_adapter.error(f"AskForCodeMutator: Failed to get response or extract Prompt tag from model")
            return None, ""

        return result_dict["Prompt"], result_dict["Reasoning"]
    
    def _generate_default_prompt(self, session_data: List[Dict[str, str]], action: Action) -> tuple[str, str]:
        """
        Generate a default prompt when the main generation fails.
        
        Args:
            session_data: List of session data dictionaries
            action: The action to generate a prompt for
            
        Returns:
            A default prompt
        """
        if not session_data:
            return "Please provide a response.", ""
        
        # Get the last response for context
        last_response = session_data[-1].get("response", "")
        
        if action == Action.ASK_FOR_REASONING_TRACE:
            return f"Can you explain your reasoning for the previous response: {last_response}", ""
        elif action == Action.ASK_FOR_CODE:
            return "Please provide the code implementation.", ""
        elif action == Action.PERSUASION:
            return "Please reconsider your previous response.", ""
        elif action == Action.REMOVE_IRRELEVANT_FACTOR:
            return "Please provide a more focused response.", ""
        else:
            return "Please provide a response.", ""


