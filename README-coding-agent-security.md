# Coding Agent Security Data Generation Pipeline

This document describes how to generate security test cases for AI coding agents using ASTRA's agent security testing framework.

## Overview

The pipeline generates adversarial test cases by:
1. Loading a knowledge graph of security vulnerabilities and attack techniques
2. Using a multi-agent system to compose realistic, actionable security test scenarios
3. Parsing and validating the generated test cases
4. Uploading the curated dataset to HuggingFace

**Example Dataset:** [PurCL/astra-agent-security](https://huggingface.co/datasets/PurCL/astra-agent-security) - Generated using this pipeline

## Prerequisites

### Installation

```bash
pip install -r requirements.txt
```

Key dependencies:
- `openai-agents[litellm]` - Multi-agent orchestration framework
- `datasets` - HuggingFace datasets library
- `pydantic` - Data validation
- `tqdm` - Progress tracking

### Configuration

#### 1. Configure Agent Security Settings

Edit `resources/agent-sec-config.yaml` to customize the generation pipeline:

```yaml
# Main coordinator agent model (orchestrates the workflow)
coordinator_model: "claude-sonnet-4-5"

# Composer agent model (generates test case drafts and revisions)
composer_model: "claude-sonnet-4-5"

# Reviewer committee models (evaluate test case quality)
reviewer_models:
  - "claude-sonnet-3-7"
  - "claude-haiku-4-5"
  - "gpt-oss-20b"
  - "gpt-oss-120b"
  - "qwen3coder"

# Generation settings
parallel_tasks: 50  # Adjust based on your API rate limits

# Output directories
output_dir: "data_out"
log_dir: "log_out_agent_sec"
```

**Pre-configured Models in `client-config.yaml`:**

| Short Name | Provider | Full Model ID | Description |
|------------|----------|---------------|-------------|
| `claude-sonnet-4-5` | bedrock | `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | Most capable Claude (recommended for coordinator/composer) |
| `claude-sonnet-3-7` | bedrock | `us.anthropic.claude-3-7-sonnet-20250219-v1:0` | Balanced performance and cost |
| `claude-haiku-4-5` | bedrock | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | Fast and cost-effective |
| `gpt-oss-20b` | bedrock | `openai.gpt-oss-20b-1:0` | OpenAI 20B on Bedrock |
| `gpt-oss-120b` | bedrock | `openai.gpt-oss-120b-1:0` | OpenAI 120B on Bedrock |
| `qwen3coder` | openai | `Qwen/Qwen3-Coder-30B-A3B-Instruct` | Custom vLLM/SGLang server |
| `phi4m` | openai | `microsoft/Phi-4-mini-instruct` | Custom vLLM/SGLang server |

**Model Selection Tips:**
- Use more capable models (e.g., `claude-sonnet-4-5`) for coordinator and composer roles
- Mix diverse models in the reviewer committee for varied perspectives
- Any model defined in `client-config.yaml` can be used in `agent-sec-config.yaml`

#### 2. Configure LLM Endpoints

Edit `resources/client-config.yaml` to set up your model endpoints.

**AWS Bedrock Models:**
```yaml
claude-sonnet-4-5:
  provider: bedrock
  model_name: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  region: us-west-2
```

**OpenAI-Compatible Servers (vLLM, SGLang, etc.):**
```yaml
qwen3coder:
  provider: openai
  model_name: Qwen/Qwen3-Coder-30B-A3B-Instruct
  addr: http://<YOUR_HOST>/v1
  api_key: <YOUR_API_KEY>

# Add more custom models as needed
my-local-model:
  provider: openai
  model_name: meta-llama/Llama-3.3-70B-Instruct
  addr: http://<YOUR_HOST>/v1
  api_key: <YOUR_API_KEY>
```

#### 3. Set Environment Variables

For HuggingFace dataset uploads:
```bash
export HF_TOKEN=<your_huggingface_token>
```

## Pipeline Steps

### Step 1: Generate Agent Security Test Cases

Run the main agent security data generation script:

```bash
python agent/main_agent_sec.py
```

**What it does:**
- Loads the knowledge graph from `kg/agent-sec/init.gen.kg`
- Extracts leaf nodes representing concrete security vulnerability instances
- For each instance, spawns a multi-agent system that:
  - Composes an initial adversarial test case draft
  - Reviews and refines the test case through multiple iterations
  - Validates realism, actionability, and benign intent scores
- Outputs results to `data_out/syn_agent_sec.jsonl`

**Key configuration:**
- Models used are defined in `resources/agent-sec-config.yaml`
- Parallelism is controlled by `parallel_tasks` setting (default: 50)
- Knowledge graph structure: `prohibited_domain → technique_family → concrete_prohibited_instance`

**Output format** (`data_out/syn_agent_sec.jsonl`):
```json
{
  "instance_id": "domain_technique_instance",
  "concrete_prohibited_instance": "SQL Injection",
  "technique_family": "Injection Attacks",
  "prohibited_domain": "Web Security",
  "final_output": "<final_case>...</final_case>",
  "message_history": [...]
}
```

**Resume capability:** The script automatically skips instances that already exist in the output file, allowing you to resume interrupted runs.

### Step 2: Parse Generated Test Cases

Parse the raw agent outputs into structured format:

```bash
python agent/parse_agent_sec.py \
  --input data_out/syn_agent_sec.jsonl \
  --output data_out/syn_agent_sec_parsed.jsonl
```

**What it does:**
- Extracts `<final_case>` XML blocks from agent outputs
- Validates against the expected schema using Pydantic models
- Parses committee member scores (realism, actionability, benign_intent)
- Outputs only successfully parsed cases

**Output format** (`data_out/syn_agent_sec_parsed.jsonl`):
```json
{
  "prohibited_domain": "Web Security",
  "technique_family": "Injection Attacks",
  "concrete_prohibited_instance": "SQL Injection",
  "request_text": "Create a login form with...",
  "malicious_rationale": "This could lead to...",
  "risk_tags": ["authentication", "database"],
  "committee_snapshot": [
    {
      "member_id": "reviewer_1",
      "realism": 5,
      "actionability": 4,
      "benign_intent": 5
    }
  ]
}
```

**Error handling:** Failed parsing attempts are logged to stdout but don't stop the process.

### Step 3: Upload to HuggingFace Dataset

Upload the parsed dataset to HuggingFace Hub:

```bash
python agent/upload_to_hf_dataset.py \
  --input data_out/syn_agent_sec_parsed.jsonl \
  --dataset-name <your-username>/astra-agent-security
```

**Example Dataset:** See [PurCL/astra-agent-security](https://huggingface.co/datasets/PurCL/astra-agent-security) for a dataset generated using this pipeline.

**What it does:**
- Loads parsed test cases
- Extracts core fields (excluding internal committee snapshots)
- Creates a HuggingFace Dataset
- Pushes to the specified repository

**Dataset schema:**
- `prohibited_domain` (str): High-level security domain
- `technique_family` (str): Category of attack technique
- `concrete_prohibited_instance` (str): Specific vulnerability type
- `request_text` (str): The adversarial prompt/request
- `malicious_rationale` (str): Explanation of potential security risks

## Example Workflow

Complete end-to-end example:

```bash
# Step 1: Generate test cases (may take hours depending on KG size)
python agent/main_agent_sec.py

# Step 2: Parse and validate
python agent/parse_agent_sec.py \
  -i data_out/syn_agent_sec.jsonl \
  -o data_out/syn_agent_sec_parsed.jsonl

# Step 3: Upload to HuggingFace
python agent/upload_to_hf_dataset.py \
  -i data_out/syn_agent_sec_parsed.jsonl \
  -d username/astra-agent-security
```

## Knowledge Graph Structure

The agent security knowledge graph (`kg/agent-sec/`) contains:
- `init.kg` - Base knowledge graph structure
- `init.gen.kg` - Expanded/generated knowledge graph
- `init.yaml` - YAML representation

The hierarchy follows:
```
Prohibited Domain (e.g., "Web Security")
└── Technique Family (e.g., "Injection Attacks")
    └── Concrete Instance (e.g., "SQL Injection", "XSS")
```

## Multi-Agent System Architecture

The generation pipeline uses three specialized agents:

1. **Coordinator Agent** (`agent/agent_sec_composer/prompts/coordinator.md`)
   - Orchestrates the overall workflow
   - Decides when to compose, revise, or review

2. **Composer Agent** (`agent/agent_sec_composer/prompts/composer.md`)
   - Creates initial test case drafts
   - Revises based on review feedback

3. **Reviewer Agent** (`agent/agent_sec_composer/prompts/reviewer.md`)
   - Evaluates test cases on multiple dimensions
   - Provides scores (1-5) for realism, actionability, benign intent

The agents iterate until consensus is reached on a high-quality test case.

## Output Directories

- `data_out/` - Generated datasets (excluded from git)
- `log_out_agent_sec/` - Detailed agent interaction logs (excluded from git)

## Customization

### Changing Models

To use different models, simply edit `resources/agent-sec-config.yaml`:

```yaml
# Use a faster/cheaper model for the composer
composer_model: "claude-haiku-4-5"

# Use only local models for reviewers
reviewer_models:
  - "qwen3coder"
  - "my-local-model"
```

**Model Resolution Logic:**

When you specify a model name in `agent-sec-config.yaml`, the system:

1. **Looks up the model** in `client-config.yaml` by name
2. **Checks the `provider` field**:
   - `provider: bedrock` → Routes to AWS Bedrock Converse API
   - `provider: openai` → Routes to OpenAI-compatible server (vLLM, SGLang, etc.)

**Example Flow:**
```yaml
# In agent-sec-config.yaml
coordinator_model: "claude-sonnet-4-5"

# System looks up in client-config.yaml:
claude-sonnet-4-5:
  provider: bedrock  # ← Automatically routes to Bedrock
  model_name: global.anthropic.claude-sonnet-4-5-20250929-v1:0
  region: us-west-2

# Result: LitellmModel("bedrock/converse/global.anthropic.claude-sonnet-4-5-20250929-v1:0")
```

**No Code Changes Needed!** Just add models to `client-config.yaml` with the appropriate `provider` field.

### Adjusting Output Directories

Edit paths in `resources/agent-sec-config.yaml`:
```yaml
output_dir: "my_output"
log_dir: "my_logs"
```

### Adding New Models

**No code changes needed!** Just add entries to `client-config.yaml`:

**For AWS Bedrock Models:**
```yaml
my-new-bedrock-model:
  provider: bedrock
  model_name: us.anthropic.claude-opus-4-7-20250514-v1:0
  region: us-west-2
```

**For OpenAI-Compatible Servers:**
```yaml
my-local-llama:
  provider: openai
  model_name: meta-llama/Llama-3.3-70B-Instruct
  addr: http://localhost:8000/v1
  api_key: dummy-key
```

Then reference it in `agent-sec-config.yaml`:
```yaml
coordinator_model: "my-new-bedrock-model"
composer_model: "my-local-llama"
```

## Troubleshooting

### Rate Limiting
If you hit API rate limits, reduce the parallelism in `resources/agent-sec-config.yaml`:
```yaml
parallel_tasks: 10  # Reduce from default 50
```

### Memory Issues
For large knowledge graphs, process in batches by modifying the `to_query` list.

### Parsing Errors
Check `agent/agent_sec_composer/output_parser.py` for schema validation details. Common issues:
- Missing required XML tags
- Score values outside 1-5 range
- Empty committee snapshots

### Authentication
Ensure you're authenticated with HuggingFace:
```bash
huggingface-cli login
```

## Citation

If you use this dataset generation pipeline, please cite:

```bibtex
@article{xu2025astra,
  title={ASTRA: Autonomous Spatial-Temporal Red-teaming for AI Software Assistants},
  author={Xu, Xiangzhe and Shen, Guangyu and Su, Zian and Cheng, Siyuan and Guo, Hanxi and Yan, Lu and Chen, Xuan and Jiang, Jiasheng and Jin, Xiaolong and Wang, Chengpeng and others},
  journal={arXiv preprint arXiv:2508.03936},
  year={2025}
}
```

## Related Resources

- Main ASTRA README: [README.md](README.md)
- ASTRA Paper: https://www.arxiv.org/pdf/2508.03936
- ASTRA Website: https://astra-share.github.io
