from kg_utils import tree_loads, TreeNode
from tqdm import tqdm
from agent_sec_composer.main_agent import MainAgentInput, run_main_agent
import asyncio
import os
import json

kg_fin = tree_loads(open("kg/agent-sec/init.gen.kg", "r").read())


def _get_leaf_nodes_from_kg(kg: TreeNode) -> list[TreeNode]:
    """
    Get all leaf nodes from a given knowledge graph (kg).
    """
    if kg is None:
        return []

    leaf_nodes = []

    def dfs(node: TreeNode):
        if not node.children:  # If no children, it's a leaf node
            leaf_nodes.append(node)
        else:
            for child in node.children:
                dfs(child)

    dfs(kg)
    return leaf_nodes

def gen_instance_id(concrete_prohibited_instance: str, technique_family: str, prohibited_domain: str) -> str:
    return f"{prohibited_domain}_{technique_family}_{concrete_prohibited_instance}".replace(":", "__").replace(" ", "-").replace("/", "__")

kg_leaves = _get_leaf_nodes_from_kg(kg_fin)

fout_name = 'data_out/syn_agent_sec.jsonl'
if os.path.exists(fout_name):
    existing_data = [json.loads(line) for line in open(fout_name, 'r')]
else:
    existing_data = []

fout = open(fout_name, 'a')

existing_ids = set([entry['instance_id'] for entry in existing_data])
to_query = []
for leaf_node in kg_leaves:
    concrete_prohibited_instance = leaf_node.get_name()
    technique_family = leaf_node.parent.get_name()
    prohibited_domain = leaf_node.parent.parent.get_name()
    instance_id = gen_instance_id(concrete_prohibited_instance, technique_family, prohibited_domain)
    if instance_id not in existing_ids:
        to_query.append(leaf_node)
    else:
        print(f"Instance {instance_id} already exists")

print(f"Number of instances to query: {len(to_query)}")


async def query_one(leaf_node: TreeNode):
    concrete_prohibited_instance = leaf_node.get_name()
    technique_family = leaf_node.parent.get_name()
    prohibited_domain = leaf_node.parent.parent.get_name()
    instance_id = gen_instance_id(concrete_prohibited_instance, technique_family, prohibited_domain)
    # set os env variable OPENAI_AGENTS_DISABLE_TRACING=1
    os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    main_agent_input = MainAgentInput(problem_id=instance_id, prohibited_domain=prohibited_domain, technique_family=technique_family, concrete_prohibited_instance=concrete_prohibited_instance)
    try:
        final_output, message_history = await run_main_agent(main_agent_input)
        ret_entry = {
            'instance_id': instance_id,
            'concrete_prohibited_instance': concrete_prohibited_instance,
            'technique_family': technique_family,
            'prohibited_domain': prohibited_domain,
            'final_output': final_output,
            'message_history': message_history,
        }
        return ret_entry
    except Exception as e:
        print(f"Error querying instance {instance_id}: {e}")
        return None

# async run, max parallel num is K
K = 50
semaphore = asyncio.Semaphore(K)
async def run_all():
    pbar = tqdm(total=len(to_query), desc="Querying instances")
    async def run_with_semaphore(leaf_node: TreeNode):
        async with semaphore:
            ret = await query_one(leaf_node)
            pbar.update(1)
            if ret is None:
                return
            fout.write(json.dumps(ret) + "\n")
            fout.flush()
    tasks = [run_with_semaphore(leaf_node) for leaf_node in to_query]
    await asyncio.gather(*tasks)
    pbar.close()
    fout.close()

asyncio.run(run_all())