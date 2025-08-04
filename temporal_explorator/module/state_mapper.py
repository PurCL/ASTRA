from typing import Dict, List
from state import State
from action import Action
from openai import OpenAI

class StateMapper:
    def __init__(self, config: Dict[str, str]):
        pass 
    
    def map(self, session_data_obj: SessionDataObj) -> State:
        previous_state = session_data_obj.previous_state
        current_action = session_data_obj.current_action
        current_prompt = session_data_obj.current_prompt
        current_response = session_data_obj.current_response
        goal = session_data_obj.goal
        seed_prompt = session_data_obj.seed_prompt

        if current_action in [Action.SEND_SEED_PROMPT, Action.PERSUASION, Action.INTENTION_OBFUSCATION, Action.TASK_DECOMPOSITION, Action.REMOVE_IRRELEVANT_FACTOR, Action.ASK_FOR_CODE]:
            jailbroken_validator = JailbrokenValidator(
                self.tool_model_client,
                self.tool_model_name_or_path,
                self.tool_model_temperature,
                self.tool_model_max_tokens,
                self.tool_model_max_retries
            )
            state = jailbroken_validator.validate(
                user_request=current_prompt,
                model_response=current_response,
                goal=goal,
            )
        elif current_action == Action.ASK_FOR_REASONING_TRACE:
            trace_validator = TraceValidator(
                self.tool_model_client,
                self.tool_model_name_or_path,
                self.tool_model_temperature,
                self.tool_model_max_tokens,
                self.tool_model_max_retries
            )
            state = trace_validator.validate(
                user_request=seed_prompt,
                model_response=current_response,
                goal=goal,
                state=previous_state,
            )
        # elif current_action == Action.SEND_UTILITY_PROMPT:
        #     utility_validator = UtilityValidator(
        #         self.tool_model_client,
        #         self.tool_model_name_or_path,
        #         self.tool_model_temperature,
        #         self.tool_model_max_tokens,
        #         self.tool_model_max_retries
        #     )
        #     state = utility_validator.validate(
        #         user_request=current_prompt,
        #         model_response=current_response,
        #         goal=goal,
        #     )
        else:
            raise ValueError(f"Invalid action: {current_action}")
            state = State.ABORT
        
        return state