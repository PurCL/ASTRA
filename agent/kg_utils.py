import numpy as np

class SpatialInfo:
    def __init__(self):
        self.succ = 0
        self.fail = 0

class TreeNode(SpatialInfo):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.children = []
        self.parent = None    

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def get_name(self):
        return self.name.lstrip("~")
    
    def has_expansion_hint(self):
        return self.name.startswith("~")
    
    def remove_expansion_hint(self):
        if self.has_expansion_hint():
            self.name = self.name.lstrip("~")
    
    def add_expansion_hint(self):
        if not self.has_expansion_hint():
            self.name = "~" + self.name

    def __str__(self):
        return "%s: (%d, %d)" % (self.name, self.succ, self.fail)

    def __repr__(self):
        return str(self)
    

def tree_loads(str_in):
    """
    Parse a string representation of a tree and return the root node.
    Indentation level determines parent-child relationships.
    """
    if not str_in or not str_in.strip():
        return None
        
    lines = str_in.strip().split('\n')
    
    # Stack to keep track of (node, indentation_level) pairs
    stack = []
    root = None
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Calculate indentation level (number of leading spaces)
        stripped = line.lstrip()
        indent_level = len(line) - len(stripped)
        node_name = stripped.strip()
        
        # Create new node
        new_node = TreeNode(node_name)
        
        if root is None:
            # First node becomes the root
            root = new_node
            stack = [(new_node, indent_level)]
        else:
            # Pop from stack until we find the correct parent
            # (parent has indentation level less than current node)
            while stack and stack[-1][1] >= indent_level:
                stack.pop()
            
            # The node at top of stack is the parent
            if stack:
                parent_node = stack[-1][0]
                parent_node.add_child(new_node)
            
            # Add current node to stack for potential future children
            stack.append((new_node, indent_level))
    
    return root

def kg_name2node(kg: TreeNode) -> dict:
    """
    Convert a knowledge graph (kg) to a dictionary mapping node names to TreeNode objects.
    """
    name2node = {}

    def dfs(node: TreeNode):        
        name2node[node.name] = node        
        for child in node.children:
            dfs(child)

    dfs(kg)
    return name2node

def kg_propagate(name2node: dict[str, TreeNode], name:str, is_succ: bool):
    node = name2node.get(name)
    if node is None:
        print("Error: Node not found in KG:", name)
        return
    def _update_parent(node: TreeNode, is_succ: bool):
        if is_succ:
            node.succ += 1            
        else:
            node.fail += 1
        if node.parent:
            _update_parent(node.parent, is_succ)
    _update_parent(node, is_succ)

def kg_sample(kg: TreeNode):
    if len(kg.children) == 0:
        # I'm a leaf node, return
        return kg.name
    else:
        all_children = kg.children
        alphas = np.array([c.succ + 1 for c in all_children])
        betas = np.array([c.fail + 1 for c in all_children])
        # beta distribution
        probs = np.random.beta(alphas, betas)
        # argmax
        idx = np.argmax(probs)
        return all_children[idx].name
