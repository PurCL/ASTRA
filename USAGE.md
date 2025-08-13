# ASTRA Usage Guide

ASTRA is a comprehensive red-teaming system that consists of three major components working together to perform autonomous vulnerability discovery and assessment of AI software assistants.

## 🧭 System Overview

ASTRA operates through a three-stage pipeline where each component feeds into the next to create a comprehensive red-teaming workflow:

1. **Domain Modeling** generates structured knowledge graphs from target domains, outputting hierarchical representations of vulnerabilities and attack vectors
2. **Prompt Generation** consumes these knowledge graphs to synthesize diverse jailbreaking prompts through multi-agent collaboration, producing contextually rich attack scenarios
3. **Online Exploration** takes the generated prompts as input and performs real-time adaptive probing against target AI systems, dynamically adjusting strategies based on system responses

Each stage builds upon the previous component's output, enabling systematic and comprehensive security evaluation of AI assistants.

## 🧩 Component 1: Offline Domain Modeling

**📁 Location**: `enumerator/`

This component takes a target domain as input and outputs a structured knowledge graph that captures domain-specific vulnerabilities and attack vectors.

### 🧩 Key Components:
- **Data Structure**: The knowledge graph structure is defined in `enumerator/tree_utils.py`, which provides the foundational tree-based representation for organizing domain knowledge hierarchically.
- **LLM-based Enumerator**: The core enumeration logic is implemented in `enumerator/enumerator.py`, which uses large language models to systematically generate comprehensive domain knowledge graphs.

### 📚 Domain Examples:
The repository includes pre-built knowledge graphs for two domains: **Secure Code Generation** and **Security Event Guidance**. Examples include `enumerator/enumerate_pl_feature.py` which enumerates programming language features, `enumerator/enumerate_context.py` for coding contexts, and `enumerator/enumerate_mal_tactics.py` for tactics as defined in [MITRE ATT&CK](https://attack.mitre.org/).

### 📝 Usage Notes:
- Knowledge graph enumeration is a one-time setup process per domain
- Pre-built knowledge graphs are provided in the `kg/` directory
- Users typically don't need to re-run the enumerator unless extending to new domains
- Interested developers can follow the existing examples to extend ASTRA to additional domains

## 🧪 Component 2: Offline Jailbreaking Prompt Generation

**📁 Location**: `agent/`

This component leverages the structured knowledge graphs to systematically generate diverse and sophisticated jailbreaking prompts through multi-agent collaboration.

In the previous stage, the input domain are decomposed into several orthonogonal dimensions, each represented as a hierarchical tree structure. The agent starts by sampling one leaf node from each dimension to form a multi-dimensional attack scenario. It then compose a concrete attack prompt based on the sampled scenario through multi-agent collaboration.

At a high level, the prompt generation process consists of the following steps:
1. A composer agent generates a draft prompt based on the sampled scenario.
2. The draft prompt is sent to a textual reviewer agent that ensure the generated prompt is benign, clear, and realistic.
3. A set of blue-team systems are used to evaluate the generated prompts. There are three blue-team systems:
   - A set of coder models that generate code snippets based on the generated prompts. A successful prompt should pass the built-in intention check of the coder model.
   - (For secure code generation) [Amazon CodeGuru](https://aws.amazon.com/codeguru/) static analyzer, which provides feedback on whether a generated code snippet is vulnerable or not. A successful prompt should induce a vulnerable code snippet.
   - (For security event guidance) A helpfulness checker that evaluates whether a target coder model completes the task as expected. A successful prompt should induce the target coder model to generate helpful responses for malicious purposes.
4. The sampling algorithm will consider the past generation process and identify the promising attributes that lead to successful prompts. It will then adjust the sampling strategy to target similar attributes in future generations, making the prompt generation process self-evolving.

### 🧩 Key Components:
- **Main Entry Points**: 
    - `main_sec_code.py`: Orchestrates prompt generation for secure code scenarios
    - `main_sec_event.py`: Handles security event-based prompt generation
- **Multi-Agent Architecture**:
    - `sec_code_composer/`: Contains agents specialized in composing code-related attack prompts
    - `sec_event_composer/`: Houses agents for security event scenario generation
    - `cgr_agent/`: Uses [Amazon CodeGuru](https://aws.amazon.com/codeguru/) static analyzer to provide feedback on whether a generated code snippet is vulnerable or not


### ▶️ Running Scripts:

The LLMs used for generating prompts and for local blue-teams are specified in the `resources/coder-config.yaml` file. Specifically, we use `qwen3-coder` as the composer and helpfulness checker, and `phi4m` as the coder model for generating code snippets.

The user needs to specify their own instances of those models in the `resources/coder-config.yaml` file. After that, use the following commands to generate attack prompts:
```bash
python3 agent/main_sec_code.py --fout <output_file-agent-code.jsonl> --log <path to log_file>
python3 agent/main_sec_event.py --fout <output_file-agent-sec.jsonl> --log <path to log_file>
```

Then use the following command to export the generated prompts to a format that can be used by the online exploration component:

```bash
## Use the following commands to export the prompts
python3 agent/export_syn_prompt.py --fin <path to the output_file-agent-code (or -sec).jsonl> --fout <output_file-exported.jsonl> 
```

## 🌐 Component 3: Online Adaptive Exploration and Violation Generation

**📁 Location**: `online/`

This component performs real-time adaptive red-teaming by dynamically probing target AI systems and adjusting attack strategies based on responses.
It takes as input a large pool of generated prompts and composes multi-round interactions with the target system to identify its unique vulnerabilities.
The adaptive exploration capabilities of the online system are two-fold:
1. **Spatial Exploration**: It samples prompts based on the past behavior of the target system, prioritizing promising attributes that are more likely to induce vulnerabilities.
2. **Temporal Exploration**: It reasons about the target system's responses over multiple turns, identifying weak links in its reasoning traces and dynamically adjusting prompts to exploit discovered vulnerabilities.

The online system leverages model-based judges to evaluate the target system's responses.
For secure code generation, it uses a judge model that mimic the behavior of the static analyzer, which evaluates whether a generated code snippet is vulnerable or not.
For security event guidance, it uses a judge model that evaluates whether the target system's response is indeed helpful for the intended malicious purposes.

### 🧩 Key Components:
- **Main Runtime**: `main.py` orchestrates the online exploration sessions
- **Runtime Engine**: `rt/` directory contains the core adaptive exploration logic

### 🔁 Workflow:
1. Initiates exploration sessions with configurable parameters
2. Performs iterative probing with `N_PROBING` initial attempts
3. Conducts multi-turn conversations (`N_TURN`) to explore temporal vulnerabilities
4. Logs detailed interaction traces for analysis
5. Dynamically adjusts strategies based on success/failure patterns

### ▶️ Running Scripts:

First, we need to host the judge models of ASTRA for evaluating whether a generated code snippet is vulnerable or not.
Hosting the model using the following command:
```bash
vllm serve microsoft/Phi-4-mini-instruct --dtype auto --api-key <YOUR API KEY> --swap_space 32 --max-model-len 8192 --enable-lora --lora-modules PurCL/astra-judge-121k=PurCL/astra-judge-121k  PurCL/astra-judge-10k=PurCL/astra-judge-10k
```
It could be hosted on an A6000 GPU with 48GB memory.
Specify the hosted judge model at `resources/online-judge.yaml`.

The online temporal exploration component requires a rewriter model to reason about the target system's responses over multiple turns. It is also used as the judge model for evaluating whether the target system's response is helpful for malicious purposes.
It could be a black-box LLM or any model hosted with vLLM.
Specify the hosted model at `online/rt/temporal_explorator/config/default_config.yaml`.
By default, we use `Qwen/Qwen3-Coder-30B-A3B-Instruct`.


To configure a blue team model, specify its settings in `resources/client-config.yaml` and the model will be automatically registered in the `_client_registry` within `online/bt/client.py`. 

**🟦 For open-source models hosted via vLLM:**
- Set the client type to `LocalOpenAIBTClient` (automatically handled)
- Configure `model_name`, `addr`, and `api_key` in the config file
- Example models: `microsoft/Phi-4-mini-instruct`, `Qwen/Qwen2.5-Coder-7B-Instruct`, `mistralai/Mistral-Instruct-8B`

**☁️ For models hosted on Amazon Bedrock:**
- The system automatically uses the appropriate client class based on the model name
- **OpenAI-compatible models** (e.g., `gpt-oss-20b`, `gpt-oss-120b`): Use `BedrockOpenAIBTClient` with parameters like `max_completion_tokens`, `temperature`, `reasoning_effort`
- **Anthropic models** (e.g., `claude-3.5-haiku`): Use `BedrockAnthropicBTClient` with parameters like `max_tokens`, `temperature`, `anthropic_version`, `top_k`
- **Claude Sonnet models**: Use `BedrockAnthropicBTClient` with the full ARN as model name

The configuration system automatically maps model names to the correct client implementation, so you only need to specify the appropriate parameters in `resources/client-config.yaml`.

#### 🧱 Using a new Bedrock model (not compatiable with current Client API)

If you want to use a Bedrock model that is not currently provided, you need to:

1. Create a client class that inherits from `BedrockBTClient`, and implement `_construct_body` and `_parse_response` because request/response formats can differ across providers/models.
2. Register the client in the `_client_registry` (or call `BTClientFactory.register_client`).
3. Add the model’s configuration in `resources/client-config.yaml`.

Minimal example:

```python
# online/bt/client.py

class MyBedrockCustomClient(BedrockBTClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Read any custom params from kwargs if needed, e.g.:
        # self.max_tokens = kwargs.get("max_tokens", 1024)
        # self.temperature = kwargs.get("temperature", 0.8)

    def _construct_body(self, messages):
        # Convert ASTRA's message format to the model's expected format
        converted = []
        for msg in messages:
            converted.append({
                "role": "user" if msg["role"] == "attacker" else "assistant",
                "content": msg["content"],
            })
        return {
            "messages": converted,
            # include any model-specific fields here
            # "max_tokens": self.max_tokens,
            # "temperature": self.temperature,
        }

    def _parse_response(self, response):
        # Extract final text from Bedrock provider's response JSON
        # return response["choices"][0]["message"]["content"]  # example shape
        raise NotImplementedError


# Register (either edit the registry dict or call the helper)
BTClientFactory.register_client(
    "provider.my-custom-model:1:0",  # the identifier you will use in config
    MyBedrockCustomClient,
)
```

Example configuration:

```yaml
# resources/client-config.yaml

my-custom-model:
  model_name: provider.my-custom-model:1:0
  region: us-west-2
  # model-specific params, passed to the client via **kwargs
  max_tokens: 1024
  temperature: 0.8
  read_timeout: 240
```

▶️ Then run the main exploration script:
```bash
python3 online/main.py --model_name <name of the blue team model> --log <path to the output log file> --n_session <number of chat sessions> --n_probing <number of initial probing sessions before the chat sessions> --n_turn <maximum number of turns per session>
```