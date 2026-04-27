from agents.extensions.models.litellm_model import LitellmModel
from openai.types.responses import ResponseOutputMessage
import yaml
from agents.model_settings import ModelSettings
from agents.models.interface import ModelTracing


# Load configurations
config = yaml.safe_load(open("resources/client-config.yaml"))
agent_sec_config = yaml.safe_load(open("resources/agent-sec-config.yaml"))


def _get_bedrock_model(model_config: dict) -> LitellmModel:
    """
    Create a Bedrock model instance.
    Uses the bedrock/converse/<model_id> routing for best tool use support.
    """
    model_id = model_config["model_name"]
    return LitellmModel(model=f"bedrock/converse/{model_id}")


def _get_openai_compatible_model(model_config: dict) -> LitellmModel:
    """
    Create an OpenAI-compatible model instance (vLLM, SGLang, etc.).
    """
    model_name = model_config["model_name"]
    addr = model_config["addr"]
    api_key = model_config["api_key"]
    return LitellmModel(
        model=f"hosted_vllm/{model_name}",
        base_url=addr,
        api_key=api_key,
    )


def get_model(model_name: str) -> LitellmModel:
    """
    Get a model instance by name with provider-based routing.

    The model name should be defined in resources/client-config.yaml.
    Each model config must have a 'provider' field:
    - "bedrock": Routes to AWS Bedrock Converse API
    - "openai": Routes to OpenAI-compatible server (vLLM, SGLang, etc.)

    Args:
        model_name: Short name of the model (e.g., "claude-sonnet-4-5", "qwen3coder")

    Returns:
        LitellmModel instance configured for the appropriate backend

    Raises:
        KeyError: If model_name is not found in client-config.yaml
        ValueError: If provider field is missing or unsupported
    """
    if model_name not in config:
        raise KeyError(
            f"Model '{model_name}' not found in resources/client-config.yaml. "
            f"Available models: {list(config.keys())}"
        )

    model_config = config[model_name]

    # Check for provider field
    if "provider" not in model_config:
        raise ValueError(
            f"Model '{model_name}' is missing 'provider' field in client-config.yaml. "
            f"Must be either 'bedrock' or 'openai'"
        )

    provider = model_config["provider"]

    # Route based on provider
    if provider == "bedrock":
        return _get_bedrock_model(model_config)
    elif provider == "openai":
        return _get_openai_compatible_model(model_config)
    else:
        raise ValueError(
            f"Unsupported provider '{provider}' for model '{model_name}'. "
            f"Must be either 'bedrock' or 'openai'"
        )


async def get_response_text(model, input_items,
                      *, system_prompt: str = None, temperature: float = 0.7, max_tokens: int = 2048):
    resp = await model.get_response(
        system_instructions=system_prompt,
        input=input_items,
        model_settings=ModelSettings(
            temperature=temperature,
            max_tokens=max_tokens,
        ),
        tools=[],
        output_schema=None,
        handoffs=[],
        tracing=ModelTracing.DISABLED,
        previous_response_id=None,
        conversation_id=None,
    )
    texts = []
    for item in resp.output:
        if type(item) == ResponseOutputMessage:
            texts += [t.text for t in item.content]
    return "\n".join(texts)
