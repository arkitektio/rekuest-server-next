from typing import List
from facade import models
from .models import NodeNodeModel, InvalidNodeModel, TemplateNodeModel, DependencyEdgeModel, DependencyGraphModel, NodeModel, ImplementationEdgeModel, EdgeModel
from uuid import uuid4


def build_graph_recursive(template: models.Template, edges: list[EdgeModel], nodes: list[NodeModel], connect_to = []) -> None:

    try:
        provision = template.provision
    except Exception as e:
        provision = None


    template_node = TemplateNodeModel(
        id=template.id, 
        template_id=template.id, 
        interface=template.interface, 
        client_id=template.agent.registry.app.client_id, 
    )

    nodes.append(template_node)

    for dep in template.dependencies.all():

        if dep.node is not None:
            node = NodeNodeModel(node_id=dep.node.id, name=dep.node.name)

            for node_template in dep.node.templates.all():
                build_graph_recursive(node_template, edges, nodes, connect_to=[node.id])

        else:
            node = InvalidNodeModel(initial_hash=dep.initial_hash)

        dep_edge = DependencyEdgeModel(source=template_node.id, target=node.id, optional=dep.optional, dep_id=dep.id)


        nodes.append(node)
        edges.append(dep_edge)


    for i in connect_to:
        edges.append(ImplementationEdgeModel(source=i, target=template_node.id, optional=False))




def build_template_graph(template: models.Template) -> DependencyGraphModel:
    nodes = []
    edges = []
    build_graph_recursive(template, edges, nodes)
    return DependencyGraphModel(nodes=nodes, edges=edges)


def build_node_graph(node: models.Node) -> DependencyGraphModel:
    nodes = []
    edges = []

    node_node = NodeNodeModel(node_id=node.id, name=node.name)
    nodes.append(node_node)

    for template in node.templates.all():
        build_graph_recursive(template, edges, nodes, connect_to=[node_node.id])
    return DependencyGraphModel(nodes=nodes, edges=edges)



def build_reservation_graph_recursive(reservation: models.Reservation, edges: list[EdgeModel], nodes: list[NodeModel], connect_to = []) -> None:


    node_node = NodeNodeModel(node_id=reservation.node.id, name=reservation.node.name, reservation_id=reservation.id, status=reservation.status)
    nodes.append(node_node)


    for temp in reservation.node.templates.all():

        linked = reservation.provisions.filter(template=temp).exists() 
        provision = temp.provision

        template_node = TemplateNodeModel(id=temp.id, template_id=temp.id, interface=temp.interface, provision_id=provision.id, client_id=temp.agent.registry.app.client_id, linked=linked, reservation_id=reservation.id, status=provision.status, active=provision.active)
        nodes.append(template_node)
        edges.append(ImplementationEdgeModel(source=node_node.id, target=template_node.id, optional=False, linked=linked))
        
        if linked:
            for reservation in provision.caused_reservations.all():
                build_reservation_graph_recursive(reservation, edges, nodes, connect_to=[template_node.id])



    for i in connect_to:
        edges.append(DependencyEdgeModel(source=i, target=node_node.id, optional=False))



def build_reservation_graph(reservation: models.Reservation) -> DependencyGraphModel:
    nodes = []
    edges = []

    build_reservation_graph_recursive(reservation, edges, nodes)

    return DependencyGraphModel(nodes=nodes, edges=edges)