from rich.tree import Tree
from graphviz import Digraph
import uuid




def build_rich_tree(node):
    label = type(node).__name__




    if hasattr(node, "op"):
        label += f"({node.op})"
    elif hasattr(node, "name"):
        label += f"({node.name})"
    elif hasattr(node, "value"):
        label += f"({node.value})"




    tree = Tree(label)




    for field, value in vars(node).items():
        if isinstance(value, list):
            for item in value:
                tree.add(build_rich_tree(item))
        elif hasattr(value, "__dict__"):
            tree.add(build_rich_tree(value))




    return tree








def build_graphviz(node, dot, parent_id=None):
    node_id = str(uuid.uuid4())




    label = type(node).__name__




    if hasattr(node, "op"):
        label += f"({node.op})"
    elif hasattr(node, "name"):
        label += f"({node.name})"
    elif hasattr(node, "value"):
        label += f"({node.value})"




    dot.node(node_id, label)




    if parent_id:
        dot.edge(parent_id, node_id)




    for field, value in vars(node).items():
        if isinstance(value, list):
            for item in value:
                build_graphviz(item, dot, node_id)
        elif hasattr(value, "__dict__"):
            build_graphviz(value, dot, node_id)




    return dot
