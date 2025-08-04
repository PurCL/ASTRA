from module.state import State, Action

class ActionSelector:
    def select(self, state: State):
        if state == State.START:
            return Action.SEND_SEED_PROMPT
        elif state == State.IRRELEVANT or state == State.REFUSAL or state == State.ANSWER_WITH_CODE_WITHOUT_GOAL:
            return Action.ASK_FOR_REASONING_TRACE
        elif state == State.VALID_REASONING_TRACE:
            # return random.choice([Action.PERSUASION, Action.INTENTION_OBFUSCATION, Action.TASK_DECOMPOSITION])
            return Action.PERSUASION
        elif state == State.INVALID_REASONING_TRACE:
            return Action.REMOVE_IRRELEVANT_FACTOR
        elif state == State.ANSWER_WITH_NO_CODE:
            return Action.ASK_FOR_CODE
        else:
            raise ValueError(f"Invalid state: {state}")

