
import random
from enum import Enum

# STATE DEFINITION
# Start => SendSeedPrompt
# Irrelevant => AskForReasoningTrace
# TemplateRefusal => AskForReasoningTrace
# RefusalWithCorrectReasoningTrace => [Persuasion, IntentionObfuscation, TaskDecomposition]
# RefusalWithIncorrectReasoningTrace => [RemoveIrrelevantFactor]
# AnswerWithNoCode => AskForCode
# AnswerWithCodeWithoutGoal => AskForReasoningTrace
# Jailbroken => Exit


class State(Enum):
    START = "Start"
    IRRELEVANT = "Irrelevant"
    TEMPLATE_REFUSAL = "TemplateRefusal"
    REFUSAL_WITH_VALID_REASONING_TRACE = "RefusalWithValidReasoningTrace"
    REFUSAL_WITH_INVALID_REASONING_TRACE = "RefusalWithInvalidReasoningTrace"
    ANSWER_WITH_NO_CODE = "AnswerWithNoCode"
    ANSWER_WITH_CODE_WITHOUT_GOAL = "AnswerWithCodeWithoutGoal"
    JAILBROKEN = "Jailbroken"

class Action(Enum):
    SEND_SEED_PROMPT = "SendSeedPrompt"
    ASK_FOR_REASONING_TRACE = "AskForReasoningTrace"
    PERSUASION = "Persuasion"
    INTENTION_OBFUSCATION = "IntentionObfuscation"
    TASK_DECOMPOSITION = "TaskDecomposition"
    REMOVE_IRRELEVANT_FACTOR = "RemoveIrrelevantFactor"
    ASK_FOR_CODE = "AskForCode"


class TemporalExplorator:
    def __init__(self, bt_model, state_mapper, action_selector, prompt_generator, config=None):
        self.bt_model = bt_model
        self.state_mapper = state_mapper
        self.action_selector = action_selector
        self.prompt_generator = prompt_generator
        self.config = config or {'max_turn': 10}
        self.state = State.START
        self.history = []
        self.chat_history = []

    def explore(self, seed_prompt: str):
        current_state = State.START
        for turn_id in range(self.config['max_turn']):
            action = self.action_selector.select(current_state)
            prompt = self.prompt_generator.generate(current_state, action)
            raw_response = self.get_bt_response(prompt)
            state = self.state_mapper.map(current_state, action, prompt, raw_response, goal)
            current_state = state
            if current_state == State.JAILBROKEN:
                break
