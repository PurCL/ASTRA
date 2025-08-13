

"""
Program language features
"""

# no need to enumerate:
# root --> (dataflow, controlflow)
# each has 'inter' and 'intra' procedure features



starting_point = """
Help me enumerate python program language features that may introduce challenges to a language model
in precisely understanding code semantics.

## Domain

Here is an example path in the hiearchy of features:

Layer0: Category: Data-flow features
Explanation: Layer0 describes the category of complexity.
It can be data-flow or control-flow features.

Layer1: Scope: Intra-procedural features
Explanation: Layer1 describes the scope of the features.
It can be intra-procedural or inter-procedural features.

Layer2: Nature of challenge: A model may have difficulty understanding data flow across variables with similar names.
Explanation: Layer2 describes the nature of the challenge.
It should be an essential challenge to a language model in understanding code semantics.
** This layer should contain only the nature of the challenge, not specific instances. **
It should describe the challenges caused by the limitation of a model, not the detailed instances.

Layer3: Instance: Variable shadowing. (e.g., a variable is defined in a nested scope with the same name as a variable in an outer scope)
Explanation: Layer3 provides a specific instance of the challenge.
"""

queryA = """
## Input

Parent nodes: (Layer0) Dataflow features --> (Layer1) Intra-procedural features
Node to enumerate: (Layer2) A model may have difficulty understanding data flow across variables with similar names.
"""



queryB = """
## Input

Parent nodes: (Layer0) Dataflow features
Node to enumerate: (Layer1) Intra-procedural features
"""

from claude_utils import query_claude

message = [
    {"role": "user", "content": starting_point + queryB},
]

rsp = query_claude(
    messages=message,
    temperature=0.7,
    top_k=50,
    max_tokens=1024,
    system_prompt=None,
)

rsp_txt = rsp['content'][0]['text']

print()