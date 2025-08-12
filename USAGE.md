# ASTRA Usage Guide

ASTRA is a comprehensive red-teaming system that consists of three major components working together to perform autonomous vulnerability discovery and assessment of AI software assistants.

## Component 1: Offline Domain Modeling

**Location**: `enumerator/`

This component takes a target domain as input and outputs a structured knowledge graph that captures domain-specific vulnerabilities and attack vectors.

### Key Components:
- **Data Structure**: The knowledge graph structure is defined in `enumerator/tree_utils.py`, which provides the foundational tree-based representation for organizing domain knowledge hierarchically.
- **LLM-based Enumerator**: The core enumeration logic is implemented in `enumerator/enumerator.py`, which uses large language models to systematically generate comprehensive domain knowledge graphs.

### Domain Examples:
The repository includes pre-built knowledge graphs for two domains: **Secure Code Generation** and **Security Event Guidance**. Examples include `enumerator/enumerate_pl_feature.py` which enumerates programming language features, `enumerator/enumerate_context.py` for coding contexts, and `enumerator/enumerate_mal_tactics.py` for tactics as defined in [MITRE ATT&CK](https://attack.mitre.org/).

### Usage Notes:
- Knowledge graph enumeration is a one-time setup process per domain
- Pre-built knowledge graphs are provided in the `kg/` directory
- Users typically don't need to re-run the enumerator unless extending to new domains
- Interested developers can follow the existing examples to extend ASTRA to additional domains

## Component 2: Offline Jailbreaking Prompt Generation

**Location**: `agent/`

This component leverages the structured knowledge graphs to systematically generate diverse and sophisticated jailbreaking prompts through multi-agent collaboration.

### Key Components:
- **Main Entry Points**: 
    - `main_sec_code.py`: Orchestrates prompt generation for secure code scenarios
    - `main_sec_event.py`: Handles security event-based prompt generation
- **Multi-Agent Architecture**:
    - `sec_code_composer/`: Contains agents specialized in composing code-related attack prompts
    - `sec_event_composer/`: Houses agents for security event scenario generation
    - `cgr_agent/`: Uses [Amazon CodeGuru](https://aws.amazon.com/codeguru/) static analyzer to provide feedback on whether a generated code snippet is vulnerable or not


### Workflow:
1. Samples relevant nodes from the domain knowledge graph
2. Uses multi-agent collaboration to compose contextually rich attack scenarios
3. Generates diverse prompts with varying complexity and attack vectors
4. Exports synthesized prompts for downstream evaluation

### Running Scripts:

```bash
python3 agent/main_sec_code.py --fout <output_file.jsonl> --log <path to log_file>
python3 agent/main_sec_event.py --fout <output_file.jsonl> --log <path to log_file>
```

## Component 3: Online Adaptive Exploration and Violation Generation

**Location**: `online/`

This component performs real-time adaptive red-teaming by dynamically probing target AI systems and adjusting attack strategies based on responses.

### Key Components:
- **Main Runtime**: `main.py` orchestrates the online exploration sessions
- **Runtime Engine**: `rt/` directory contains the core adaptive exploration logic

### Adaptive Exploration Features:
- **Spatial Probing**: Explores the input space by varying prompt characteristics, contexts, and attack vectors
- **Temporal Reasoning**: Analyzes multi-turn conversations to identify vulnerabilities in reasoning chains
- **Dynamic Strategy Adjustment**: Adapts attack strategies based on target system responses

### Workflow:
1. Initiates exploration sessions with configurable parameters
2. Performs iterative probing with N_PROBING initial attempts
3. Conducts multi-turn conversations (N_TURN) to explore temporal vulnerabilities
4. Logs detailed interaction traces for analysis
5. Dynamically adjusts strategies based on success/failure patterns

### Running Scripts:

First, modify the `online/tests/example_bt.py` to specify your target coder model.
Then run the main exploration script:
```bash

python3 online/main.py --pair_id <pair_id>
```