"""Tests for all Pydantic schema models in crossfire.shared.schemas."""

import json

import pytest
from pydantic import ValidationError

from crossfire.shared.schemas.anonymization import AnonymizationMapping
from crossfire.shared.schemas.config import (
    DatasetVersion,
    GenerationParams,
    PipelineConfig,
)
from crossfire.shared.schemas.contradictions import ContradictionLabel, DistractorLabel
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.domain_registry import DomainEntry, DomainRegistry
from crossfire.shared.schemas.evaluation import (
    AggregatedResult,
    EvaluationResult,
    MetricStats,
    RepresentationQualityResult,
    ScopeResult,
    StageResult,
)
from crossfire.shared.schemas.knowledge_graph import CrossReference, KnowledgeGraphClaim
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.schemas.scope_map import ScopeMap, ScopeMapEntry


# ---------------------------------------------------------------------------
# ContradictionLabel
# ---------------------------------------------------------------------------
class TestContradictionLabel:
    def _make(self, **overrides):
        defaults = dict(
            scope="intra_doc",
            mechanism="entity_swap",
            detectability="multi_hop",
            system_affinity="balanced",
            difficulty="medium",
            char_start=10,
            char_end=50,
            original_text="The Boeing 737 was manufactured in 2015.",
            modified_text="The Boeing 737 was manufactured in 2019.",
            rationale="Date changed to create numeric contradiction.",
            ground_truth=True,
            document_references=["doc-001", "doc-002"],
        )
        defaults.update(overrides)
        return ContradictionLabel(**defaults)

    def test_create(self):
        label = self._make()
        assert label.scope == "intra_doc"
        assert label.mechanism == "entity_swap"
        assert label.difficulty == "medium"
        assert label.ground_truth is True
        assert len(label.document_references) == 2

    def test_round_trip(self):
        label = self._make(scope="inter_doc", mechanism="temporal_contradiction")
        json_str = label.model_dump_json()
        restored = ContradictionLabel.model_validate_json(json_str)
        assert label == restored

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        expected_keys = {
            "scope", "mechanism", "detectability", "system_affinity",
            "difficulty", "char_start", "char_end", "original_text",
            "modified_text", "rationale", "ground_truth", "document_references",
        }
        assert expected_keys == set(data.keys())

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            self._make(scope="invalid")

    def test_invalid_mechanism(self):
        with pytest.raises(ValidationError):
            self._make(mechanism="invalid_mech")

    def test_invalid_detectability(self):
        with pytest.raises(ValidationError):
            self._make(detectability="invalid")

    def test_invalid_system_affinity(self):
        with pytest.raises(ValidationError):
            self._make(system_affinity="invalid")

    def test_invalid_difficulty(self):
        with pytest.raises(ValidationError):
            self._make(difficulty="invalid")

    def test_negative_char_start(self):
        with pytest.raises(ValidationError):
            self._make(char_start=-1)

    def test_negative_char_end(self):
        with pytest.raises(ValidationError):
            self._make(char_end=-1)

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            ContradictionLabel(scope="intra_doc")

    @pytest.mark.parametrize("scope", ["intra_doc", "inter_doc"])
    def test_all_scopes(self, scope):
        label = self._make(scope=scope)
        assert label.scope == scope

    @pytest.mark.parametrize("mechanism", [
        "numeric_drift", "entity_swap", "causal_inversion",
        "temporal_contradiction", "omission_based_implicit", "temporal_revision_conflict",
    ])
    def test_all_mechanisms(self, mechanism):
        label = self._make(mechanism=mechanism)
        assert label.mechanism == mechanism

    @pytest.mark.parametrize("detectability", [
        "single_hop", "multi_hop", "entity_resolution_dependent",
    ])
    def test_all_detectabilities(self, detectability):
        label = self._make(detectability=detectability)
        assert label.detectability == detectability

    @pytest.mark.parametrize("affinity", ["balanced", "graph_favoring", "agentic_favoring"])
    def test_all_system_affinities(self, affinity):
        label = self._make(system_affinity=affinity)
        assert label.system_affinity == affinity

    @pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
    def test_all_difficulties(self, difficulty):
        label = self._make(difficulty=difficulty)
        assert label.difficulty == difficulty


# ---------------------------------------------------------------------------
# DistractorLabel
# ---------------------------------------------------------------------------
class TestDistractorLabel:
    def _make(self, **overrides):
        defaults = dict(
            scope="intra_doc",
            divergence_type="expert_opinion",
            document_references=["doc-001", "doc-003"],
            description="Two experts disagree on failure cause.",
        )
        defaults.update(overrides)
        return DistractorLabel(**defaults)

    def test_create(self):
        dl = self._make()
        assert dl.divergence_type == "expert_opinion"
        assert len(dl.document_references) == 2

    def test_round_trip(self):
        dl = self._make(scope="inter_doc", divergence_type="preliminary_vs_final")
        json_str = dl.model_dump_json()
        restored = DistractorLabel.model_validate_json(json_str)
        assert dl == restored

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "divergence_type" in data
        assert "document_references" in data

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            self._make(scope="invalid")

    def test_invalid_divergence_type(self):
        with pytest.raises(ValidationError):
            self._make(divergence_type="invalid")

    @pytest.mark.parametrize("div_type", [
        "expert_opinion", "preliminary_vs_final",
        "measurement_methodology", "uncertainty_expression",
    ])
    def test_all_divergence_types(self, div_type):
        dl = self._make(divergence_type=div_type)
        assert dl.divergence_type == div_type


# ---------------------------------------------------------------------------
# KnowledgeGraphClaim
# ---------------------------------------------------------------------------
class TestKnowledgeGraphClaim:
    def _make(self, **overrides):
        defaults = dict(
            claim_id="claim-001",
            subject="Boeing 737",
            predicate="manufactured_by",
            object="Boeing",
            source_document="doc-001",
            confidence=0.95,
        )
        defaults.update(overrides)
        return KnowledgeGraphClaim(**defaults)

    def test_create(self):
        claim = self._make()
        assert claim.claim_id == "claim-001"
        assert claim.confidence == 0.95

    def test_round_trip(self):
        claim = self._make()
        json_str = claim.model_dump_json()
        restored = KnowledgeGraphClaim.model_validate_json(json_str)
        assert claim == restored

    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            self._make(confidence=1.5)

    def test_confidence_too_low(self):
        with pytest.raises(ValidationError):
            self._make(confidence=-0.1)

    def test_confidence_boundaries(self):
        assert self._make(confidence=0.0).confidence == 0.0
        assert self._make(confidence=1.0).confidence == 1.0

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "claim_id" in data
        assert "source_document" in data


# ---------------------------------------------------------------------------
# CrossReference
# ---------------------------------------------------------------------------
class TestCrossReference:
    def _make(self, **overrides):
        defaults = dict(
            reference_id="ref-001",
            source_claim="claim-001",
            target_claim="claim-002",
            relationship="contradicts",
            source_documents=["doc-001", "doc-002"],
        )
        defaults.update(overrides)
        return CrossReference(**defaults)

    def test_create(self):
        ref = self._make()
        assert ref.reference_id == "ref-001"
        assert len(ref.source_documents) == 2

    def test_round_trip(self):
        ref = self._make()
        json_str = ref.model_dump_json()
        restored = CrossReference.model_validate_json(json_str)
        assert ref == restored

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "reference_id" in data
        assert "source_claim" in data
        assert "target_claim" in data
        assert "source_documents" in data


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------
class TestDocument:
    def _make(self, **overrides):
        defaults = dict(
            document_id="doc-001",
            source="ntsb",
            document_type="investigation_report",
            source_case_id="NTSB-2024-001",
            scope_classification="primary",
            content="Report content here.",
        )
        defaults.update(overrides)
        return Document(**defaults)

    def test_create(self):
        doc = self._make()
        assert doc.document_id == "doc-001"
        assert doc.source == "ntsb"
        assert doc.document_type == "investigation_report"
        assert doc.source_case_id == "NTSB-2024-001"

    def test_round_trip(self):
        doc = self._make(document_type="witness_testimony")
        json_str = doc.model_dump_json()
        restored = Document.model_validate_json(json_str)
        assert doc == restored

    def test_source_field(self):
        for src in ["grenfell", "copa", "ntsb"]:
            doc = self._make(source=src)
            assert doc.source == src

    def test_arbitrary_document_type(self):
        doc = self._make(source="grenfell", document_type="hearing_transcript")
        assert doc.document_type == "hearing_transcript"
        doc2 = self._make(source="copa", document_type="tactical_response_report")
        assert doc2.document_type == "tactical_response_report"

    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            Document(document_id="doc-001")

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "document_id" in data
        assert "source" in data
        assert "document_type" in data
        assert "source_case_id" in data
        assert "scope_classification" in data


# ---------------------------------------------------------------------------
# DomainEntry & DomainRegistry
# ---------------------------------------------------------------------------
class TestDomainRegistry:
    def test_create_entry(self):
        entry = DomainEntry(domain="airline", original_value="Delta", anonymized_value="Airline-A")
        assert entry.domain == "airline"

    def test_create_registry(self):
        registry = DomainRegistry(
            case_id="case-001",
            entries=[
                DomainEntry(domain="airline", original_value="Delta", anonymized_value="Airline-A"),
                DomainEntry(domain="airport", original_value="ATL", anonymized_value="Airport-X"),
            ],
        )
        assert registry.case_id == "case-001"
        assert len(registry.entries) == 2

    def test_round_trip(self):
        registry = DomainRegistry(
            case_id="case-001",
            entries=[DomainEntry(domain="airline", original_value="Delta", anonymized_value="Airline-A")],
        )
        json_str = registry.model_dump_json()
        restored = DomainRegistry.model_validate_json(json_str)
        assert registry == restored

    def test_snake_case_keys(self):
        entry = DomainEntry(domain="airline", original_value="Delta", anonymized_value="Airline-A")
        data = json.loads(entry.model_dump_json())
        assert "original_value" in data
        assert "anonymized_value" in data


# ---------------------------------------------------------------------------
# ScopeMapEntry & ScopeMap
# ---------------------------------------------------------------------------
class TestScopeMap:
    def test_create_entry(self):
        entry = ScopeMapEntry(document_id="doc-001", scope_classification="primary")
        assert entry.document_id == "doc-001"

    def test_create_map(self):
        scope_map = ScopeMap(
            case_id="case-001",
            entries=[
                ScopeMapEntry(document_id="doc-001", scope_classification="primary"),
                ScopeMapEntry(document_id="doc-002", scope_classification="secondary"),
            ],
        )
        assert scope_map.case_id == "case-001"
        assert len(scope_map.entries) == 2

    def test_round_trip(self):
        scope_map = ScopeMap(
            case_id="case-001",
            entries=[ScopeMapEntry(document_id="doc-001", scope_classification="primary")],
        )
        json_str = scope_map.model_dump_json()
        restored = ScopeMap.model_validate_json(json_str)
        assert scope_map == restored

    def test_snake_case_keys(self):
        entry = ScopeMapEntry(document_id="doc-001", scope_classification="primary")
        data = json.loads(entry.model_dump_json())
        assert "document_id" in data
        assert "scope_classification" in data


# ---------------------------------------------------------------------------
# AnonymizationMapping
# ---------------------------------------------------------------------------
class TestAnonymizationMapping:
    def test_create(self):
        mapping = AnonymizationMapping(original="John Doe", anonymized="Person-A", entity_type="person")
        assert mapping.original == "John Doe"
        assert mapping.entity_type == "person"

    def test_round_trip(self):
        mapping = AnonymizationMapping(original="Delta Airlines", anonymized="Airline-A", entity_type="organization")
        json_str = mapping.model_dump_json()
        restored = AnonymizationMapping.model_validate_json(json_str)
        assert mapping == restored

    def test_snake_case_keys(self):
        mapping = AnonymizationMapping(original="x", anonymized="y", entity_type="person")
        data = json.loads(mapping.model_dump_json())
        assert "entity_type" in data


# ---------------------------------------------------------------------------
# PipelineConfig
# ---------------------------------------------------------------------------
class TestPipelineConfig:
    def test_create(self):
        pc = PipelineConfig(mode="hybrid", case_dir="/data/case-001")
        assert pc.mode == "hybrid"
        assert pc.case_dir == "/data/case-001"
        assert pc.output_dir == "output/reports"

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            PipelineConfig(mode="invalid", case_dir="/data/case")

    def test_round_trip(self):
        pc = PipelineConfig(mode="agentic", case_dir="/data/case", output_dir="/tmp/reports")
        json_str = pc.model_dump_json()
        restored = PipelineConfig.model_validate_json(json_str)
        assert pc == restored

    def test_snake_case_keys(self):
        data = json.loads(PipelineConfig(mode="hybrid", case_dir="/data").model_dump_json())
        assert "case_dir" in data
        assert "output_dir" in data

    @pytest.mark.parametrize("mode", ["hybrid", "agentic", "graph_native"])
    def test_all_modes(self, mode):
        pc = PipelineConfig(mode=mode, case_dir="/data")
        assert pc.mode == mode


# ---------------------------------------------------------------------------
# DatasetVersion
# ---------------------------------------------------------------------------
class TestDatasetVersion:
    def test_create(self):
        dv = DatasetVersion(version_id="v1.0")
        assert dv.version_id == "v1.0"
        assert dv.base_version is None
        assert dv.label_corrections == []

    def test_with_base_version(self):
        dv = DatasetVersion(version_id="v1.1", base_version="v1.0", label_corrections=["fix-001"])
        assert dv.base_version == "v1.0"
        assert len(dv.label_corrections) == 1

    def test_round_trip(self):
        dv = DatasetVersion(version_id="v2.0", base_version="v1.0", label_corrections=["a", "b"])
        json_str = dv.model_dump_json()
        restored = DatasetVersion.model_validate_json(json_str)
        assert dv == restored

    def test_snake_case_keys(self):
        data = json.loads(DatasetVersion(version_id="v1").model_dump_json())
        assert "version_id" in data
        assert "base_version" in data
        assert "label_corrections" in data

    def test_defaults(self):
        data = json.loads(DatasetVersion(version_id="v1").model_dump_json())
        assert data["base_version"] is None
        assert data["label_corrections"] == []


# ---------------------------------------------------------------------------
# GenerationParams
# ---------------------------------------------------------------------------
class TestGenerationParams:
    def _make(self, **overrides):
        defaults = dict(
            version_id="v1.0",
            contradiction_rate_intra_doc=0.15,
            contradiction_rate_inter_doc=0.10,
            distractor_ratio=0.3,
        )
        defaults.update(overrides)
        return GenerationParams(**defaults)

    def test_create(self):
        gp = self._make()
        assert gp.version_id == "v1.0"
        assert gp.contradiction_rate_intra_doc == 0.15
        assert gp.distractor_ratio == 0.3

    def test_with_distributions(self):
        gp = self._make(
            mechanism_distribution={"numeric_drift": 0.4, "entity_swap": 0.6},
            difficulty_distribution={"easy": 0.3, "medium": 0.5, "hard": 0.2},
        )
        assert gp.mechanism_distribution["numeric_drift"] == 0.4
        assert gp.difficulty_distribution["hard"] == 0.2

    def test_round_trip(self):
        gp = self._make(
            base_version="v0.9",
            mechanism_distribution={"numeric_drift": 1.0},
        )
        json_str = gp.model_dump_json()
        restored = GenerationParams.model_validate_json(json_str)
        assert gp == restored

    def test_defaults(self):
        gp = self._make()
        assert gp.base_version is None
        assert gp.mechanism_distribution == {}
        assert gp.difficulty_distribution == {}

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "version_id" in data
        assert "contradiction_rate_intra_doc" in data
        assert "contradiction_rate_inter_doc" in data
        assert "distractor_ratio" in data
        assert "mechanism_distribution" in data
        assert "difficulty_distribution" in data


# ---------------------------------------------------------------------------
# DetectedContradiction
# ---------------------------------------------------------------------------
class TestDetectedContradiction:
    def _make(self, **overrides):
        defaults = dict(
            scope="intra_doc",
            document_references=["doc-001", "doc-002"],
            text_span_start=100,
            text_span_end=200,
            evidence_text="Conflicting dates for incident.",
            confidence=0.87,
            description="Numeric drift in date field.",
        )
        defaults.update(overrides)
        return DetectedContradiction(**defaults)

    def test_create(self):
        dc = self._make()
        assert dc.confidence == 0.87
        assert dc.scope == "intra_doc"
        assert len(dc.document_references) == 2

    def test_round_trip(self):
        dc = self._make(scope="inter_doc")
        json_str = dc.model_dump_json()
        restored = DetectedContradiction.model_validate_json(json_str)
        assert dc == restored

    def test_confidence_too_high(self):
        with pytest.raises(ValidationError):
            self._make(confidence=1.5)

    def test_confidence_too_low(self):
        with pytest.raises(ValidationError):
            self._make(confidence=-0.1)

    def test_confidence_boundaries(self):
        assert self._make(confidence=0.0).confidence == 0.0
        assert self._make(confidence=1.0).confidence == 1.0

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            self._make(scope="invalid")

    def test_snake_case_keys(self):
        data = json.loads(self._make().model_dump_json())
        assert "text_span_start" in data
        assert "text_span_end" in data
        assert "evidence_text" in data
        assert "document_references" in data


# ---------------------------------------------------------------------------
# PipelineReport
# ---------------------------------------------------------------------------
class TestPipelineReport:
    def test_create(self):
        report = PipelineReport(
            pipeline_mode="hybrid",
            case_dir="/data/case-001",
            detections=[
                DetectedContradiction(
                    scope="intra_doc", document_references=["doc-1"],
                    text_span_start=0, text_span_end=50,
                    evidence_text="conflict", confidence=0.9, description="desc",
                ),
            ],
            timestamp="2026-04-10T12:00:00",
        )
        assert report.pipeline_mode == "hybrid"
        assert len(report.detections) == 1

    def test_empty_detections(self):
        report = PipelineReport(
            pipeline_mode="agentic",
            case_dir="/data/case",
            timestamp="2026-04-10T12:00:00",
        )
        assert report.detections == []
        assert report.run_metadata == {}

    def test_with_run_metadata(self):
        report = PipelineReport(
            pipeline_mode="hybrid",
            case_dir="/data/case",
            timestamp="2026-04-10T12:00:00",
            run_metadata={"total_tokens": 15000, "duration_seconds": 120.5},
        )
        assert report.run_metadata["total_tokens"] == 15000

    def test_round_trip(self):
        report = PipelineReport(
            pipeline_mode="graph_native",
            case_dir="/data/case",
            detections=[
                DetectedContradiction(
                    scope="inter_doc", document_references=["doc-1", "doc-2"],
                    text_span_start=10, text_span_end=100,
                    evidence_text="x", confidence=0.75, description="y",
                ),
            ],
            timestamp="2026-04-10T12:00:00",
            run_metadata={"key": "value"},
        )
        json_str = report.model_dump_json()
        restored = PipelineReport.model_validate_json(json_str)
        assert report == restored

    def test_snake_case_keys(self):
        report = PipelineReport(
            pipeline_mode="hybrid", case_dir="/data", timestamp="t",
            run_metadata={"k": "v"},
        )
        data = json.loads(report.model_dump_json())
        assert "pipeline_mode" in data
        assert "case_dir" in data
        assert "run_metadata" in data


# ---------------------------------------------------------------------------
# ScopeResult
# ---------------------------------------------------------------------------
class TestScopeResult:
    def test_create(self):
        sr = ScopeResult(scope="intra_doc", precision=0.8, recall=0.7, f1=0.75, partial_credit_score=0.82)
        assert sr.scope == "intra_doc"
        assert sr.f1 == 0.75

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            ScopeResult(scope="invalid", precision=0.8, recall=0.7, f1=0.75, partial_credit_score=0.8)

    def test_round_trip(self):
        sr = ScopeResult(scope="inter_doc", precision=0.6, recall=0.5, f1=0.55, partial_credit_score=0.65)
        json_str = sr.model_dump_json()
        restored = ScopeResult.model_validate_json(json_str)
        assert sr == restored

    @pytest.mark.parametrize("scope", ["intra_doc", "inter_doc"])
    def test_all_scopes(self, scope):
        sr = ScopeResult(scope=scope, precision=0.5, recall=0.5, f1=0.5, partial_credit_score=0.5)
        assert sr.scope == scope


# ---------------------------------------------------------------------------
# StageResult
# ---------------------------------------------------------------------------
class TestStageResult:
    def test_create(self):
        st = StageResult(stage="claim_extraction", precision=0.9, recall=0.85, f1=0.87)
        assert st.stage == "claim_extraction"

    def test_invalid_stage(self):
        with pytest.raises(ValidationError):
            StageResult(stage="invalid_stage", precision=0.5, recall=0.5, f1=0.5)

    def test_round_trip(self):
        st = StageResult(stage="contradiction_detection", precision=0.7, recall=0.6, f1=0.65)
        json_str = st.model_dump_json()
        restored = StageResult.model_validate_json(json_str)
        assert st == restored

    @pytest.mark.parametrize("stage", [
        "claim_extraction", "cross_reference_identification", "contradiction_detection",
    ])
    def test_all_stages(self, stage):
        st = StageResult(stage=stage, precision=0.5, recall=0.5, f1=0.5)
        assert st.stage == stage


# ---------------------------------------------------------------------------
# RepresentationQualityResult
# ---------------------------------------------------------------------------
class TestRepresentationQualityResult:
    def test_create(self):
        rq = RepresentationQualityResult(claim_coverage=0.85, cross_reference_accuracy=0.9)
        assert rq.claim_coverage == 0.85
        assert rq.cross_reference_accuracy == 0.9

    def test_round_trip(self):
        rq = RepresentationQualityResult(claim_coverage=0.7, cross_reference_accuracy=0.8)
        json_str = rq.model_dump_json()
        restored = RepresentationQualityResult.model_validate_json(json_str)
        assert rq == restored

    def test_snake_case_keys(self):
        data = json.loads(
            RepresentationQualityResult(claim_coverage=0.5, cross_reference_accuracy=0.5).model_dump_json()
        )
        assert "claim_coverage" in data
        assert "cross_reference_accuracy" in data


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------
class TestEvaluationResult:
    def test_create(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
                ScopeResult(scope="inter_doc", precision=0.7, recall=0.6, f1=0.65, partial_credit_score=0.7),
            ],
            per_stage=[
                StageResult(stage="claim_extraction", precision=0.85, recall=0.8, f1=0.82),
                StageResult(stage="cross_reference_identification", precision=0.75, recall=0.7, f1=0.72),
                StageResult(stage="contradiction_detection", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        assert er.overall_f1 == 0.75
        assert len(er.per_scope) == 2
        assert len(er.per_stage) == 3

    def test_defaults(self):
        er = EvaluationResult(overall_precision=0.5, overall_recall=0.5, overall_f1=0.5)
        assert er.per_scope == []
        assert er.per_stage == []
        assert er.overall_partial_credit_score is None
        assert er.distractor_false_positive_rate is None
        assert er.representation_quality is None

    def test_with_optional_fields(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            overall_partial_credit_score=0.82,
            distractor_false_positive_rate=0.05,
            representation_quality=RepresentationQualityResult(
                claim_coverage=0.9, cross_reference_accuracy=0.85,
            ),
        )
        assert er.overall_partial_credit_score == 0.82
        assert er.distractor_false_positive_rate == 0.05
        assert er.representation_quality.claim_coverage == 0.9

    def test_round_trip(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
            ],
            per_stage=[
                StageResult(stage="claim_extraction", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        json_str = er.model_dump_json()
        restored = EvaluationResult.model_validate_json(json_str)
        assert er == restored

    def test_snake_case_keys(self):
        er = EvaluationResult(
            overall_precision=0.8, overall_recall=0.7, overall_f1=0.75,
            overall_partial_credit_score=0.82,
            distractor_false_positive_rate=0.05,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
            ],
            per_stage=[
                StageResult(stage="claim_extraction", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        data = json.loads(er.model_dump_json())
        assert "overall_precision" in data
        assert "overall_recall" in data
        assert "overall_f1" in data
        assert "overall_partial_credit_score" in data
        assert "distractor_false_positive_rate" in data
        assert "per_scope" in data
        assert "per_stage" in data
        assert "partial_credit_score" in data["per_scope"][0]


# ---------------------------------------------------------------------------
# MetricStats & AggregatedResult
# ---------------------------------------------------------------------------
class TestMetricStats:
    def test_create(self):
        ms = MetricStats(mean=0.8, std=0.05, ci_lower=0.7, ci_upper=0.9)
        assert ms.mean == 0.8
        assert ms.std == 0.05

    def test_round_trip(self):
        ms = MetricStats(mean=0.75, std=0.1, ci_lower=0.65, ci_upper=0.85)
        json_str = ms.model_dump_json()
        restored = MetricStats.model_validate_json(json_str)
        assert ms == restored

    def test_snake_case_keys(self):
        data = json.loads(MetricStats(mean=0.5, std=0.1, ci_lower=0.4, ci_upper=0.6).model_dump_json())
        assert "ci_lower" in data
        assert "ci_upper" in data


class TestAggregatedResult:
    def _make_stats(self):
        return MetricStats(mean=0.8, std=0.05, ci_lower=0.7, ci_upper=0.9)

    def test_create(self):
        ar = AggregatedResult(
            n_seeds=5,
            precision=self._make_stats(),
            recall=self._make_stats(),
            f1=self._make_stats(),
        )
        assert ar.n_seeds == 5
        assert ar.precision.mean == 0.8

    def test_defaults(self):
        ar = AggregatedResult(
            n_seeds=3,
            precision=self._make_stats(),
            recall=self._make_stats(),
            f1=self._make_stats(),
        )
        assert ar.partial_credit_score is None
        assert ar.distractor_fpr is None
        assert ar.per_scope == {}
        assert ar.per_stage == {}
        assert ar.mode_comparison is None

    def test_round_trip(self):
        ar = AggregatedResult(
            n_seeds=5,
            precision=self._make_stats(),
            recall=self._make_stats(),
            f1=self._make_stats(),
            partial_credit_score=self._make_stats(),
            distractor_fpr=self._make_stats(),
            per_scope={"intra_doc": {"precision": self._make_stats()}},
            per_stage={"claim_extraction": {"f1": self._make_stats()}},
            mode_comparison={"hybrid": 0.75, "agentic": 0.8},
        )
        json_str = ar.model_dump_json()
        restored = AggregatedResult.model_validate_json(json_str)
        assert ar == restored

    def test_snake_case_keys(self):
        ar = AggregatedResult(
            n_seeds=3,
            precision=self._make_stats(),
            recall=self._make_stats(),
            f1=self._make_stats(),
        )
        data = json.loads(ar.model_dump_json())
        assert "n_seeds" in data
        assert "partial_credit_score" in data
        assert "distractor_fpr" in data
        assert "per_scope" in data
        assert "per_stage" in data
        assert "mode_comparison" in data


# ---------------------------------------------------------------------------
# Package-level imports
# ---------------------------------------------------------------------------
class TestPackageImports:
    def test_all_models_importable_from_package(self):
        from crossfire.shared.schemas import (
            AnonymizationMapping,
            AggregatedResult,
            ContradictionLabel,
            CrossReference,
            DatasetVersion,
            DetectedContradiction,
            DistractorLabel,
            Document,
            DomainEntry,
            DomainRegistry,
            EvaluationResult,
            GenerationParams,
            KnowledgeGraphClaim,
            MetricStats,
            PipelineConfig,
            PipelineReport,
            RepresentationQualityResult,
            ScopeMap,
            ScopeMapEntry,
            ScopeResult,
            StageResult,
        )
        # Verify they are actual classes
        assert all(isinstance(cls, type) for cls in [
            AnonymizationMapping, AggregatedResult, ContradictionLabel,
            CrossReference, DatasetVersion, DetectedContradiction,
            DistractorLabel, Document, DomainEntry, DomainRegistry,
            EvaluationResult, GenerationParams, KnowledgeGraphClaim,
            MetricStats, PipelineConfig, PipelineReport,
            RepresentationQualityResult, ScopeMap, ScopeMapEntry,
            ScopeResult, StageResult,
        ])
