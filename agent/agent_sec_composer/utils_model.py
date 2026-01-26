from agents.extensions.models.litellm_model import LitellmModel
from openai.types.responses import ResponseOutputMessage
import yaml
from agents.model_settings import ModelSettings
from agents.models.interface import ModelTracing


def _get_model_sonnet_4_5():
    # Claude 4 model IDs on Bedrock (example: Sonnet 4)
    # See AWS announcement for these IDs. :contentReference[oaicite:3]{index=3}
    model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"

    # Force the Bedrock Converse route (best for tool use).
    # LiteLLM supports explicit bedrock/converse/<model> routing. :contentReference[oaicite:4]{index=4}
    model = LitellmModel(model=f"bedrock/converse/{model_id}")
    return model


def _get_model_haiku_4_5():
    model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    model = LitellmModel(model=f"bedrock/converse/{model_id}")
    return model


def _get_model_gpt_oss_20b():
    model_id = "openai.gpt-oss-20b-1:0"
    model = LitellmModel(model=f"bedrock/converse/{model_id}")
    return model

def _get_model_gpt_oss_120b():
    model_id = "openai.gpt-oss-120b-1:0"
    model = LitellmModel(model=f"bedrock/converse/{model_id}")
    return model

def _get_model_sonnet_3_7():
    model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    model = LitellmModel(model=f"bedrock/converse/{model_id}")
    return model

config = yaml.safe_load(open("resources/client-config.yaml"))


def _get_model_local(model_short_name: str):
    model_config = config[model_short_name]
    model_name = model_config["model_name"]
    addr = model_config["addr"]
    api_key = model_config["api_key"]
    model = LitellmModel(
        model=f"hosted_vllm/{model_name}",
        base_url=addr,
        api_key=api_key,
    )
    return model


def get_model(model_name: str):
    if 'sonnet-4-5' in model_name:
        return _get_model_sonnet_4_5()
    elif 'haiku-4-5' in model_name:
        return _get_model_haiku_4_5()
    elif 'sonnet-3-7' in model_name:
        return _get_model_sonnet_3_7()
    elif 'gpt-oss-20b' in model_name:
        return _get_model_gpt_oss_20b()
    elif 'gpt-oss-120b' in model_name:
        return _get_model_gpt_oss_120b()
    else:
        return _get_model_local(model_name)


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
