

class PromptGenerator:
    def generate(self, state: State, action: Action, chat_history: List[Dict[str, str]]) -> str:
        if state == State.START:
            return chat_history[0]['prompt']
        elif state == State.IRRELEVANT or state == State.TEMPLATE_REFUSAL or state == State.ANSWER_WITH_CODE_WITHOUT_GOAL:
            # call tool to generate reasoning trace
            pass 
        elif state == State.REFUSAL_WITH_VALID_REASONING_TRACE:
            if action == Action.PERSUASION:
                # generate persuasion prompt
            elif action == Action.INTENTION_OBFUSCATION:
                # generate intention obfuscation prompt
            elif action == Action.TASK_DECOMPOSITION:
                # generate task decomposition prompt
            else:
                raise ValueError(f"Invalid action: {action} for state: {state}")
        elif state == State.REFUSAL_WITH_INVALID_REASONING_TRACE:
            # generate remove irrelevant factor prompt
        elif state == State.ANSWER_WITH_NO_CODE:
            # generate ask for code prompt
        else:
            raise ValueError(f"Invalid state: {state}")
            
        