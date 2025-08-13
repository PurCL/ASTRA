from typing import List
from tree_utils import get_all_expansion_paths, tree_loads, tree_dumps, TreeNode
from tqdm import tqdm
from claude_utils import query_claude
import asyncio

requirements_of_enumerator = """
## Requirements of your enumeration

I will input a path from the root node to a leaf node.
Your task is to enumerate the direct children of this leaf node in the hierarchy.

For example, suppose that I input a path like this:
Root -> Node at Layer 1 -> Node at Layer 2
You should and should only enumerate the direct children of the node at Layer 2.
You should try to summarize what is already included in the children of the current node.
Do not repeat what is already there.

For each step, you should
(1) analyze what might be a child of the current node, what you plan to enumerate next
(2) enumerate up to 10 children of the current node,
(3) summarize what is already included in the children of the current node.

Pay special attention to which layer the leaf node is at.
For example, if the given leaf node is at Layer 2, you should enumerate only nodes at Layer 3.

If your enumeration contains a node that is very similar to what is already there,
I will give you feedback so that you know you should not enumerate it again.

The process is iterative. For each round, enumerate 10 or fewer children.
If you have done with your enumeration, return "[[DONE]]" as the only output.

## Output Format
<Analysis>
... (your reasoning of the current node and what might be its children in the next layer)
</Analysis>

<Enumeration>
... (enumeration of the direct children of the current node, one per line)
</Enumeration>

<Existing Children>
... (summary of what is already included in the children of the current node, including the children you just enumerated)
</Existing Children>
"""


class Enumerator:

    def __init__(self, path_to_explore: List[TreeNode], starting_point: str, pbar=True):
        """
        Initialize the enumerator with a path to explore and a starting point.
        :param path_to_explore: List of TreeNode objects representing the path to explore.
        :param starting_point: The initial prompt or context for the enumeration.
        """
        self.path_to_explore = path_to_explore
        self.starting_point = starting_point
        self.pbar = pbar

    def _path_to_query(self, path: List[TreeNode]) -> str:
        """
        Convert a path to a query string.
        :param path: List of TreeNode objects representing the path.
        :return: A formatted query string.
        """
        path_str = " --> ".join([node.get_name() for node in path])
        node_to_enumerate = path[-1].get_name()
        return f"## Input\n\nPath (including the leaf node): {path_str}\nNode to enumerate: {node_to_enumerate}\n"
        
    def start_enumerate(self, budget=10):
        query = self.starting_point + "\n" + requirements_of_enumerator + '\n' + self._path_to_query(self.path_to_explore)
        message = [{"role": "user", "content": query}]
        enumerated = []
        if self.pbar:
            pbar = tqdm(total=budget, desc="Enumerating features")
        for i in range(budget):
            rsp = query_claude(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                messages=message,
                temperature=0.7,
                max_tokens=1024,
                system_prompt=None,
            )
            if "error" in rsp:
                # randomly sleep from 10 to 30 seconds
                import random
                sleep_time = random.randint(10, 30)
                print(f"Error: {rsp['error']}. Retrying in {sleep_time} seconds...")
                import time
                time.sleep(sleep_time)
                continue
                

            if self.pbar:
                pbar.update(1)
            rsp_txt = rsp["content"][0]["text"]
            if "DONE" in rsp_txt:
                print("Enumeration completed.")
                break
            if "<Enumeration>" not in rsp_txt or "</Enumeration>" not in rsp_txt:
                print("Error: Enumeration section not found in response.")
                break

            enumerated_string = (
                rsp_txt.split("<Enumeration>")[1].split("</Enumeration>")[0].strip()
            )

            def parse_enumerated_string(enumerated_string):
                """
                Parse the enumerated string into a list of children.
                """
                lines = enumerated_string.strip().split("\n")
                # lstrip potentially numeric prefixes like "1. ", "2. ", etc.
                children = [
                    line.lstrip("0123456789. ").strip() for line in lines if line.strip()
                ]
                return children

            children = parse_enumerated_string(enumerated_string)
            message.extend(
                [
                    {"role": "assistant", "content": rsp_txt},
                    {"role": "user", "content": "All children look good. Are there more?"}
                ]
            )
            enumerated.extend(children)
        return enumerated



if __name__ == "__main__":

    fin = open("kg/pl_features.kg", "r")
    tree_str = fin.read()
    fin.close()
    root = tree_loads(tree_str)
    paths_to_explore = get_all_expansion_paths(root)

    from vul_code_example import starting_point
    enumerator = Enumerator(paths_to_explore[0], starting_point)
    ret = enumerator.start_enumerate(budget=10)
    print()
