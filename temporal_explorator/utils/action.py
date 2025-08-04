from enum import Enum

class Action(Enum):
    SEND_SEED_PROMPT = "SendSeedPrompt"
    ASK_FOR_REASONING_TRACE = "AskForReasoningTrace"
    PERSUASION = "Persuasion"
    INTENTION_OBFUSCATION = "IntentionObfuscation"
    TASK_DECOMPOSITION = "TaskDecomposition"
    REMOVE_IRRELEVANT_FACTOR = "RemoveIrrelevantFactor"
    ASK_FOR_CODE = "AskForCode"
    ABORT_PLACEHOLDER = "AbortPlaceholder"
