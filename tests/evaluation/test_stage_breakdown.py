"""Tests for per-stage evaluation breakdown."""

import pytest

from crossfire.evaluation.stage_breakdown import DETECTABILITY_TO_STAGE, score_by_stage
from crossfire.shared.schemas.incoherences import IncoherenceLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        corpus_path="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestStagePerfectMatch:
    """All detections match all gold labels — each stage scored."""

    def test_per_stage_scores(self, sample_gold_labels, perfect_report):
        result = score_by_stage(perfect_report, sample_gold_labels)
        assert len(result.per_stage) == 3
        stage_map = {sr.stage: sr for sr in result.per_stage}
        # Each stage has 1 gold label; all 3 detections tried against each stage's 1 gold
        for stage in ["entity_resolution", "graph_construction", "scanning"]:
            assert stage in stage_map
            assert stage_map[stage].recall == 1.0

    def test_overall_metrics(self, sample_gold_labels, perfect_report):
        result = score_by_stage(perfect_report, sample_gold_labels)
        assert result.overall_precision == 1.0
        assert result.overall_recall == 1.0
        assert result.overall_f1 == 1.0

    def test_stage_names_sorted(self, sample_gold_labels, perfect_report):
        result = score_by_stage(perfect_report, sample_gold_labels)
        stage_names = [sr.stage for sr in result.per_stage]
        assert stage_names == sorted(stage_names)


class TestStageMapping:
    """Detectability-to-stage mapping is correct."""

    def test_mapping_values(self):
        assert DETECTABILITY_TO_STAGE["single_hop"] == "scanning"
        assert DETECTABILITY_TO_STAGE["multi_hop"] == "graph_construction"
        assert DETECTABILITY_TO_STAGE["entity_resolution_dependent"] == "entity_resolution"


class TestStageNonCascading:
    """Missing detections in one stage doesn't affect other stages."""

    def test_miss_entity_resolution_scanning_unaffected(self, sample_gold_labels):
        # Only match the single_hop gold label (scanning stage)
        # gold_001 = single_hop (doc_A, doc_B) → scanning
        report = _make_report(
            [
                DetectedIncoherence(
                    id="det_001",
                    evidence_references=["doc_A", "doc_B"],
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_by_stage(report, sample_gold_labels)
        stage_map = {sr.stage: sr for sr in result.per_stage}

        # scanning: 1 match / 1 gold → recall=1.0, precision=1.0
        assert stage_map["scanning"].recall == 1.0
        assert stage_map["scanning"].precision == 1.0
        assert stage_map["scanning"].f1 == 1.0

        # entity_resolution: 0 matches → recall=0.0
        assert stage_map["entity_resolution"].recall == 0.0
        assert stage_map["entity_resolution"].f1 == 0.0

        # graph_construction: 0 matches → recall=0.0
        assert stage_map["graph_construction"].recall == 0.0
        assert stage_map["graph_construction"].f1 == 0.0


class TestStageEdgeCases:
    """Edge cases: empty report, empty gold, single stage."""

    def test_empty_report(self, sample_gold_labels, empty_report):
        result = score_by_stage(empty_report, sample_gold_labels)
        assert len(result.per_stage) == 3
        for sr in result.per_stage:
            assert sr.precision == 0.0
            assert sr.recall == 0.0
            assert sr.f1 == 0.0

    def test_empty_gold(self):
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="orphan",
                ),
            ]
        )
        result = score_by_stage(report, [])
        assert result.per_stage == []

    def test_single_stage_only(self):
        # All gold labels are single_hop → only scanning stage
        gold = [
            IncoherenceLabel(
                id="g1",
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=["a", "b"],
                modified_fact="x",
                original_fact="y",
            ),
            IncoherenceLabel(
                id="g2",
                scope="intra_corpus",
                mechanism="entity_swap",
                detectability="single_hop",
                system_affinity="graph_favoring",
                document_references=["c", "d"],
                modified_fact="m",
                original_fact="n",
            ),
        ]
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="first",
                ),
                DetectedIncoherence(
                    id="d2",
                    evidence_references=["c", "d"],
                    confidence=0.8,
                    description="second",
                ),
            ]
        )
        result = score_by_stage(report, gold)
        assert len(result.per_stage) == 1
        assert result.per_stage[0].stage == "scanning"
        assert result.per_stage[0].recall == 1.0
        assert result.per_stage[0].precision == 1.0


class TestStageFR19Contingency:
    """FR19: no multi_hop gold → no graph_construction stage."""

    def test_no_graph_construction_stage(self):
        gold = [
            IncoherenceLabel(
                id="g1",
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=["a", "b"],
                modified_fact="x",
                original_fact="y",
            ),
            IncoherenceLabel(
                id="g2",
                scope="inter_corpus",
                mechanism="temporal_contradiction",
                detectability="entity_resolution_dependent",
                system_affinity="agentic_favoring",
                document_references=["c", "d"],
                modified_fact="m",
                original_fact="n",
            ),
        ]
        report = _make_report(
            [
                DetectedIncoherence(
                    id="d1",
                    evidence_references=["a", "b"],
                    confidence=0.9,
                    description="first",
                ),
            ]
        )
        result = score_by_stage(report, gold)
        stage_names = [sr.stage for sr in result.per_stage]
        assert "graph_construction" not in stage_names
        assert "scanning" in stage_names
        assert "entity_resolution" in stage_names


class TestStageDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self, sample_gold_labels, perfect_report):
        r1 = score_by_stage(perfect_report, sample_gold_labels)
        r2 = score_by_stage(perfect_report, sample_gold_labels)
        assert r1 == r2
