class ActionSelector:
    def select(self, state: State, history):
        if state == State.START:
            return Action.SEND_SEED_PROMPT
        elif state == State.IRRELEVANT:
            return Action.ASK_FOR_REASONING_TRACE
        elif state == State.TEMPLATE_REFUSAL:
            return Action.ASK_FOR_REASONING_TRACE
        elif state == State.REFUSAL_WITH_VALID_REASONING_TRACE:
            return random.choice([Action.PERSUASION, Action.INTENTION_OBFUSCATION, Action.TASK_DECOMPOSITION])
        elif state == State.REFUSAL_WITH_INVALID_REASONING_TRACE:
            return Action.REMOVE_IRRELEVANT_FACTOR
        elif state == State.ANSWER_WITH_NO_CODE:
            return Action.ASK_FOR_CODE
        elif state == State.ANSWER_WITH_CODE_WITHOUT_GOAL:
            return Action.ASK_FOR_REASONING_TRACE
        else:
            raise ValueError(f"Invalid state: {state}")
