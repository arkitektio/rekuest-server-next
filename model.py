
# Initialiaze django

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rekuest.settings")

django.setup()

# Import the models
from facade import models
from pydantic import BaseModel, Field







## Build dependency graph

x = models.Template.objects.get(id=8)



class InvalidNode(BaseModel):
    id: int
    initial_hash: str


class NodeNode(BaseModel):
    id: int
    node_id: str


class TemplateNode(BaseModel):
    id: int
    template_id: str



class DependencyEdge(BaseModel):
    id: int
    source: str 
    target: str
    optional: bool



Node = NodeNode | InvalidNode | TemplateNode


class Graph(BaseModel):
    nodes: list[Node]
    edges: list[DependencyEdge]



def build_graph_recursive(template_id: int, edges: list[DependencyEdge], nodes: list[Node]) -> None:


    template = models.Template.objects.get(id=template_id)
    nodes.append(TemplateNode(id=template.id, template_id=template.id))

    for dep in template.dependencies.all():
        if dep.node is not None:
            print("Valid node")
            nodes.append(NodeNode(id=dep.node.id, node_id=dep.node.id))
            edges.append(DependencyEdge(id=dep.id, source=dep.node.hash, target=template.node.hash, optional=dep.optional))
            for template in dep.node.templates.all():
                build_graph_recursive(template.id, edges, nodes)

        else:
            print("Invalid node")
            nodes.append(InvalidNode(id=dep.id, initial_hash=dep.initial_hash))
            edges.append(DependencyEdge(id=dep.id, source=dep.initial_hash, target=template.node.hash, optional=dep.optional))




def build_graph(template_id: int) -> Graph:
    nodes = []
    edges = []
    build_graph_recursive(template_id, edges, nodes)
    return Graph(nodes=nodes, edges=edges)


x = build_graph(8)
print(x.json())