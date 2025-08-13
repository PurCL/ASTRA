import ast
import sys

class DocstringRemover(ast.NodeTransformer):
    """
    AST transformer that removes docstrings from modules, classes, and functions.
    """
    def visit_Module(self, node):
        self.generic_visit(node)
        # Remove module docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        # Remove function docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node

    def visit_AsyncFunctionDef(self, node):
        self.generic_visit(node)
        # Remove async function docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node

    def visit_ClassDef(self, node):
        self.generic_visit(node)
        # Remove class docstring
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body.pop(0)
        return node


def remove_docstrings(source: str) -> str:
    """
    Parse the source code, remove docstrings, and return the transformed code.
    """
    try:
        tree = ast.parse(source)
    except Exception as e:
        # print(f"Error parsing source code: {e}", file=sys.stderr)
        return None
    remover = DocstringRemover()
    new_tree = remover.visit(tree)
    ast.fix_missing_locations(new_tree)
    try:
        # Python 3.9+ provides ast.unparse
        return ast.unparse(new_tree)
    except AttributeError:
        # For older Python versions, fall back to compile + exec to reconstruct source
        import astor
        return astor.to_source(new_tree)