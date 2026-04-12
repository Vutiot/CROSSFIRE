"""Tests for per-stage evaluation breakdown."""

import pytest

from crossfire.evaluation.stage_breakdown import DETECTABILITY_TO_STAGE, score_by_stage
from crossfire.shared.schemas.contradictions import ContradictionLabel
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport


def _make_report(detections):
    return PipelineReport(
        pipeline_mode="hybrid",
        case_dir="/test",
        detections=detections,
        timestamp="2026-04-06T00:00:00",
    )


class TestStagePerfectMatch:
    """All detections match all gold labels — each stage scored."""

    def test_per_stage_scores(self, sample_gold_labels, perfect_report):
        result = score_by_stage(perfect_report, sample_gold_labels)
        assert len(result.per_stage) == 3
        stage_map = {sr.stage: sr for sr in result.per_stage}
        for stage in ["contradiction_detection", "cross_reference_identification", "claim_extraction"]:
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
        assert DETECTABILITY_TO_STAGE["single_hop"] == "claim_extraction"
        assert DETECTABILITY_TO_STAGE["multi_hop"] == "cross_reference_identification"
        assert DETECTABILITY_TO_STAGE["entity_resolution_dependent"] == "contradiction_detection"


class TestStageNonCascading:
    """Missing detections in one stage doesn't affect other stages."""

    def test_miss_entity_resolution_scanning_unaffected(self, sample_gold_labels):
        # Only match the single_hop gold label (scanning stage)
        # gold_001 = single_hop (doc_A, doc_B) -> scanning
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["doc_A", "doc_B"],
                    text_span_start=0,
                    text_span_end=20,
                    evidence_text="speed mismatch",
                    confidence=0.9,
                    description="speed mismatch",
                ),
            ]
        )
        result = score_by_stage(report, sample_gold_labels)
        stage_map = {sr.stage: sr for sr in result.per_stage}

        # scanning: 1 match / 1 gold -> recall=1.0, precision=1.0
        assert stage_map["claim_extraction"].recall == 1.0
        assert stage_map["claim_extraction"].precision == 1.0
        assert stage_map["claim_extraction"].f1 == 1.0

        # entity_resolution: 0 matches -> recall=0.0
        assert stage_map["contradiction_detection"].recall == 0.0
        assert stage_map["contradiction_detection"].f1 == 0.0

        # graph_construction: 0 matches -> recall=0.0
        assert stage_map["cross_reference_identification"].recall == 0.0
        assert stage_map["cross_reference_identification"].f1 == 0.0


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
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="orphan",
                    confidence=0.9,
                    description="orphan",
                ),
            ]
        )
        result = score_by_stage(report, [])
        assert result.per_stage == []

    def test_single_stage_only(self):
        # All gold labels are single_hop -> only scanning stage
        gold = [
            ContradictionLabel(
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                difficulty="easy",
                char_start=0,
                char_end=10,
                original_text="y",
                modified_text="x",
                rationale="test",
                ground_truth=True,
                document_references=["a", "b"],
            ),
            ContradictionLabel(
                scope="inter_doc",
                mechanism="entity_swap",
                detectability="single_hop",
                system_affinity="graph_favoring",
                difficulty="medium",
                char_start=0,
                char_end=10,
                original_text="n",
                modified_text="m",
                rationale="test2",
                ground_truth=True,
                document_references=["c", "d"],
            ),
        ]
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="first",
                    confidence=0.9,
                    description="first",
                ),
                DetectedContradiction(
                    scope="inter_doc",
                    document_references=["c", "d"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="second",
                    confidence=0.8,
                    description="second",
                ),
            ]
        )
        result = score_by_stage(report, gold)
        assert len(result.per_stage) == 1
        assert result.per_stage[0].stage == "claim_extraction"
        assert result.per_stage[0].recall == 1.0
        assert result.per_stage[0].precision == 1.0


class TestStageFR19Contingency:
    """FR19: no multi_hop gold -> no graph_construction stage."""

    def test_no_graph_construction_stage(self):
        gold = [
            ContradictionLabel(
                scope="intra_doc",
                mechanism="numeric_drift",
                detectability="single_hop",
                system_affinity="balanced",
                difficulty="easy",
                char_start=0,
                char_end=10,
                original_text="y",
                modified_text="x",
                rationale="test",
                ground_truth=True,
                document_references=["a", "b"],
            ),
            ContradictionLabel(
                scope="inter_doc",
                mechanism="temporal_contradiction",
                detectability="entity_resolution_dependent",
                system_affinity="agentic_favoring",
                difficulty="hard",
                char_start=0,
                char_end=10,
                original_text="n",
                modified_text="m",
                rationale="test2",
                ground_truth=True,
                document_references=["c", "d"],
            ),
        ]
        report = _make_report(
            [
                DetectedContradiction(
                    scope="intra_doc",
                    document_references=["a", "b"],
                    text_span_start=0,
                    text_span_end=10,
                    evidence_text="first",
                    confidence=0.9,
                    description="first",
                ),
            ]
        )
        result = score_by_stage(report, gold)
        stage_names = [sr.stage for sr in result.per_stage]
        assert "cross_reference_identification" not in stage_names
        assert "claim_extraction" in stage_names
        assert "contradiction_detection" in stage_names


class TestStageDeterminism:
    """Same inputs always produce identical results."""

    def test_deterministic(self, sample_gold_labels, perfect_report):
        r1 = score_by_stage(perfect_report, sample_gold_labels)
        r2 = score_by_stage(perfect_report, sample_gold_labels)
        assert r1 == r2
