"""Tests for all Pydantic schema models in crossfire.shared.schemas."""

import json
from pathlib import Path

import yaml
import pytest
from pydantic import ValidationError

from crossfire.shared.schemas.config import (
    ScopeDistribution,
    DetectabilityDistribution,
    IncoherenceConfig,
    PresetConfig,
    GeneratorConfig,
    PipelineConfig,
)
from crossfire.shared.schemas.corpus import Document, SubcorpusMetadata
from crossfire.shared.schemas.entities import EntityNode, EntityEdge, EntityGraph
from crossfire.shared.schemas.incoherences import IncoherenceLabel, DistractorLabel
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport
from crossfire.shared.schemas.evaluation import ScopeResult, StageResult, EvaluationResult


PRESETS_DIR = Path(__file__).resolve().parents[2] / "configs" / "presets"


class TestScopeDistribution:
    def test_create(self):
        sd = ScopeDistribution(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3)
        assert sd.intra_doc == 0.2
        assert sd.intra_corpus == 0.5
        assert sd.inter_corpus == 0.3

    def test_round_trip(self):
        sd = ScopeDistribution(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3)
        json_str = sd.model_dump_json()
        restored = ScopeDistribution.model_validate_json(json_str)
        assert sd == restored


class TestDetectabilityDistribution:
    def test_create(self):
        dd = DetectabilityDistribution(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2)
        assert dd.single_hop == 0.3

    def test_round_trip(self):
        dd = DetectabilityDistribution(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2)
        json_str = dd.model_dump_json()
        restored = DetectabilityDistribution.model_validate_json(json_str)
        assert dd == restored


class TestPresetConfig:
    def _make_preset(self, **overrides):
        defaults = dict(
            name="test",
            description="Test config",
            master_seed=42,
            subcorpora_count=5,
            docs_per_subcorpus=80,
            connectivity_level=2,
            doc_type_mix="balanced",
            incoherences=dict(
                scope_distribution=dict(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
                mechanism="uniform",
                detectability_distribution=dict(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
                system_affinity="balanced",
                count="auto",
            ),
            distractor_ratio=0.3,
        )
        defaults.update(overrides)
        return PresetConfig(**defaults)

    def test_create(self):
        preset = self._make_preset()
        assert preset.name == "test"
        assert preset.master_seed == 42
        assert preset.connectivity_level == 2
        assert preset.incoherences.count == "auto"

    def test_count_as_int(self):
        preset = self._make_preset(
            incoherences=dict(
                scope_distribution=dict(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
                mechanism="uniform",
                detectability_distribution=dict(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
                system_affinity="balanced",
                count=50,
            ),
        )
        assert preset.incoherences.count == 50

    def test_invalid_connectivity_level(self):
        with pytest.raises(ValidationError):
            self._make_preset(connectivity_level=5)

    def test_round_trip(self):
        preset = self._make_preset()
        json_str = preset.model_dump_json()
        restored = PresetConfig.model_validate_json(json_str)
        assert preset == restored

    def test_snake_case_keys(self):
        preset = self._make_preset()
        data = json.loads(preset.model_dump_json())
        assert "master_seed" in data
        assert "subcorpora_count" in data
        assert "docs_per_subcorpus" in data
        assert "connectivity_level" in data
        assert "doc_type_mix" in data
        assert "distractor_ratio" in data
        assert "scope_distribution" in data["incoherences"]
        assert "detectability_distribution" in data["incoherences"]
        assert "system_affinity" in data["incoherences"]

    @pytest.mark.parametrize("preset_name", [
        "default", "low_connectivity", "high_connectivity", "stress_test",
    ])
    def test_load_existing_preset_yaml(self, preset_name):
        yaml_path = PRESETS_DIR / f"{preset_name}.yaml"
        assert yaml_path.exists(), f"Preset YAML not found: {yaml_path}"
        with open(yaml_path) as f:
            data = yaml.safe_load(f)
        preset = PresetConfig(**data)
        assert preset.name == preset_name
        # Round-trip
        json_str = preset.model_dump_json()
        restored = PresetConfig.model_validate_json(json_str)
        assert preset == restored


class TestGeneratorConfig:
    def test_extends_preset(self):
        gc = GeneratorConfig(
            name="test",
            description="Test",
            master_seed=42,
            subcorpora_count=5,
            docs_per_subcorpus=80,
            connectivity_level=2,
            doc_type_mix="balanced",
            incoherences=dict(
                scope_distribution=dict(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
                mechanism="uniform",
                detectability_distribution=dict(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
                system_affinity="balanced",
                count="auto",
            ),
            distractor_ratio=0.3,
            output_dir="/tmp/output",
            dry_run=True,
        )
        assert gc.output_dir == "/tmp/output"
        assert gc.dry_run is True
        assert gc.master_seed == 42

    def test_defaults(self):
        gc = GeneratorConfig(
            name="test",
            description="Test",
            master_seed=42,
            subcorpora_count=5,
            docs_per_subcorpus=80,
            connectivity_level=2,
            doc_type_mix="balanced",
            incoherences=dict(
                scope_distribution=dict(intra_doc=0.2, intra_corpus=0.5, inter_corpus=0.3),
                mechanism="uniform",
                detectability_distribution=dict(single_hop=0.3, multi_hop=0.5, entity_resolution=0.2),
                system_affinity="balanced",
                count="auto",
            ),
            distractor_ratio=0.3,
        )
        assert gc.output_dir == "output/generated"
        assert gc.dry_run is False


class TestPipelineConfig:
    def test_create(self):
        pc = PipelineConfig(mode="hybrid", corpus_path="/data/corpus")
        assert pc.mode == "hybrid"
        assert pc.corpus_path == "/data/corpus"
        assert pc.output_dir == "output/reports"

    def test_invalid_mode(self):
        with pytest.raises(ValidationError):
            PipelineConfig(mode="invalid", corpus_path="/data/corpus")

    def test_round_trip(self):
        pc = PipelineConfig(mode="agentic", corpus_path="/data/corpus", output_dir="/tmp/reports")
        json_str = pc.model_dump_json()
        restored = PipelineConfig.model_validate_json(json_str)
        assert pc == restored


class TestDocument:
    def test_create(self):
        doc = Document(
            id="doc-001",
            document_type="investigation_report",
            subcorpus_id="sc-1",
            reliability_signal=0.85,
            content="Report content here.",
        )
        assert doc.id == "doc-001"
        assert doc.document_type == "investigation_report"
        assert doc.reliability_signal == 0.85

    def test_invalid_document_type(self):
        with pytest.raises(ValidationError):
            Document(
                id="doc-001",
                document_type="invalid_type",
                subcorpus_id="sc-1",
                reliability_signal=0.5,
                content="Content",
            )

    def test_reliability_signal_bounds(self):
        with pytest.raises(ValidationError):
            Document(
                id="doc-001",
                document_type="investigation_report",
                subcorpus_id="sc-1",
                reliability_signal=1.5,
                content="Content",
            )

    def test_round_trip(self):
        doc = Document(
            id="doc-001",
            document_type="technical_analysis",
            subcorpus_id="sc-2",
            reliability_signal=0.7,
            content="Technical analysis content.",
        )
        json_str = doc.model_dump_json()
        restored = Document.model_validate_json(json_str)
        assert doc == restored

    def test_snake_case_keys(self):
        doc = Document(
            id="doc-001",
            document_type="witness_testimony",
            subcorpus_id="sc-1",
            reliability_signal=0.9,
            content="Testimony.",
        )
        data = json.loads(doc.model_dump_json())
        assert "document_type" in data
        assert "subcorpus_id" in data
        assert "reliability_signal" in data

    def test_all_document_types(self):
        types = [
            "investigation_report", "technical_analysis", "witness_testimony",
            "regulatory_filing", "press_coverage", "expert_deposition",
            "internal_memo", "preliminary_report",
        ]
        for dt in types:
            doc = Document(id="x", document_type=dt, subcorpus_id="sc", reliability_signal=0.5, content="c")
            assert doc.document_type == dt


class TestSubcorpusMetadata:
    def test_create(self):
        meta = SubcorpusMetadata(
            subcorpus_id="sc-1",
            document_count=80,
            document_types=["investigation_report", "technical_analysis"],
        )
        assert meta.subcorpus_id == "sc-1"
        assert meta.document_count == 80

    def test_round_trip(self):
        meta = SubcorpusMetadata(
            subcorpus_id="sc-1",
            document_count=80,
            document_types=["investigation_report"],
        )
        json_str = meta.model_dump_json()
        restored = SubcorpusMetadata.model_validate_json(json_str)
        assert meta == restored


class TestEntityNode:
    def test_create(self):
        node = EntityNode(
            id="ent-001",
            entity_type="company",
            canonical_name="Acme Corp",
            aliases=["ACME", "Acme Corporation"],
            subcorpus_memberships=["sc-1", "sc-2"],
        )
        assert node.id == "ent-001"
        assert node.canonical_name == "Acme Corp"
        assert len(node.aliases) == 2

    def test_defaults(self):
        node = EntityNode(id="ent-001", entity_type="person", canonical_name="John Doe")
        assert node.aliases == []
        assert node.subcorpus_memberships == []

    def test_round_trip(self):
        node = EntityNode(
            id="ent-001",
            entity_type="equipment",
            canonical_name="Boeing 737",
            aliases=["B737", "737"],
            subcorpus_memberships=["sc-1"],
        )
        json_str = node.model_dump_json()
        restored = EntityNode.model_validate_json(json_str)
        assert node == restored


class TestEntityEdge:
    def test_create(self):
        edge = EntityEdge(source="ent-001", target="ent-002", relationship_type="manufactured_by")
        assert edge.source == "ent-001"
        assert edge.relationship_type == "manufactured_by"

    def test_round_trip(self):
        edge = EntityEdge(source="ent-001", target="ent-002", relationship_type="operates")
        json_str = edge.model_dump_json()
        restored = EntityEdge.model_validate_json(json_str)
        assert edge == restored


class TestEntityGraph:
    def _make_graph(self):
        nodes = [
            EntityNode(id="ent-1", entity_type="company", canonical_name="Acme", aliases=["ACME"], subcorpus_memberships=["sc-1"]),
            EntityNode(id="ent-2", entity_type="person", canonical_name="Jane", aliases=[], subcorpus_memberships=["sc-1", "sc-2"]),
        ]
        edges = [EntityEdge(source="ent-1", target="ent-2", relationship_type="employs")]
        return EntityGraph(nodes=nodes, edges=edges)

    def test_create(self):
        eg = self._make_graph()
        assert len(eg.nodes) == 2
        assert len(eg.edges) == 1

    def test_to_networkx(self):
        eg = self._make_graph()
        g = eg.to_networkx()
        assert len(g.nodes) == 2
        assert len(g.edges) == 1
        assert g.nodes["ent-1"]["canonical_name"] == "Acme"
        assert g.nodes["ent-1"]["aliases"] == ["ACME"]
        assert g["ent-1"]["ent-2"]["relationship_type"] == "employs"

    def test_from_networkx(self):
        eg = self._make_graph()
        g = eg.to_networkx()
        restored = EntityGraph.from_networkx(g)
        assert len(restored.nodes) == 2
        assert len(restored.edges) == 1
        node_ids = {n.id for n in restored.nodes}
        assert node_ids == {"ent-1", "ent-2"}

    def test_networkx_round_trip(self):
        eg = self._make_graph()
        g = eg.to_networkx()
        restored = EntityGraph.from_networkx(g)
        # Verify all node data preserved
        original_by_id = {n.id: n for n in eg.nodes}
        restored_by_id = {n.id: n for n in restored.nodes}
        for nid in original_by_id:
            assert original_by_id[nid] == restored_by_id[nid]
        # Verify edge data preserved
        assert len(eg.edges) == len(restored.edges)
        orig_edge = eg.edges[0]
        rest_edge = restored.edges[0]
        assert {orig_edge.source, orig_edge.target} == {rest_edge.source, rest_edge.target}
        assert orig_edge.relationship_type == rest_edge.relationship_type

    def test_json_round_trip(self):
        eg = self._make_graph()
        json_str = eg.model_dump_json()
        restored = EntityGraph.model_validate_json(json_str)
        assert eg == restored

    def test_empty_graph(self):
        eg = EntityGraph()
        assert len(eg.nodes) == 0
        assert len(eg.edges) == 0
        g = eg.to_networkx()
        assert len(g.nodes) == 0


class TestIncoherenceLabel:
    def test_create(self):
        label = IncoherenceLabel(
            id="inc-001",
            scope="intra_corpus",
            mechanism="entity_swap",
            detectability="multi_hop",
            system_affinity="balanced",
            document_references=["doc-001", "doc-002"],
            modified_fact="The Boeing 737 was manufactured in 2019.",
            original_fact="The Boeing 737 was manufactured in 2015.",
        )
        assert label.id == "inc-001"
        assert label.scope == "intra_corpus"
        assert label.mechanism == "entity_swap"
        assert len(label.document_references) == 2

    def test_invalid_scope(self):
        with pytest.raises(ValidationError):
            IncoherenceLabel(
                id="inc-001",
                scope="invalid",
                mechanism="entity_swap",
                detectability="multi_hop",
                system_affinity="balanced",
                document_references=[],
                modified_fact="m",
                original_fact="o",
            )

    def test_invalid_mechanism(self):
        with pytest.raises(ValidationError):
            IncoherenceLabel(
                id="inc-001",
                scope="intra_doc",
                mechanism="invalid_mech",
                detectability="single_hop",
                system_affinity="balanced",
                document_references=[],
                modified_fact="m",
                original_fact="o",
            )

    def test_round_trip(self):
        label = IncoherenceLabel(
            id="inc-001",
            scope="inter_corpus",
            mechanism="temporal_contradiction",
            detectability="entity_resolution_dependent",
            system_affinity="graph_favoring",
            document_references=["doc-001"],
            modified_fact="Modified.",
            original_fact="Original.",
        )
        json_str = label.model_dump_json()
        restored = IncoherenceLabel.model_validate_json(json_str)
        assert label == restored

    def test_snake_case_keys(self):
        label = IncoherenceLabel(
            id="inc-001",
            scope="intra_doc",
            mechanism="numeric_drift",
            detectability="single_hop",
            system_affinity="agentic_favoring",
            document_references=["doc-001"],
            modified_fact="m",
            original_fact="o",
        )
        data = json.loads(label.model_dump_json())
        assert "system_affinity" in data
        assert "document_references" in data
        assert "modified_fact" in data
        assert "original_fact" in data

    def test_all_mechanisms(self):
        mechs = [
            "numeric_drift", "entity_swap", "causal_inversion",
            "temporal_contradiction", "omission_based_implicit", "temporal_revision_conflict",
        ]
        for mech in mechs:
            label = IncoherenceLabel(
                id="x", scope="intra_doc", mechanism=mech, detectability="single_hop",
                system_affinity="balanced", document_references=[], modified_fact="m", original_fact="o",
            )
            assert label.mechanism == mech


class TestDistractorLabel:
    def test_create(self):
        dl = DistractorLabel(
            id="dist-001",
            scope="intra_corpus",
            document_references=["doc-001", "doc-003"],
            divergence_type="expert_opinion",
            description="Two experts disagree on failure cause.",
        )
        assert dl.id == "dist-001"
        assert dl.divergence_type == "expert_opinion"

    def test_round_trip(self):
        dl = DistractorLabel(
            id="dist-001",
            scope="inter_corpus",
            document_references=["doc-001"],
            divergence_type="measurement_methodology",
            description="Different measurement approaches.",
        )
        json_str = dl.model_dump_json()
        restored = DistractorLabel.model_validate_json(json_str)
        assert dl == restored


class TestDetectedIncoherence:
    def test_create(self):
        di = DetectedIncoherence(
            id="det-001",
            evidence_references=["doc-001", "doc-002"],
            confidence=0.87,
            description="Conflicting dates for incident.",
        )
        assert di.confidence == 0.87
        assert len(di.evidence_references) == 2

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            DetectedIncoherence(id="x", evidence_references=[], confidence=1.5, description="d")

    def test_round_trip(self):
        di = DetectedIncoherence(
            id="det-001",
            evidence_references=["doc-001"],
            confidence=0.5,
            description="Desc.",
        )
        json_str = di.model_dump_json()
        restored = DetectedIncoherence.model_validate_json(json_str)
        assert di == restored


class TestPipelineReport:
    def test_create(self):
        report = PipelineReport(
            pipeline_mode="hybrid",
            corpus_path="/data/corpus",
            detections=[
                DetectedIncoherence(id="d1", evidence_references=["doc-1"], confidence=0.9, description="Conflict"),
            ],
            timestamp="2026-04-06T12:00:00",
        )
        assert report.pipeline_mode == "hybrid"
        assert len(report.detections) == 1

    def test_empty_detections(self):
        report = PipelineReport(
            pipeline_mode="agentic",
            corpus_path="/data/corpus",
            timestamp="2026-04-06T12:00:00",
        )
        assert report.detections == []

    def test_round_trip(self):
        report = PipelineReport(
            pipeline_mode="graph-native",
            corpus_path="/data/corpus",
            detections=[
                DetectedIncoherence(id="d1", evidence_references=["doc-1", "doc-2"], confidence=0.75, description="X"),
                DetectedIncoherence(id="d2", evidence_references=["doc-3"], confidence=0.6, description="Y"),
            ],
            timestamp="2026-04-06T12:00:00",
        )
        json_str = report.model_dump_json()
        restored = PipelineReport.model_validate_json(json_str)
        assert report == restored

    def test_snake_case_keys(self):
        report = PipelineReport(
            pipeline_mode="hybrid",
            corpus_path="/data/corpus",
            detections=[
                DetectedIncoherence(id="d1", evidence_references=["doc-1"], confidence=0.9, description="C"),
            ],
            timestamp="2026-04-06T12:00:00",
        )
        data = json.loads(report.model_dump_json())
        assert "pipeline_mode" in data
        assert "corpus_path" in data
        assert "evidence_references" in data["detections"][0]


class TestScopeResult:
    def test_create(self):
        sr = ScopeResult(scope="intra_doc", precision=0.8, recall=0.7, f1=0.75, partial_credit_score=0.82)
        assert sr.scope == "intra_doc"
        assert sr.f1 == 0.75

    def test_round_trip(self):
        sr = ScopeResult(scope="inter_corpus", precision=0.6, recall=0.5, f1=0.55, partial_credit_score=0.65)
        json_str = sr.model_dump_json()
        restored = ScopeResult.model_validate_json(json_str)
        assert sr == restored


class TestStageResult:
    def test_create(self):
        st = StageResult(stage="entity_resolution", precision=0.9, recall=0.85, f1=0.87)
        assert st.stage == "entity_resolution"

    def test_round_trip(self):
        st = StageResult(stage="scanning", precision=0.7, recall=0.6, f1=0.65)
        json_str = st.model_dump_json()
        restored = StageResult.model_validate_json(json_str)
        assert st == restored


class TestEvaluationResult:
    def test_create(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
                ScopeResult(scope="intra_corpus", precision=0.7, recall=0.6, f1=0.65, partial_credit_score=0.7),
                ScopeResult(scope="inter_corpus", precision=0.6, recall=0.5, f1=0.55, partial_credit_score=0.6),
            ],
            per_stage=[
                StageResult(stage="entity_resolution", precision=0.85, recall=0.8, f1=0.82),
                StageResult(stage="graph_construction", precision=0.75, recall=0.7, f1=0.72),
                StageResult(stage="scanning", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        assert er.overall_f1 == 0.75
        assert len(er.per_scope) == 3
        assert len(er.per_stage) == 3

    def test_defaults(self):
        er = EvaluationResult(overall_precision=0.5, overall_recall=0.5, overall_f1=0.5)
        assert er.per_scope == []
        assert er.per_stage == []

    def test_round_trip(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
            ],
            per_stage=[
                StageResult(stage="scanning", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        json_str = er.model_dump_json()
        restored = EvaluationResult.model_validate_json(json_str)
        assert er == restored

    def test_snake_case_keys(self):
        er = EvaluationResult(
            overall_precision=0.8,
            overall_recall=0.7,
            overall_f1=0.75,
            per_scope=[
                ScopeResult(scope="intra_doc", precision=0.9, recall=0.8, f1=0.85, partial_credit_score=0.9),
            ],
            per_stage=[
                StageResult(stage="scanning", precision=0.8, recall=0.75, f1=0.77),
            ],
        )
        data = json.loads(er.model_dump_json())
        assert "overall_precision" in data
        assert "overall_recall" in data
        assert "overall_f1" in data
        assert "per_scope" in data
        assert "per_stage" in data
        assert "partial_credit_score" in data["per_scope"][0]
