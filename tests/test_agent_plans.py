"""Tests for source-specific agent plan documents.

Validates that plan documents exist, contain required sections,
specify correct models, and include source-specific anonymization rules.
"""

from pathlib import Path

import pytest

# Project root and plan directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATION_DIR = PROJECT_ROOT / "generation" / "sources"

SOURCES = ["ntsb", "grenfell", "copa"]
PLAN_PATHS = {s: GENERATION_DIR / s / "agent_plan.md" for s in SOURCES}


# ---------------------------------------------------------------------------
# AC1: Plan files exist at expected paths
# ---------------------------------------------------------------------------
class TestPlanFilesExist:
    """AC1: Source-specific plan documents exist."""

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_file_exists(self, source_id: str) -> None:
        path = PLAN_PATHS[source_id]
        assert path.exists(), f"Plan file missing: {path}"
        assert path.is_file(), f"Expected file, got directory: {path}"

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_file_is_readable_markdown(self, source_id: str) -> None:
        path = PLAN_PATHS[source_id]
        content = path.read_text()
        assert len(content) > 500, f"Plan file suspiciously short ({len(content)} chars): {path}"
        assert content.startswith("# CROSSFIRE:"), f"Plan should start with '# CROSSFIRE:' header: {path}"


# ---------------------------------------------------------------------------
# AC2: Plan instructs four processing phases
# ---------------------------------------------------------------------------
class TestFourPhases:
    """AC2: Each plan instructs four processing phases."""

    REQUIRED_PHASES = [
        "Phase 1: Anonymization",
        "Phase 2: Reformatting",
        "Phase 3: Per-Chunk Claim Extraction",
        "Phase 4: Cross-Document Reasoning",
    ]

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_contains_all_four_phases(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        for phase in self.REQUIRED_PHASES:
            assert phase in content, (
                f"Plan for {source_id} missing required phase: '{phase}'"
            )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_phases_are_sections(self, source_id: str) -> None:
        """Phases should be markdown sections (## headers)."""
        content = PLAN_PATHS[source_id].read_text()
        for phase in self.REQUIRED_PHASES:
            assert f"## {phase}" in content, (
                f"Plan for {source_id}: '{phase}' should be a ## section header"
            )


# ---------------------------------------------------------------------------
# AC3: Output directory structure
# ---------------------------------------------------------------------------
class TestOutputStructure:
    """AC3: Plans specify correct output directory structure."""

    REQUIRED_OUTPUT_DIRS = [
        "anonymized_docs/",
        "original_claims/",
        "metadata/",
    ]

    REQUIRED_OUTPUT_FILES = [
        "entity_mapping.json",
        "knowledge_graph.json",
        "domain_registry.json",
        "scope_map.json",
    ]

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_specifies_output_directories(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        for dir_name in self.REQUIRED_OUTPUT_DIRS:
            assert dir_name in content, (
                f"Plan for {source_id} missing output directory: '{dir_name}'"
            )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_specifies_output_files(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        for filename in self.REQUIRED_OUTPUT_FILES:
            assert filename in content, (
                f"Plan for {source_id} missing output file: '{filename}'"
            )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_has_output_layout_section(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        assert "Output Directory Layout" in content, (
            f"Plan for {source_id} missing 'Output Directory Layout' section"
        )


# ---------------------------------------------------------------------------
# AC4: Fan-out architecture specified with correct models
# ---------------------------------------------------------------------------
class TestFanOutArchitecture:
    """AC4: Plans specify fan-out architecture with Sonnet + Opus."""

    SONNET_MODEL = "claude-sonnet-4-20250514"
    OPUS_MODEL = "claude-opus-4-20250514"

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_references_sonnet_model(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        assert self.SONNET_MODEL in content, (
            f"Plan for {source_id} missing Sonnet model reference: '{self.SONNET_MODEL}'"
        )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_references_opus_model(self, source_id: str) -> None:
        content = PLAN_PATHS[source_id].read_text()
        assert self.OPUS_MODEL in content, (
            f"Plan for {source_id} missing Opus model reference: '{self.OPUS_MODEL}'"
        )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_sonnet_used_for_extraction(self, source_id: str) -> None:
        """Sonnet should be specified for per-chunk claim extraction (Phase 3)."""
        content = PLAN_PATHS[source_id].read_text()
        # Find Phase 3 header and check model assignment
        assert "Phase 3" in content
        phase3_start = content.index("Phase 3")
        phase3_section = content[phase3_start:phase3_start + 200]
        assert self.SONNET_MODEL in phase3_section, (
            f"Plan for {source_id}: Phase 3 should specify Sonnet model"
        )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_opus_used_for_reasoning(self, source_id: str) -> None:
        """Opus should be specified for cross-document reasoning (Phase 4)."""
        content = PLAN_PATHS[source_id].read_text()
        assert "Phase 4" in content
        phase4_start = content.index("Phase 4")
        phase4_section = content[phase4_start:phase4_start + 200]
        assert self.OPUS_MODEL in phase4_section, (
            f"Plan for {source_id}: Phase 4 should specify Opus model"
        )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_plan_references_chunk_manifest(self, source_id: str) -> None:
        """Plan should reference chunk_manifest.json for fan-out input."""
        content = PLAN_PATHS[source_id].read_text()
        assert "chunk_manifest.json" in content, (
            f"Plan for {source_id} missing chunk_manifest.json reference"
        )


# ---------------------------------------------------------------------------
# AC5: Source-specific anonymization rules
# ---------------------------------------------------------------------------
class TestNTSBSpecificRules:
    """AC5: NTSB plan has aviation-specific anonymization."""

    def _content(self) -> str:
        return PLAN_PATHS["ntsb"].read_text()

    def test_tail_number_anonymization(self) -> None:
        content = self._content()
        assert "N-number" in content or "Tail number" in content or "tail number" in content, (
            "NTSB plan should mention tail number / N-number anonymization"
        )

    def test_airline_anonymization(self) -> None:
        content = self._content()
        assert "Airline-A" in content, (
            "NTSB plan should specify airline anonymization labels (Airline-A, Airline-B)"
        )

    def test_airport_anonymization(self) -> None:
        content = self._content()
        assert "Airport-Alpha" in content or "Airport-Bravo" in content, (
            "NTSB plan should specify airport anonymization labels"
        )

    def test_personnel_role_based(self) -> None:
        content = self._content()
        assert "PIC" in content or "FO" in content, (
            "NTSB plan should use role-based personnel identifiers (PIC, FO, Controller)"
        )

    def test_cross_document_entity_variation(self) -> None:
        """NTSB plan must preserve natural cross-document entity variation."""
        content = self._content()
        assert "entity variation" in content.lower() or "natural variation" in content.lower(), (
            "NTSB plan should mention preserving cross-document entity variation"
        )

    def test_ntsb_document_types(self) -> None:
        """Plan should reference NTSB document types from classifier."""
        content = self._content()
        for doc_type in ["ops_group_report", "meteorology_report", "atc_transcript", "witness_testimony"]:
            assert doc_type in content, (
                f"NTSB plan missing document type: {doc_type}"
            )


class TestGrenfellSpecificRules:
    """AC5: Grenfell plan has inquiry party anonymization."""

    def _content(self) -> str:
        return PLAN_PATHS["grenfell"].read_text()

    def test_eight_cladding_parties(self) -> None:
        """Grenfell plan must anonymize 8 cladding inquiry parties."""
        content = self._content()
        parties = ["Arconic", "Celotex", "Kingspan", "RBKC TMO", "London Fire Brigade", "BRE", "Exova", "Studio E"]
        for party in parties:
            assert party in content, (
                f"Grenfell plan missing party: {party}"
            )

    def test_party_labels(self) -> None:
        """Grenfell plan should use Company/Organization/Service/Agency/Firm labels."""
        content = self._content()
        for label in ["Company-A", "Company-B", "Company-C", "Organization-D", "Service-E"]:
            assert label in content, (
                f"Grenfell plan missing party label: {label}"
            )

    def test_witness_anonymization(self) -> None:
        content = self._content()
        assert "Witness-1" in content or "Witness-2" in content, (
            "Grenfell plan should use Witness-N anonymization labels"
        )

    def test_location_anonymization(self) -> None:
        content = self._content()
        assert "Tower-X" in content, "Grenfell plan should anonymize Grenfell Tower as Tower-X"
        assert "Estate-Y" in content, "Grenfell plan should anonymize Lancaster West Estate as Estate-Y"

    def test_hearing_transcript_structure(self) -> None:
        """Grenfell plan should preserve Q&A hearing transcript structure."""
        content = self._content()
        assert "Q&A" in content or "page/line" in content or "page and line" in content, (
            "Grenfell plan should mention hearing transcript Q&A structure"
        )

    def test_party_vs_party_testimony(self) -> None:
        """Grenfell plan should preserve party-vs-party testimony structure."""
        content = self._content()
        assert "party" in content.lower() and "testimony" in content.lower(), (
            "Grenfell plan should describe party-vs-party testimony structure"
        )


class TestCOPASpecificRules:
    """AC5: COPA plan has police accountability anonymization."""

    def _content(self) -> str:
        return PLAN_PATHS["copa"].read_text()

    def test_officer_anonymization(self) -> None:
        content = self._content()
        assert "Officer-1" in content or "Officer-2" in content, (
            "COPA plan should use Officer-N anonymization labels"
        )

    def test_badge_number_anonymization(self) -> None:
        content = self._content()
        assert "badge" in content.lower() or "star" in content.lower(), (
            "COPA plan should mention badge/star number anonymization"
        )

    def test_witness_complainant_anonymization(self) -> None:
        content = self._content()
        assert "Witness-A" in content or "Subject-B" in content or "Subject-A" in content, (
            "COPA plan should use Witness-A/Subject-B anonymization labels"
        )

    def test_address_anonymization(self) -> None:
        content = self._content()
        assert "Location-North" in content or "Location-South" in content, (
            "COPA plan should use generic neighborhood labels for addresses"
        )

    def test_case_identifier_anonymization(self) -> None:
        content = self._content()
        assert "Case-001" in content, (
            "COPA plan should anonymize RD/log numbers to Case-001 format"
        )

    def test_copa_document_types(self) -> None:
        """Plan should reference COPA document types from classifier."""
        content = self._content()
        for doc_type in ["tactical_response_report", "final_summary_report", "case_incident_report"]:
            assert doc_type in content, (
                f"COPA plan missing document type: {doc_type}"
            )


# ---------------------------------------------------------------------------
# Schema conformance: plans should reference schema field names
# ---------------------------------------------------------------------------
class TestSchemaConformance:
    """Plans should specify output formats matching project schemas."""

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_knowledge_graph_claim_fields(self, source_id: str) -> None:
        """Plans should reference KnowledgeGraphClaim fields."""
        content = PLAN_PATHS[source_id].read_text()
        for field in ["claim_id", "subject", "predicate", "object", "source_document", "confidence"]:
            assert field in content, (
                f"Plan for {source_id} missing KnowledgeGraphClaim field: '{field}'"
            )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_cross_reference_fields(self, source_id: str) -> None:
        """Plans should reference CrossReference fields."""
        content = PLAN_PATHS[source_id].read_text()
        for field in ["reference_id", "source_claim", "target_claim", "relationship", "source_documents"]:
            assert field in content, (
                f"Plan for {source_id} missing CrossReference field: '{field}'"
            )

    @pytest.mark.parametrize("source_id", SOURCES)
    def test_anonymization_mapping_fields(self, source_id: str) -> None:
        """Plans should reference AnonymizationMapping fields."""
        content = PLAN_PATHS[source_id].read_text()
        for field in ["original", "anonymized", "entity_type"]:
            assert field in content, (
                f"Plan for {source_id} missing AnonymizationMapping field: '{field}'"
            )
