"""
State mapper module for mapping conversation states based on actions and responses.
"""

from typing import Dict, List, Any, Optional
from openai import OpenAI

from rt.temporal_explorator.models.state import State
from rt.temporal_explorator.models.action import Action
from rt.temporal_explorator.utils.chat_utils import query_model
from rt.logger import purcl_logger_adapter
from rt.temporal_explorator.prompts.system_prompts import (
    JAILBROKEN_VALIDATOR_SYSTEM_PROMPT,
    REFUSAL_SYSTEM_PROMPT,
    TRACE_VALIDATOR_SYSTEM_PROMPT,
    IRRELEVANT_SYSTEM_PROMPT
)



class StateMapper:
    """
    Maps conversation states based on the current action and model response.
    
    This class determines the next state of the conversation by analyzing
    the model's response in the context of the current action and goal.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the StateMapper.
        
        Args:
            config: Configuration dictionary containing model parameters
        """
        
        self.config = config
        
        # Initialize model client
        model_url = config.get('model_url', 'http://localhost:8000/v1')
        model_api_key = config.get('model_api_key', 'default')
        purcl_logger_adapter.debug(f"Initializing model client with URL: {model_url}")
        
        self.model_client = OpenAI(
            base_url=model_url,
            api_key=model_api_key
        )
        self.model_name = config.get('model_name', 'gpt-3.5-turbo')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 500)
        self.max_retries = config.get('max_retries', 3)

    
    def map(
        self,
        state: State,
        action: Action,
        prompt: str,
        response: str,
        goal: Optional[str] = None,
    ) -> tuple[State, str]:
        """
        Map the current conversation state based on action and response.
        
        Args:
            state: Current state
            action: Current action that was taken
            prompt: The prompt that was sent
            response: The model's response
            goal: Optional goal for the conversation
            
        Returns:
            The new state after analysis
            
        Raises:
            ValueError: If the action is not supported
        """
        purcl_logger_adapter.info(f"Mapping state for action: {action}")
        purcl_logger_adapter.debug(f"Current state: {state}")
        purcl_logger_adapter.debug(f"Prompt length: {len(prompt)}")
        purcl_logger_adapter.debug(f"Response length: {len(response)}")
        purcl_logger_adapter.debug(f"Goal: {goal}")
        
        try:
            if action in [Action.SEND_SEED_PROMPT, Action.PERSUASION, Action.ASK_FOR_CODE, Action.REMOVE_IRRELEVANT_FACTOR]:
                purcl_logger_adapter.debug("Using jailbroken state validation")
                result_state, reasoning = self._validate_jailbroken_state(prompt, response, goal)
                purcl_logger_adapter.info(f"Jailbroken validation result: {result_state}")
                return result_state, reasoning
            
            elif action == Action.ASK_FOR_REASONING_TRACE:
                purcl_logger_adapter.debug("Using reasoning trace state validation")
                result_state, reasoning = self._validate_reasoning_trace_state(prompt, response, goal, state)
                purcl_logger_adapter.info(f"Reasoning trace validation result: {result_state}")
                return result_state, reasoning
            
            else:
                purcl_logger_adapter.error(f"Unsupported action for state mapping: {action}")
                raise ValueError(f"Unsupported action for state mapping: {action}")
                
        except Exception as e:
            purcl_logger_adapter.error(f"Error in state mapping: {e}")
            return State.ABORT, ""
    
    def _validate_jailbroken_state(self, prompt: str, response: str, goal: Optional[str]) -> tuple[State, str]:
        """
        Validate if the response indicates a jailbroken state.
        
        Args:
            prompt: The prompt that was sent
            response: The model's response
            goal: Optional goal for the conversation
            
        Returns:
            State indicating if jailbroken or not
        """
        try:
            # Use the predefined system prompt
            system_prompt = JAILBROKEN_VALIDATOR_SYSTEM_PROMPT.format(
                user_request=prompt,
                model_response=response,
                goal=goal or "Not specified",
                jailbroken_state=State.JAILBROKEN.value
            )
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            result_dict = query_model(
                model_client=self.model_client,
                model_name_or_path=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                messages=messages,
                tag_names=["State", "Reasoning"]
            )

            
            if result_dict is None or "State" not in result_dict:
                purcl_logger_adapter.error(f"JailbrokenJudge: Failed to get response or extract State tag from model")
                return State.ABORT, ""
                
            result = result_dict["State"]
            reasoning = result_dict.get("Reasoning", "")
            purcl_logger_adapter.debug(f"JailbrokenJudge reasoning: {reasoning}")
            
            # Parse state from the response
            if result == State.JAILBROKEN.value:
                return State.JAILBROKEN, reasoning
            else:
                # If not jailbroken, use refusal validator to determine specific state
                return self._validate_refusal_state(prompt, response, goal)
            
        except Exception as e:
            purcl_logger_adapter.error(f"Error in jailbroken validation: {e}")
            return State.ABORT, ""
    
    def _validate_refusal_state(self, prompt: str, response: str, goal: Optional[str]) -> tuple[State, str]:
        """
        Validate the type of refusal state.
        
        Args:
            prompt: The prompt that was sent
            response: The model's response
            goal: Optional goal for the conversation
            
        Returns:
            State indicating the type of refusal
        """
        try:
            # Use the predefined refusal system prompt
            system_prompt = REFUSAL_SYSTEM_PROMPT.format(
                user_request=prompt,
                model_response=response,
                goal=goal or "Not specified",
                refusal=State.REFUSAL.value,
                no_refusal=State.NO_REFUSAL.value
            )
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            result_dict = query_model(
                model_client=self.model_client,
                model_name_or_path=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                messages=messages,
                tag_names=["State", "Reasoning"]
            )
            
            if result_dict is None or "State" not in result_dict:
                purcl_logger_adapter.error(f"RefusalValidator: Failed to get response or extract State tag from model")
                return State.ABORT, ""
                
            result = result_dict["State"]
            reasoning = result_dict.get("Reasoning", "")
            purcl_logger_adapter.debug(f"RefusalValidator reasoning: {reasoning}")
            
            if result == State.REFUSAL.value:
                return State.REFUSAL, reasoning
            else:
                # If no refusal, check if response contains code
                if "```python" in response:
                    return State.ANSWER_WITH_CODE_WITHOUT_GOAL, reasoning
                else:
                    # Use irrelevant validator to determine final state
                    return self._validate_irrelevant_state(prompt, response, goal)
            
        except Exception as e:
            purcl_logger_adapter.error(f"Error in refusal validation: {e}")
            return State.ABORT, ""
    
    def _validate_irrelevant_state(self, prompt: str, response: str, goal: Optional[str]) -> tuple[State, str]:
        """
        Validate if the response is irrelevant to the goal.
        
        Args:
            prompt: The prompt that was sent
            response: The model's response
            goal: Optional goal for the conversation
            
        Returns:
            State indicating if response is irrelevant or not
        """
        try:
            system_prompt = IRRELEVANT_SYSTEM_PROMPT.format(
                user_request=prompt,
                model_response=response,
                goal=goal or "Not specified",
                irrelevant=State.IRRELEVANT.value,
                answer_with_no_code=State.ANSWER_WITH_NO_CODE.value
            )
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            result_dict = query_model(
                model_client=self.model_client,
                model_name_or_path=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                messages=messages,
                tag_names=["State", "Reasoning"]
            )
            
            if result_dict is None or "State" not in result_dict:
                purcl_logger_adapter.error(f"IrrelevantValidator: Failed to get response or extract State tag from model")
                return State.ABORT, ""
                
            result = result_dict["State"]
            reasoning = result_dict.get("Reasoning", "")
            purcl_logger_adapter.debug(f"IrrelevantValidator reasoning: {reasoning}")
            
            if result == State.IRRELEVANT.value:
                return State.IRRELEVANT, reasoning
            else:
                return State.ANSWER_WITH_NO_CODE, reasoning
            
        except Exception as e:
            purcl_logger_adapter.error(f"Error in irrelevant validation: {e}")
            return State.ABORT, ""
    
    def _validate_reasoning_trace_state(self, prompt: str, response: str, goal: Optional[str], previous_state: State) -> tuple[State, str]:
        """
        Validate if the reasoning trace is valid.
        
        Args:
            prompt: The prompt that was sent
            response: The model's response
            goal: Optional goal for the conversation
            previous_state: The previous state
            
        Returns:
            State indicating if reasoning trace is valid or not
        """
        try:
            # Use the predefined trace validator system prompt
            system_prompt = TRACE_VALIDATOR_SYSTEM_PROMPT.format(
                seed_prompt=prompt,
                trace=response,
                goal=goal or "Not specified",
                valid_reasoning_trace=State.VALID_REASONING_TRACE.value,
                invalid_reasoning_trace=State.INVALID_REASONING_TRACE.value,
                refusal=State.REFUSAL.value
            )
            
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            result_dict = query_model(
                model_client=self.model_client,
                model_name_or_path=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                messages=messages,
                tag_names=["State", "Reasoning"]
            )
            
            if result_dict is None or "State" not in result_dict:
                purcl_logger_adapter.error(f"TraceValidator: Failed to get response or extract State tag from model")
                return State.ABORT, ""
                
            result = result_dict["State"]
            reasoning = result_dict.get("Reasoning", "")
            purcl_logger_adapter.debug(f"TraceValidator reasoning: {reasoning}")
            
            if result == State.VALID_REASONING_TRACE.value:
                return State.VALID_REASONING_TRACE, reasoning
            elif result == State.INVALID_REASONING_TRACE.value:
                return State.INVALID_REASONING_TRACE, reasoning
            elif result == State.REFUSAL.value:
                return State.REFUSAL, reasoning
            else:
                return State.INVALID_REASONING_TRACE, reasoning
            
        except Exception as e:
            purcl_logger_adapter.error(f"Error in reasoning trace validation: {e}")
            return State.INVALID_REASONING_TRACE, ""
    
    def get_state_description(self, state: State) -> str:
        """
        Get a human-readable description of a state.
        
        Args:
            state: The state to describe
            
        Returns:
            Description of the state
        """
        descriptions = {
            State.START: "Conversation has started",
            State.IRRELEVANT: "Model response is irrelevant to the goal",
            State.REFUSAL: "Model refused with a template response",
            State.VALID_REASONING_TRACE: "Model provided valid reasoning trace",
            State.INVALID_REASONING_TRACE: "Model provided invalid reasoning trace",
            State.ANSWER_WITH_NO_CODE: "Model answered but didn't provide code",
            State.ANSWER_WITH_CODE_WITHOUT_GOAL: "Model provided code but it doesn't achieve the goal",
            State.JAILBROKEN: "Model has been jailbroken and achieved the goal",
            State.ABORT: "Conversation has been aborted"
        }
        
        return descriptions.get(state, f"Unknown state: {state.value}")