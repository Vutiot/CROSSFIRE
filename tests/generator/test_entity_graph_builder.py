"""Tests for the entity graph builder."""

import pytest

from crossfire.generator.entity_graph_builder import build_entity_graph
from crossfire.shared.schemas.config import (
    DetectabilityDistribution,
    GeneratorConfig,
    IncoherenceConfig,
    ScopeDistribution,
)
from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.seed_manager import SeedManager


def _make_config(connectivity_level: int = 2, subcorpora_count: int = 5) -> GeneratorConfig:
    return GeneratorConfig(
        name="test",
        description="test config",
        master_seed=42,
        subcorpora_count=subcorpora_count,
        docs_per_subcorpus=20,
        connectivity_level=connectivity_level,
        doc_type_mix="balanced",
        incoherences=IncoherenceConfig(
            scope_distribution=ScopeDistribution(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
            mechanism="uniform",
            detectability_distribution=DetectabilityDistribution(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
            system_affinity="balanced",
            count="auto",
        ),
        distractor_ratio=0.3,
    )


@pytest.fixture
def seed_mgr():
    return SeedManager(master_seed=42)


class TestConnectivityLevel0:
    def test_no_shared_entities(self, seed_mgr):
        config = _make_config(connectivity_level=0)
        graph = build_entity_graph(config, seed_mgr)
        for node in graph.nodes:
            assert len(node.subcorpus_memberships) == 1, (
                f"Level 0: entity {node.id} should have exactly 1 subcorpus, "
                f"got {node.subcorpus_memberships}"
            )

    def test_produces_valid_graph(self, seed_mgr):
        config = _make_config(connectivity_level=0)
        graph = build_entity_graph(config, seed_mgr)
        assert len(graph.nodes) > 0
        assert isinstance(graph, EntityGraph)

    def test_aliases_are_canonical_only(self, seed_mgr):
        config = _make_config(connectivity_level=0)
        graph = build_entity_graph(config, seed_mgr)
        for node in graph.nodes:
            assert node.aliases == [node.canonical_name]


class TestConnectivityLevel1:
    def test_some_shared_entities(self, seed_mgr):
        config = _make_config(connectivity_level=1)
        graph = build_entity_graph(config, seed_mgr)
        shared = [n for n in graph.nodes if len(n.subcorpus_memberships) > 1]
        assert len(shared) > 0, "Level 1 should have shared entities"

    def test_aliases_are_canonical_only(self, seed_mgr):
        config = _make_config(connectivity_level=1)
        graph = build_entity_graph(config, seed_mgr)
        for node in graph.nodes:
            assert node.aliases == [node.canonical_name]


class TestConnectivityLevel2:
    def test_shared_entities_have_varied_aliases(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        shared = [n for n in graph.nodes if len(n.subcorpus_memberships) > 1]
        assert len(shared) > 0
        # At least some shared entities should have multiple alias forms
        multi_alias = [n for n in shared if len(n.aliases) > 1]
        assert len(multi_alias) > 0, "Level 2 should have entities with multiple aliases"

    def test_sharing_fraction_around_35_percent(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        shared = sum(1 for n in graph.nodes if len(n.subcorpus_memberships) > 1)
        fraction = shared / len(graph.nodes)
        assert 0.15 <= fraction <= 0.60, f"Level 2 shared fraction {fraction:.2f} out of range"


class TestConnectivityLevel3:
    def test_more_shared_than_level1(self, seed_mgr):
        config1 = _make_config(connectivity_level=1)
        config3 = _make_config(connectivity_level=3)
        graph1 = build_entity_graph(config1, seed_mgr)
        seed_mgr2 = SeedManager(master_seed=42)
        graph3 = build_entity_graph(config3, seed_mgr2)
        shared1 = sum(1 for n in graph1.nodes if len(n.subcorpus_memberships) > 1)
        shared3 = sum(1 for n in graph3.nodes if len(n.subcorpus_memberships) > 1)
        assert shared3 > shared1, f"Level 3 ({shared3}) should have more shared than level 1 ({shared1})"

    def test_aggressive_alias_variation(self, seed_mgr):
        config = _make_config(connectivity_level=3)
        graph = build_entity_graph(config, seed_mgr)
        # Level 3 adds case-swapped variants — aliases should be longer
        max_aliases = max(len(n.aliases) for n in graph.nodes)
        assert max_aliases >= 3, f"Level 3 should have entities with 3+ aliases, max was {max_aliases}"

    def test_dense_edges(self, seed_mgr):
        config = _make_config(connectivity_level=3)
        graph = build_entity_graph(config, seed_mgr)
        assert len(graph.edges) > 0


class TestDeterminism:
    def test_same_seed_same_graph(self):
        config = _make_config(connectivity_level=2)
        graph1 = build_entity_graph(config, SeedManager(42))
        graph2 = build_entity_graph(config, SeedManager(42))
        assert len(graph1.nodes) == len(graph2.nodes)
        assert len(graph1.edges) == len(graph2.edges)
        ids1 = sorted(n.id for n in graph1.nodes)
        ids2 = sorted(n.id for n in graph2.nodes)
        assert ids1 == ids2

    def test_different_seed_different_graph(self):
        config = _make_config(connectivity_level=2)
        graph1 = build_entity_graph(config, SeedManager(42))
        graph2 = build_entity_graph(config, SeedManager(99))
        ids1 = sorted(n.id for n in graph1.nodes)
        ids2 = sorted(n.id for n in graph2.nodes)
        # Different seeds should produce different entity selections
        assert ids1 != ids2


class TestNetworkXRoundTrip:
    def test_round_trip_preserves_nodes(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        nx_graph = graph.to_networkx()
        restored = EntityGraph.from_networkx(nx_graph)
        assert len(restored.nodes) == len(graph.nodes)

    def test_round_trip_preserves_edges(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        nx_graph = graph.to_networkx()
        restored = EntityGraph.from_networkx(nx_graph)
        assert len(restored.edges) == len(graph.edges)

    def test_round_trip_preserves_attributes(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        nx_graph = graph.to_networkx()
        restored = EntityGraph.from_networkx(nx_graph)
        original_by_id = {n.id: n for n in graph.nodes}
        for node in restored.nodes:
            orig = original_by_id[node.id]
            assert node.entity_type == orig.entity_type
            assert node.canonical_name == orig.canonical_name
            assert sorted(node.subcorpus_memberships) == sorted(orig.subcorpus_memberships)


class TestScaling:
    def test_more_subcorpora_more_entities(self):
        small = build_entity_graph(_make_config(subcorpora_count=2), SeedManager(42))
        large = build_entity_graph(_make_config(subcorpora_count=8), SeedManager(42))
        assert len(large.nodes) >= len(small.nodes)

    def test_entity_types_present(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        types = {n.entity_type for n in graph.nodes}
        assert "organization" in types
        assert "equipment" in types
        assert "regulation" in types


class TestEdgeConstraints:
    def test_edges_only_between_shared_subcorpus(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        node_map = {n.id: n for n in graph.nodes}
        for edge in graph.edges:
            src = node_map[edge.source]
            tgt = node_map[edge.target]
            shared = set(src.subcorpus_memberships) & set(tgt.subcorpus_memberships)
            assert len(shared) > 0, (
                f"Edge {edge.source}→{edge.target} has no shared subcorpus"
            )

    def test_edges_have_valid_relationship_types(self, seed_mgr):
        config = _make_config(connectivity_level=2)
        graph = build_entity_graph(config, seed_mgr)
        valid_rels = {
            "manufactures", "operates", "regulated_by", "issued_by",
            "headquartered_in", "operates_from", "certified_under", "employs",
        }
        for edge in graph.edges:
            assert edge.relationship_type in valid_rels, (
                f"Unknown relationship: {edge.relationship_type}"
            )
