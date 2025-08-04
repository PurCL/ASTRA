from openai import OpenAI
from typing import List, Dict
from action import Action
from system_prompt import (
    ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT, 
    ASK_FOR_CODE_SYSTEM_PROMPT,
)
from utils.chat_utils import chat_with_model, extract_tag

# TODO: move tag_extraction in the retry loop
class Mutator:
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        self.model_client = model_client
        self.model_name_or_path = model_name_or_path
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        self.memory = []

    def mutate(
        self, 
        session_data_dict: List[Dict[str, str]],
        action: Action
    ) -> str:
        pass


class PersuasionMutator(Mutator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)
        self.system_prompt = PERSUASION_SYSTEM_PROMPT

    def mutate(
        self, 
        session_data_dict: List[Dict[str, str]],
        action: Action
    ) -> str:
        goal = session_data_dict[0]["goal"]
        seed_prompt = session_data_dict[0]["prompt"]
        previous_response = session_data_dict[-1]["response"]

        query = self.system_prompt.format(
            seed_prompt=seed_prompt,
            previous_response=previous_response,
            goal=goal,
        )

        messages = [
            {"role": "user", "content": query},
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
            print(f"PersuasionMutator: Failed to get response from model")
            return None
        prompt = extract_tag(response, "Prompt")
        if prompt is None:
            print(f"PersuasionMutator: Failed to get prompt from model")
            return None

        return prompt


# class FactualInstantiationMutator(Mutator):
#     def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
#         super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)

#     def mutate(
#         self, 
#         session_data_dict: List[Dict[str, str]],
#         action: Action
#     ) -> str:
#         pass


# class TaskDecompositionMutator(Mutator):
#     def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
#         super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)

#     def mutate(
#         self, 
#         session_data_dict: List[Dict[str, str]],
#         action: Action
#     ) -> str:
#         pass

class RemoveIrrelevantFactorMutator(Mutator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)
        self.system_prompt = REMOVE_IRRELEVANT_FACTOR_SYSTEM_PROMPT

    def mutate(
        self, 
        session_data_dict: List[Dict[str, str]],
        action: Action
    ) -> str:
        goal = session_data_dict[0]["goal"]
        seed_prompt = session_data_dict[0]["prompt"]
        previous_response = session_data_dict[-1]["response"]
        previous_state = session_data_dict[-1]["state"]

        query = self.system_prompt.format(
            seed_prompt=seed_prompt,
            invalid_trace=previous_response,
            goal=goal,
        )
        messages = [
            {"role": "user", "content": query},
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
            print(f"RemoveIrrelevantFactorMutator: Failed to get response from model")
            return None
        prompt = extract_tag(response, "Prompt")
        if prompt is None:
            print(f"RemoveIrrelevantFactorMutator: Failed to get prompt from model")
            return None
        
        return prompt



class AskForReasoningTraceMutator(Mutator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)
        self.system_prompt = ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT

    def mutate(
        self, 
        session_data_dict: List[Dict[str, str]],
        action: Action
    ) -> str:
        goal = session_data_dict[0]["goal"]
        previous_prompt = session_data_dict[-1]["prompt"]
        previous_response = session_data_dict[-1]["response"]
        previous_state = session_data_dict[-1]["state"]

        query = self.system_prompt.format(
            user_request=previous_prompt,
            model_response=previous_response,
            goal=goal,
            state=previous_state,
        )
        messages = [
            {"role": "user", "content": query},
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
            print(f"AskForReasoningTraceMutator: Failed to get response from model")
            return None
        prompt = extract_tag(response, "Prompt")
        if prompt is None:
            print(f"AskForReasoningTraceMutator: Failed to get prompt from model")
            return None
        
        return prompt
        


class AskForCodeMutator(Mutator):
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        super().__init__(model_client, model_name_or_path, temperature, max_tokens, max_retries)
        self.system_prompt = ASK_FOR_CODE_SYSTEM_PROMPT

    def mutate(
        self, 
        session_data_dict: List[Dict[str, str]],
        action: Action
    ) -> str:
        
        goal = session_data_dict[0]["goal"]
        previous_prompt = session_data_dict[-1]["prompt"]
        previous_response = session_data_dict[-1]["response"]

        query = self.system_prompt.format(
            user_request=previous_prompt,
            model_response=previous_response,
            goal=goal,
        )
        messages = [
            {"role": "user", "content": query},
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
            print(f"AskForCodeMutator: Failed to get response from model")
            return None
        prompt = extract_tag(response, "Prompt")
        if prompt is None:
            print(f"AskForCodeMutator: Failed to get prompt from model")
            return None

        return prompt
    
        

class MutatorFactory:
    def __init__(self, model_client: OpenAI, model_name_or_path: str, temperature: float, max_tokens: int, max_retries: int):
        self.model_client = model_client
        self.model_name_or_path = model_name_or_path
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def get_mutator(self, action: Action) -> Mutator:
        if action == Action.PERSUASION:
            return PersuasionMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        elif action == Action.FACTUAL_INSTANTIATION:
            return FactualInstantiationMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        elif action == Action.TASK_DECOMPOSITION:
            return TaskDecompositionMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        elif action == Action.REMOVE_IRRELEVANT_FACTOR:
            return RemoveIrrelevantFactorMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        elif action == Action.ASK_FOR_REASONING_TRACE:
            return AskForReasoningTraceMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        elif action == Action.ASK_FOR_CODE:
            return AskForCodeMutator(self.model_client, self.model_name_or_path, self.temperature, self.max_tokens, self.max_retries)
        else:
            raise ValueError(f"Invalid action: {action}")