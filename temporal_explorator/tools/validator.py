from openai import OpenAI 
from typing import List, Dict
from tools.system_prompt import JAILBROKEN_VALIDATOR_SYSTEM_PROMPT, REFUSAL_SYSTEM_PROMPT, IRRELEVANT_SYSTEM_PROMPT, TRACE_VALIDATOR_SYSTEM_PROMPT
from utils.state import State
from utils.chat_utils import chat_with_model, extract_tag

class Validator:
    def __init__(
        self, 
        model_client: OpenAI, 
        model_name_or_path: str, 
        temperature: float, 
        max_tokens: int, 
        max_retries: int
    ):
        self.model_client = model_client
        self.model_name_or_path = model_name_or_path
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
    
    
    def validate(
        self, 
        user_request: str, 
        model_response: str, 
        goal: str,
    ) -> State:
        pass 


class JailbrokenValidator(Validator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)
    
    def validate(self, user_request: str, model_response: str, goal: str):
        system_prompt = JAILBROKEN_JUDGE_SYSTEM_PROMPT.format(user_request=user_request, model_response=model_response, goal=goal, jailbroken_state=State.JAILBROKEN.value)
        messages = [
            {"role": "user", "content": system_prompt},
        ]
        response = chat_with_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name_or_path,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages
        )
        if response is None:
            print(f"JailbrokenJudge: Failed to get response from model")
            return State.ABORT
        # parse state from the response 
        state = extract_tag(response, "State")
        if state == State.JAILBROKEN.value:
            return State.JAILBROKEN
        else:
            system_prompt = REFUSAL_SYSTEM_PROMPT.format(user_request=user_request, model_response=model_response, goal=goal, refusal=State.REFUSAL.value, valid_reasoning_trace=State.VALID_REASONING_TRACE.value, invalid_reasoning_trace=State.INVALID_REASONING_TRACE.value, no_refusal=State.NO_REFUSAL.value)
            messages = [
                {"role": "user", "content": system_prompt},
            ]
            response = chat_with_model(
                model_client=self.model_client,
                model_name_or_path=self.model_name_or_path,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                max_retries=self.max_retries,
                messages=messages
            )
            if response is None:
                print(f"JailbrokenJudge: Failed to get response from model")
                return State.ABORT
            state = extract_tag(response, "State")
            if state == State.REFUSAL.value:
                return State.REFUSAL
            elif state == State.VALID_REASONING_TRACE.value:
                return State.VALID_REASONING_TRACE
            elif state == State.INVALID_REASONING_TRACE.value:
                return State.INVALID_REASONING_TRACE
            else:
                if "```python" in model_response:
                    return State.ANSWER_WITH_CODE_WITHOUT_GOAL
                else:
                    system_prompt = IRRELEVANT_SYSTEM_PROMPT.format(user_request=user_request, model_response=model_response, goal=goal, irrelevant=State.IRRELEVANT.value, answer_with_no_code=State.ANSWER_WITH_NO_CODE.value)
                    messages = [
                        {"role": "user", "content": system_prompt},
                    ]
                    response = chat_with_model(
                        model_client=self.model_client,
                        model_name_or_path=self.model_name_or_path,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        max_retries=self.max_retries,
                        messages=messages
                    )
                    if response is None:
                        print(f"JailbrokenJudge: Failed to get response from model")
                        return State.ABORT
                    state = extract_tag(response, "State")
                    if state == State.IRRELEVANT.value:
                        return State.IRRELEVANT
                    else:
                        return State.ANSWER_WITH_NO_CODE


class TraceValidator(Validator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)

    def validate(
        self,
        user_request: str,
        model_response: str,
        goal: str,
        state: State
    ) -> State:
        
        system_prompt = TRACE_VALIDATOR_SYSTEM_PROMPT.format(seed_prompt=user_request, trace=model_response, goal=goal, valid_reasoning_trace=State.VALID_REASONING_TRACE.value, invalid_reasoning_trace=State.INVALID_REASONING_TRACE.value, refusal=State.REFUSAL.value)
        messages = [
            {"role": "user", "content": system_prompt},
        ]
        response = chat_with_model(
            model_client=self.model_client,
            model_name_or_path=self.model_name_or_path,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries,
            messages=messages)
        if response is None:
            print(f"TraceValidator: Failed to get response from model")
            return State.ABORT
        state = extract_tag(response, "State")
        if state == State.VALID_REASONING_TRACE.value:
            return State.VALID_REASONING_TRACE
        elif state == State.INVALID_REASONING_TRACE.value:
            return State.INVALID_REASONING_TRACE
        elif state == State.REFUSAL.value:
            return State.REFUSAL
        else:
            raise ValueError(f"Invalid state: {state}")
        