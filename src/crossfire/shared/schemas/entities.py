"""Entity graph schemas for gold entity graphs."""

import networkx as nx
from pydantic import BaseModel


class EntityNode(BaseModel):
    id: str
    entity_type: str
    canonical_name: str
    aliases: list[str] = []
    subcorpus_memberships: list[str] = []


class EntityEdge(BaseModel):
    source: str
    target: str
    relationship_type: str


class EntityGraph(BaseModel):
    nodes: list[EntityNode] = []
    edges: list[EntityEdge] = []

    def to_networkx(self) -> nx.Graph:
        """Convert to a NetworkX graph with node/edge attributes."""
        g = nx.Graph()
        for node in self.nodes:
            g.add_node(
                node.id,
                entity_type=node.entity_type,
                canonical_name=node.canonical_name,
                aliases=node.aliases,
                subcorpus_memberships=node.subcorpus_memberships,
            )
        for edge in self.edges:
            g.add_edge(edge.source, edge.target, relationship_type=edge.relationship_type)
        return g

    @classmethod
    def from_networkx(cls, g: nx.Graph) -> "EntityGraph":
        """Construct an EntityGraph from a NetworkX graph."""
        nodes = []
        for node_id, attrs in g.nodes(data=True):
            nodes.append(EntityNode(
                id=node_id,
                entity_type=attrs.get("entity_type", ""),
                canonical_name=attrs.get("canonical_name", ""),
                aliases=attrs.get("aliases", []),
                subcorpus_memberships=attrs.get("subcorpus_memberships", []),
            ))
        edges = []
        for src, tgt, attrs in g.edges(data=True):
            edges.append(EntityEdge(
                source=src,
                target=tgt,
                relationship_type=attrs.get("relationship_type", ""),
            ))
        return cls(nodes=nodes, edges=edges)
