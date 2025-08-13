from typing import List
import yaml
import openai
import boto3
from botocore.config import Config
from semantic_kernel.connectors.ai.bedrock import BedrockChatCompletion
from autogen_ext.models.semantic_kernel import SKChatCompletionAdapter
from semantic_kernel import Kernel
from semantic_kernel.memory.null_memory import NullMemory
import nltk

# from nltk.translate.bleu_score import sentence_bleu, corpus_bleu
from transformers import AutoTokenizer
from codebleu import calc_codebleu
from semantic_kernel.connectors.ai.bedrock import BedrockChatPromptExecutionSettings
import sacrebleu
from collections import Counter
from nltk.util import ngrams
from sacrebleu.tokenizers import tokenizer_13a
from autogen_core.models import UserMessage, AssistantMessage, LLMMessage
import tree_sitter as ts
import tree_sitter_python as ts_py


py_lang = ts.Language(ts_py.language())
py_parser = ts.Parser(py_lang)


llama3_tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-1B")

# nltk.download('stopwords')
english_stopwords = set(nltk.corpus.stopwords.words("english"))


def _get_ngram_counts(tokens, n):
    return Counter(ngrams(tokens, n))


def _get_overlapped_n_gram(ref_tokens, hyp_tokens, n):
    # Compute 1-gram counts for candidate and reference
    cand_ngram_counts = _get_ngram_counts(ref_tokens, n)
    ref_ngram_counts = _get_ngram_counts(hyp_tokens, n)
    overlappen_n = cand_ngram_counts & ref_ngram_counts
    overlapped_sorted = sorted(overlappen_n.items(), key=lambda x: x[1], reverse=True)
    return overlapped_sorted


def get_rep_wording_hints(ref_text, hyp_text):
    tokenizer = tokenizer_13a.Tokenizer13a()
    ref_text_lower = ref_text.lower()
    hyp_text_lower = hyp_text.lower()
    ref_tokens = tokenizer(ref_text_lower).split()
    hyp_tokens = tokenizer(hyp_text_lower).split()
    overlapped_1 = _get_overlapped_n_gram(ref_tokens, hyp_tokens, 1)
    overlapped_2 = _get_overlapped_n_gram(ref_tokens, hyp_tokens, 2)
    overlapped_3 = _get_overlapped_n_gram(ref_tokens, hyp_tokens, 3)
    overlapped_4 = _get_overlapped_n_gram(ref_tokens, hyp_tokens, 4)
    non_stop_overlapped_1 = [
        token[0]
        for token, count in overlapped_1
        if token[0] not in english_stopwords and all([c.isalpha() for c in token[0]])
    ]
    non_stop_overlapped_2 = [" ".join(tokens) for tokens, count in overlapped_2]
    non_stop_overlapped_3 = [" ".join(tokens) for tokens, count in overlapped_3]
    non_stop_overlapped_4 = [" ".join(tokens) for tokens, count in overlapped_4]
    return (
        non_stop_overlapped_1,
        non_stop_overlapped_2,
        non_stop_overlapped_3,
        non_stop_overlapped_4,
    )


def calculate_bleu_score(ref, hypo):
    return (
        sacrebleu.sentence_bleu(hypothesis=hypo, references=[ref], lowercase=True).score
        / 100
    )
    # tokens0 = llama3_tokenizer.tokenize(text0)
    # tokens1 = llama3_tokenizer.tokenize(text1)
    # return sentence_bleu([tokens0], tokens1)


def calculate_code_bleu(code0, code1):
    codeblue_score_all = calc_codebleu(
        references=[code0], predictions=[code1], lang="python"
    )
    codebleu_score = codeblue_score_all["codebleu"]
    return codebleu_score


# the_config = yaml.safe_load(open("cls_example_syn/config.yaml"))


def load_model_from_config(model_config):
    real_model_name = model_config["vllm_name"]
    api_key = model_config["api_key"]
    api_addresses = model_config["api_address"]
    clients = [openai.OpenAI(base_url=addr, api_key=api_key) for addr in api_addresses]
    return real_model_name, clients


def try_extract_code_block(rsp_txt):
    # find the last ```python
    last_start = rsp_txt.rfind("```python")
    if last_start == -1:
        return None
    remaining = rsp_txt[last_start + len("```python") :]
    if "```" not in remaining:
        return remaining
    return remaining[: remaining.find("```")]


def _get_claude_sk_client(model_name):
    config = Config(read_timeout=120, retries={"max_attempts": 10, "mode": "standard"})
    br_client = boto3.client("bedrock-runtime", region_name="us-east-1", config=config)
    # arn = "arn:aws:bedrock:us-west-2:897729136583:inference-profile/us.anthropic.claude-3-5-haiku-20241022-v1:0"
    if model_name is None:
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    else:
        model_id = model_name
    sk_client = BedrockChatCompletion(runtime_client=br_client, model_id=model_id)
    return sk_client


def get_claude_completion_adapter(model_name=None):
    kernel = Kernel(memory=NullMemory())
    sk_client = _get_claude_sk_client(model_name=model_name)
    return SKChatCompletionAdapter(sk_client=sk_client, kernel=kernel)


def get_creative_completion_setting():
    return BedrockChatPromptExecutionSettings(
        temperature=0.8,
        top_k=50,
    )


def _parse_tag(text, tag):
    opening = f"<{tag}>"
    closing = f"</{tag}>"
    start = text.find(opening)
    if start == -1:
        return None
    end = text.find(closing)
    if end == -1:
        return None
    return text[start + len(opening) : end]


def parse_tags(text, tags):
    missing_tags = ""
    ret_entries = {}
    for tag in tags:
        ret = _parse_tag(text, tag)
        if ret is None:
            missing_tags += f"{tag}, "
        else:
            ret_entries[tag] = ret
    return {"missing_tags": missing_tags, **ret_entries}


async def get_response_with_retry(
    prompt: str,
    source_name: str,
    expected_tags: List[str],
    llm_client,
    gen_config,
    retry=3,
):
    messages = [UserMessage(content=prompt, source=source_name)]
    rsp = await llm_client.create(
        messages, extra_create_args={"prompt_execution_settings": gen_config}
    )
    while retry > 0:
        rsp_txt = rsp.content
        messages += [AssistantMessage(content=rsp_txt, source="Assistant")]
        extracted = parse_tags(rsp_txt, expected_tags)
        if len(extracted["missing_tags"]) > 0:
            retry -= 1
            err_msg = """
            "I cannot find the following tags in your response: {missing_tags}.
Please make sure you include all the tags (including openning and closing tags) in your response.
Revise your response and try again. (Please include all tags in the revised response, not just the missing ones.)
""".format(
                missing_tags=extracted["missing_tags"]
            )
            messages += [UserMessage(content=err_msg, source=source_name)]
            rsp = await llm_client.create(
                messages,
                extra_create_args={"prompt_execution_settings": gen_config},
            )
        else:
            return {"succ": True, "raw_rsp": rsp_txt, **extracted}

    return {"succ": False, "raw_rsp": rsp_txt, **extracted}


# dbg = {'modelId': 'anthropic.claude-3-haiku-20240307-v1:0', 'messages': [{'role': 'user', 'content': [{'text': 'What is the capital of France?'}]}], 'system': [{'text': 'You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.'}], 'inferenceConfig': {'stopSequences': []}, 'additionalModelRequestFields': None}

# from semantic_kernel.connectors.ai.bedrock.services.model_provider.utils import run_in_executor
# from functools import partial

# asyncio.run(run_in_executor(None, partial(br_client.converse, **dbg)))


def remove_py_comments(code):
    root_node = py_parser.parse(bytes(code, "utf8")).root_node

    # Function to collect all comment nodes
    def collect_comment_nodes(node, comment_nodes):
        if node.type == "comment":
            comment_nodes.append(node)
        for child in node.children:
            collect_comment_nodes(child, comment_nodes)

    comment_nodes = []
    collect_comment_nodes(root_node, comment_nodes)

    query_str = """
    (module
        (expression_statement (string) @docstring))

    (class_definition
        body: (block (expression_statement (string) @docstring)))

    (function_definition
        body: (block (expression_statement (string) @docstring)))
    """
    query = py_lang.query(query_str)
    captures = query.captures(root_node)
    for capture in captures:
        comment_nodes.append(capture[0])

    sorted_comment_nodes = sorted(comment_nodes, key=lambda x: x.start_byte)

    new_code = ""
    prev_end_byte = 0
    # Remove comments
    for comment_node in sorted_comment_nodes:
        start_byte = comment_node.start_byte
        new_code += code[prev_end_byte:start_byte]
        prev_end_byte = comment_node.end_byte

    new_code += code[prev_end_byte:]


    return new_code
