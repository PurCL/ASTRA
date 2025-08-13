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
    IRRELEVANT = "Irrelevant"
    REFUSAL = "Refusal"
    VALID_REASONING_TRACE = "ValidReasoningTrace"
    INVALID_REASONING_TRACE = "InvalidReasoningTrace"
    NO_REFUSAL = "NoRefusal"
    ANSWER_WITH_NO_CODE = "AnswerWithNoCode"
    ANSWER_WITH_CODE_WITHOUT_GOAL = "AnswerWithCodeWithoutGoal"
    JAILBROKEN = "Jailbroken"
    UNKNOWN = "Unknown"
    ABORT = "Abort"
