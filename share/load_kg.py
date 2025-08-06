
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


def tree_dumps(root: TreeNode):
    """
    Convert a tree to its string representation with indentation.
    Each level of depth adds 2 spaces of indentation.
    """
    if root is None:
        return ""
    
    result = []
    
    def dfs(node, depth):
        # Add current node with proper indentation
        indent = "  " * depth  # 2 spaces per level
        result.append(indent + node.name)
        
        # Recursively process children
        for child in node.children:
            dfs(child, depth + 1)
    
    dfs(root, 0)
    return '\n'.join(result)

# Example usage and testing
if __name__ == "__main__":
    # load .kg file
    kg_fin = open("sec-event/mal_software.gen.kg", "r").read()
    kg_in = tree_loads(kg_fin)



    # load bugtype.kg.json
    import json
    bugtype_fin = open("sec-code/bugtype.kg.json", "r").read()
    bugtype_in = json.loads(bugtype_fin)
    print()
    
    