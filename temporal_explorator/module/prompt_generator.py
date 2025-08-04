from typing import List, Dict
from state import State
from action import Action
from system_prompt import ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT
from utils.chat_utils import chat_with_model
from openai import OpenAI


def generate_prompt(
    session_data_dict: List[Dict[str, str]], 
    config: Dict[str, str],
    action: Action,
    ) -> str:

    mutator_factory = MutatorFactory(
        model_client=OpenAI(base_url=config.get('mutator_model_url'), api_key=config.get('mutator_model_api_key')),
        model_name_or_path=config.get('mutator_model_name_or_path'),
        temperature=config.get('mutator_model_temperature'),
        max_tokens=config.get('mutator_model_max_tokens'),
        max_retries=config.get('mutator_model_max_retries')
    )

    mutator = mutator_factory.get_mutator(action)
    prompt = mutator.mutate(session_data_dict, action)

    return prompt

    
    
    

class PromptGenerator:
    def __init__(self, config: Dict[str, str]):
        self.model_client = OpenAI(base_url=config.get('prompt_generator_model_url'), api_key=config.get('prompt_generator_model_api_key'))
        self.model_name_or_path = config.get('prompt_generator_model_name_or_path')
        self.temperature = config.get('prompt_generator_model_temperature')
        self.max_tokens = config.get('prompt_generator_model_max_tokens')
        self.max_retries = config.get('prompt_generator_model_max_retries')

        self.mutator_factory = MutatorFactory(
            model_client=self.model_client,
            model_name_or_path=self.model_name_or_path,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            max_retries=self.max_retries
        )

    def generate(self, state: State, action: Action, seed_prompt: str, chat_history: List[Dict[str, str]]) -> str:

        mutator = self.mutator_factory.get_mutator(action)
        prompt = mutator.mutate(seed_prompt, goal, chat_history, action, state)

        return prompt
        
        
        
        if state in [State.IRRELEVANT, State.REFUSAL, State.ANSWER_WITH_CODE_WITHOUT_GOAL]:
            # call tool to generate reasoning trace 
            '''
            current_prompt = chat_history[-1]["prompt"]
            current_response = chat_history[-1]["response"]
            current_goal = chat_history[-1]["goal"]
            ask_for_reasoning_trace_prompt = ASK_FOR_REASONING_TRACE_SYSTEM_PROMPT.format(user_request=current_prompt, model_response=current_response, goal=current_goal, state=state)
            messages = [
                {"role": "user", "content": ask_for_reasoning_trace_prompt},
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
                print(f"PromptGenerator: Failed to get response from model")
                return None
            prompt = extract_tag(response, "Prompt")
            if prompt is None:
                print(f"PromptGenerator: Failed to get prompt from model")
                return None
            '''

        elif state == State.VALID_REASONING_TRACE:
            if action == Action.PERSUASION:

                
            elif action == Action.FACTUAL_INSTANTIATION:
                #TODO generate intention obfuscation prompt, use some jailbreaks from the pool 
            elif action == Action.TASK_DECOMPOSITION:
                # generate task decomposition prompt
                pass
            else:
                raise ValueError(f"Invalid action: {action} for state: {state}")
        elif state == State.INVALID_REASONING_TRACE:
            # generate remove irrelevant factor prompt

        elif state == State.ANSWER_WITH_NO_CODE:
            # generate ask for code prompt
        else:
            raise ValueError(f"Invalid state: {state}")
        
        
        return prompt