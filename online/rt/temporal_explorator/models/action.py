from enum import Enum

class Action(Enum):
    SEND_SEED_PROMPT = "SendSeedPrompt"
    ASK_FOR_REASONING_TRACE = "AskForReasoningTrace"
    ASK_FOR_CODE = "AskForCode"
    REMOVE_IRRELEVANT_FACTOR = "RemoveIrrelevantFactor"
    PERSUASION = "Persuasion"
