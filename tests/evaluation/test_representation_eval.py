"""Tests for Layer 1 representation quality evaluation."""

import pytest

from crossfire.evaluation.representation_eval import score_representation
from crossfire.shared.schemas.entities import EntityEdge, EntityGraph, EntityNode


def _gold_graph():
    """Gold graph with 3 entities (1 with aliases) and 2 edges."""
    return EntityGraph(
        nodes=[
            EntityNode(
                id="gold_e1",
                entity_type="company",
                canonical_name="Acme Corp",
                aliases=["ACME", "Acme Corporation"],
                subcorpus_memberships=["sc-0"],
            ),
            EntityNode(
                id="gold_e2",
                entity_type="equipment",
                canonical_name="Engine Model X",
                aliases=[],
                subcorpus_memberships=["sc-0"],
            ),
            EntityNode(
                id="gold_e3",
                entity_type="location",
                canonical_name="Denver",
                aliases=["DEN"],
                subcorpus_memberships=["sc-1"],
            ),
        ],
        edges=[
            EntityEdge(
                source="gold_e1", target="gold_e2", relationship_type="manufactured"
            ),
            EntityEdge(
                source="gold_e1", target="gold_e3", relationship_type="located_in"
            ),
        ],
    )


class TestRepresentationPerfectMatch:
    """System graph perfectly matches gold graph."""

    def test_perfect_scores(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="sys_001",
                    entity_type="company",
                    canonical_name="Acme Corp",
                    aliases=["ACME", "Acme Corporation"],
                ),
                EntityNode(
                    id="sys_002",
                    entity_type="equipment",
                    canonical_name="Engine Model X",
                ),
                EntityNode(
                    id="sys_003",
                    entity_type="location",
                    canonical_name="Denver",
                    aliases=["DEN"],
                ),
            ],
            edges=[
                EntityEdge(
                    source="sys_001",
                    target="sys_002",
                    relationship_type="manufactured",
                ),
                EntityEdge(
                    source="sys_001",
                    target="sys_003",
                    relationship_type="located_in",
                ),
            ],
        )
        result = score_representation(system, gold)
        rq = result.representation_quality
        assert rq is not None
        assert rq.entity_coverage == 1.0
        assert rq.relationship_accuracy == 1.0
        assert rq.entity_resolution_quality == 1.0

    def test_returns_evaluation_result(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(id="s1", entity_type="company", canonical_name="Acme Corp"),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality is not None
        # Layer 1 doesn't set detection metrics
        assert result.overall_precision == 0.0


class TestEntityCoverage:
    """Entity coverage metric."""

    def test_partial_coverage(self):
        gold = _gold_graph()
        # System only has 2 of 3 gold entities
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.entity_coverage == pytest.approx(2 / 3)

    def test_coverage_via_alias(self):
        gold = _gold_graph()
        # System knows "ACME" (alias) not "Acme Corp" (canonical)
        system = EntityGraph(
            nodes=[
                EntityNode(id="s1", entity_type="company", canonical_name="ACME"),
            ],
        )
        result = score_representation(system, gold)
        # "acme" matches gold alias → gold_e1 covered
        assert result.representation_quality.entity_coverage == pytest.approx(1 / 3)

    def test_case_insensitive(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="acme corp"
                ),
                EntityNode(
                    id="s2",
                    entity_type="equipment",
                    canonical_name="engine model x",
                ),
                EntityNode(
                    id="s3", entity_type="location", canonical_name="denver"
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.entity_coverage == 1.0


class TestRelationshipAccuracy:
    """Relationship accuracy metric."""

    def test_all_correct_edges(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
            ],
            edges=[
                EntityEdge(
                    source="s1", target="s2", relationship_type="manufactured"
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.relationship_accuracy == 1.0

    def test_wrong_relationship_type(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
            ],
            edges=[
                EntityEdge(
                    source="s1", target="s2", relationship_type="wrong_type"
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.relationship_accuracy == 0.0

    def test_mixed_correct_and_wrong(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
                EntityNode(
                    id="s3", entity_type="location", canonical_name="Denver"
                ),
            ],
            edges=[
                EntityEdge(
                    source="s1", target="s2", relationship_type="manufactured"
                ),  # correct
                EntityEdge(
                    source="s2", target="s3", relationship_type="invented"
                ),  # wrong
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.relationship_accuracy == pytest.approx(0.5)

    def test_undirected_edge_matching(self):
        gold = _gold_graph()
        # System has reversed direction — should still match (undirected)
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
            ],
            edges=[
                EntityEdge(
                    source="s2", target="s1", relationship_type="manufactured"
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.relationship_accuracy == 1.0


class TestEntityResolutionQuality:
    """Entity resolution quality metric."""

    def test_all_aliases_resolved(self):
        gold = _gold_graph()
        # System merges all aliases under one entity
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1",
                    entity_type="company",
                    canonical_name="Acme Corp",
                    aliases=["ACME", "Acme Corporation"],
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
                EntityNode(
                    id="s3",
                    entity_type="location",
                    canonical_name="Denver",
                    aliases=["DEN"],
                ),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.entity_resolution_quality == 1.0

    def test_aliases_split_into_separate_entities(self):
        gold = _gold_graph()  # gold_e1 has aliases ["ACME", "Acme Corporation"]
        # System splits: "Acme Corp" and "ACME" are different entities
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
                EntityNode(id="s2", entity_type="company", canonical_name="ACME"),
                EntityNode(
                    id="s3",
                    entity_type="company",
                    canonical_name="Acme Corporation",
                ),
                EntityNode(
                    id="s4", entity_type="location", canonical_name="Denver"
                ),
                EntityNode(id="s5", entity_type="location", canonical_name="DEN"),
            ],
        )
        result = score_representation(system, gold)
        # gold_e1 aliases: "ACME" -> s2 (!=s1), "Acme Corporation" -> s3 (!=s1) → 0 resolved
        # gold_e3 alias: "DEN" -> s5 (!=s4) → 0 resolved
        # total aliases = 3, resolved = 0
        assert result.representation_quality.entity_resolution_quality == 0.0

    def test_partial_resolution(self):
        gold = _gold_graph()  # gold_e1: ["ACME", "Acme Corporation"], gold_e3: ["DEN"]
        # System resolves ACME with Acme Corp, but not Acme Corporation
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1",
                    entity_type="company",
                    canonical_name="Acme Corp",
                    aliases=["ACME"],
                ),
                EntityNode(
                    id="s2",
                    entity_type="company",
                    canonical_name="Acme Corporation",
                ),
                EntityNode(
                    id="s3",
                    entity_type="location",
                    canonical_name="Denver",
                    aliases=["DEN"],
                ),
            ],
        )
        result = score_representation(system, gold)
        # gold_e1: "ACME" -> s1 (same as canonical "Acme Corp"->s1) ✓
        #          "Acme Corporation" -> s2 (!=s1) ✗
        # gold_e3: "DEN" -> s3 (same as canonical "Denver"->s3) ✓
        # resolved = 2 / 3 total aliases
        assert result.representation_quality.entity_resolution_quality == pytest.approx(
            2 / 3
        )

    def test_no_aliases_vacuous_truth(self):
        gold = EntityGraph(
            nodes=[
                EntityNode(
                    id="g1",
                    entity_type="company",
                    canonical_name="Acme",
                    aliases=[],
                ),
            ],
        )
        system = EntityGraph(
            nodes=[
                EntityNode(id="s1", entity_type="company", canonical_name="Acme"),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.entity_resolution_quality == 1.0


class TestRepresentationEdgeCases:
    """Edge cases: empty graphs."""

    def test_both_empty(self):
        result = score_representation(EntityGraph(), EntityGraph())
        rq = result.representation_quality
        assert rq.entity_coverage == 0.0
        assert rq.relationship_accuracy == 0.0
        assert rq.entity_resolution_quality == 0.0

    def test_empty_system(self):
        gold = _gold_graph()
        result = score_representation(EntityGraph(), gold)
        assert result.representation_quality.entity_coverage == 0.0
        assert result.representation_quality.entity_resolution_quality == 0.0

    def test_empty_gold(self):
        system = EntityGraph(
            nodes=[
                EntityNode(id="s1", entity_type="company", canonical_name="Acme"),
            ],
            edges=[
                EntityEdge(source="s1", target="s1", relationship_type="self"),
            ],
        )
        result = score_representation(system, EntityGraph())
        assert result.representation_quality.entity_coverage == 0.0
        # No gold edges, system has edges → accuracy = 0.0 (no matches possible)
        assert result.representation_quality.relationship_accuracy == 0.0

    def test_no_edges_either_graph(self):
        gold = EntityGraph(
            nodes=[
                EntityNode(
                    id="g1", entity_type="company", canonical_name="Acme"
                ),
            ],
        )
        system = EntityGraph(
            nodes=[
                EntityNode(id="s1", entity_type="company", canonical_name="Acme"),
            ],
        )
        result = score_representation(system, gold)
        assert result.representation_quality.entity_coverage == 1.0
        # No system edges, no gold edges → vacuous truth (no wrong claims)
        assert result.representation_quality.relationship_accuracy == 1.0


class TestRepresentationIndependence:
    """Layer 1 is independent from Layer 2 — no PipelineReport needed."""

    def test_no_pipeline_report_dependency(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1", entity_type="company", canonical_name="Acme Corp"
                ),
            ],
        )
        # This call should work without any PipelineReport
        result = score_representation(system, gold)
        assert result.representation_quality is not None
        assert result.per_scope == []
        assert result.per_stage == []


class TestRepresentationDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self):
        gold = _gold_graph()
        system = EntityGraph(
            nodes=[
                EntityNode(
                    id="s1",
                    entity_type="company",
                    canonical_name="Acme Corp",
                    aliases=["ACME"],
                ),
                EntityNode(
                    id="s2", entity_type="equipment", canonical_name="Engine Model X"
                ),
            ],
            edges=[
                EntityEdge(
                    source="s1", target="s2", relationship_type="manufactured"
                ),
            ],
        )
        r1 = score_representation(system, gold)
        r2 = score_representation(system, gold)
        assert r1 == r2
