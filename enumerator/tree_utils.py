
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

def get_all_expansion_paths(root: TreeNode):
    """
    Get all paths in the tree that have expansion hints (nodes starting with '~').
    Returns a list of lists, where each inner list is a path from root to a node with an expansion hint.
    """
    if root is None:
        return []
    
    paths = []
    
    def dfs(node, current_path):
        current_path.append(node)
        
        # If this node has an expansion hint, save the path
        if node.has_expansion_hint():
            paths.append(current_path.copy())
        
        # Recur for children
        for child in node.children:
            dfs(child, current_path)
        
        # Backtrack
        current_path.pop()
    
    dfs(root, [])
    # remove 'root' from paths
    for i in range(len(paths)):
        if paths[i]:
            paths[i] = paths[i][1:]
    return paths

# Example usage and testing
if __name__ == "__main__":
    # Test the implementation
    tree_str = """
Root
  Child11
    ~Child21
    Child22
  ~Child12
    Child23"""
    
    # Load tree from string
    root = tree_loads(tree_str)
    print("Loaded tree:")
    print(tree_dumps(root))
    
    print("\nTree structure verification:")
    print(f"Root: {root.name}")
    print(f"Root children: {[child.name for child in root.children]}")
    if root.children:
        print(f"Child11 children: {[child.name for child in root.children[0].children]}")
        print(f"Child12 children: {[child.name for child in root.children[1].children]}")
    
    # Test round-trip
    dumped = tree_dumps(root)
    reloaded = tree_loads(dumped)
    dumped_again = tree_dumps(reloaded)
    
    print(f"\nRound-trip test passed: {dumped == dumped_again}")

    expansion_paths = get_all_expansion_paths(root)
    print()