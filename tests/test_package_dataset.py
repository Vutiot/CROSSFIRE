"""Tests for dataset versioning & release packaging (Story 3.5-NEW).

Covers:
    AC1: Dataset directory structure
    AC2: Generation params tracking
    AC3: Re-injection from base (--base-version)
    AC4: Dataset manifest with aggregate stats
    AC5: Knowledge graph included (not gold eval reference)
    AC6: Distractor labels included
"""

import json
import sys
from pathlib import Path

import pytest

# Ensure generation/ scripts can import from crossfire.shared.schemas
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "src"))

if str(_PROJECT_ROOT / "generation") not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "generation"))

from package_dataset import (  # noqa: E402
    compute_manifest,
    copy_case,
    package_dataset,
)
from crossfire.shared.schemas.config import GenerationParams  # noqa: E402
from crossfire.shared.schemas.contradictions import (  # noqa: E402
    ContradictionLabel,
    DistractorLabel,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_contradiction(
    scope: str = "intra_doc",
    mechanism: str = "numeric_drift",
    detectability: str = "single_hop",
    difficulty: str = "medium",
) -> ContradictionLabel:
    """Build a ContradictionLabel for test data."""
    return ContradictionLabel(
        scope=scope,
        mechanism=mechanism,
        detectability=detectability,
        system_affinity="balanced",
        difficulty=difficulty,
        char_start=0,
        char_end=10,
        original_text="35,000 feet",
        modified_text="28,000 feet",
        rationale="Numeric drift test",
        ground_truth=True,
        document_references=["doc_001"],
    )


def _make_distractor(scope: str = "intra_doc") -> DistractorLabel:
    """Build a DistractorLabel for test data."""
    return DistractorLabel(
        scope=scope,
        divergence_type="expert_opinion",
        document_references=["doc_001"],
        description="Expert opinion divergence test",
    )


def _setup_source_case(
    base_dir: Path,
    case_id: str = "case_001",
    num_intra: int = 2,
    num_inter: int = 1,
    num_distractors: int = 1,
    num_docs: int = 3,
) -> Path:
    """Create a mock source case directory with all expected subdirectories.

    Structure:
        base_dir/{case_id}/
            anonymized_docs/*.txt
            contradictions/
                intra_doc_contradictions.jsonl
                inter_doc_contradictions.jsonl
                all_contradictions.jsonl
            distractors/distractor_labels.jsonl
            metadata/
                knowledge_graph.json
                domain_registry.json
                scope_map.json
            validation/diff_verification_log.json
    """
    case_dir = base_dir / case_id

    # anonymized_docs - text files
    docs_dir = case_dir / "anonymized_docs"
    docs_dir.mkdir(parents=True)
    for i in range(num_docs):
        (docs_dir / f"doc_{i:03d}.txt").write_text(
            f"Document {i} content for testing purposes.", encoding="utf-8",
        )

    # contradictions
    contra_dir = case_dir / "contradictions"
    contra_dir.mkdir(parents=True)

    intra_labels = [_make_contradiction(scope="intra_doc") for _ in range(num_intra)]
    inter_labels = [
        _make_contradiction(
            scope="inter_doc",
            mechanism="temporal_contradiction",
            detectability="multi_hop",
            difficulty="hard",
        )
        for _ in range(num_inter)
    ]
    all_labels = intra_labels + inter_labels

    _write_model_jsonl(contra_dir / "intra_doc_contradictions.jsonl", intra_labels)
    _write_model_jsonl(contra_dir / "inter_doc_contradictions.jsonl", inter_labels)
    _write_model_jsonl(contra_dir / "all_contradictions.jsonl", all_labels)

    # distractors
    dist_dir = case_dir / "distractors"
    dist_dir.mkdir(parents=True)
    distractors = [_make_distractor() for _ in range(num_distractors)]
    _write_model_jsonl(dist_dir / "distractor_labels.jsonl", distractors)

    # metadata
    meta_dir = case_dir / "metadata"
    meta_dir.mkdir(parents=True)
    (meta_dir / "knowledge_graph.json").write_text(
        json.dumps({"claims": [], "note": "NOT a gold evaluation reference"}),
        encoding="utf-8",
    )
    (meta_dir / "domain_registry.json").write_text(
        json.dumps({"domains": []}), encoding="utf-8",
    )
    (meta_dir / "scope_map.json").write_text(
        json.dumps({"entries": []}), encoding="utf-8",
    )

    # validation
    val_dir = case_dir / "validation"
    val_dir.mkdir(parents=True)
    (val_dir / "diff_verification_log.json").write_text(
        json.dumps([{"label_index": 0, "passed": True}]), encoding="utf-8",
    )

    return case_dir


def _write_model_jsonl(path: Path, models: list) -> None:
    """Write a list of Pydantic models as JSONL."""
    with open(path, "w", encoding="utf-8") as f:
        for model in models:
            f.write(model.model_dump_json() + "\n")


# ---------------------------------------------------------------------------
# Task 1: Dataset directory structure (AC1)
# ---------------------------------------------------------------------------


class TestDatasetDirectoryStructure:
    """AC1: Dataset directory structure is correctly assembled."""

    def test_version_directory_created(self, tmp_path: Path) -> None:
        """Dataset version directory is created at output_dir/version."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        assert (output_dir / "v1").is_dir()

    def test_case_subdirectory_created(self, tmp_path: Path) -> None:
        """Each case gets its own subdirectory in the version dir."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        assert (output_dir / "v1" / "case_001").is_dir()

    def test_anonymized_docs_copied(self, tmp_path: Path) -> None:
        """anonymized_docs/ .txt files are copied per case."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001", num_docs=3)
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        docs_dir = output_dir / "v1" / "case_001" / "anonymized_docs"
        assert docs_dir.is_dir()
        txt_files = list(docs_dir.glob("*.txt"))
        assert len(txt_files) == 3

    def test_contradictions_copied(self, tmp_path: Path) -> None:
        """contradictions/ JSONL files are copied per case."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        contra_dir = output_dir / "v1" / "case_001" / "contradictions"
        assert contra_dir.is_dir()
        assert (contra_dir / "intra_doc_contradictions.jsonl").exists()
        assert (contra_dir / "inter_doc_contradictions.jsonl").exists()
        assert (contra_dir / "all_contradictions.jsonl").exists()

    def test_distractors_copied(self, tmp_path: Path) -> None:
        """AC6: distractors/distractor_labels.jsonl is copied per case."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        dist_path = output_dir / "v1" / "case_001" / "distractors" / "distractor_labels.jsonl"
        assert dist_path.exists()

    def test_metadata_copied(self, tmp_path: Path) -> None:
        """AC5: metadata/ (knowledge_graph.json, domain_registry.json, scope_map.json) copied."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        meta_dir = output_dir / "v1" / "case_001" / "metadata"
        assert meta_dir.is_dir()
        assert (meta_dir / "knowledge_graph.json").exists()
        assert (meta_dir / "domain_registry.json").exists()
        assert (meta_dir / "scope_map.json").exists()

    def test_validation_copied(self, tmp_path: Path) -> None:
        """validation/ files are copied per case."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        val_dir = output_dir / "v1" / "case_001" / "validation"
        assert val_dir.is_dir()
        assert (val_dir / "diff_verification_log.json").exists()

    def test_multiple_cases(self, tmp_path: Path) -> None:
        """Multiple case directories are all copied."""
        source = tmp_path / "source"
        case1 = _setup_source_case(source, "case_001")
        case2 = _setup_source_case(source, "case_002")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case1, case2],
            output_dir=output_dir,
        )

        assert (output_dir / "v1" / "case_001").is_dir()
        assert (output_dir / "v1" / "case_002").is_dir()


# ---------------------------------------------------------------------------
# Task 1 continued: Generation params (AC2)
# ---------------------------------------------------------------------------


class TestGenerationParams:
    """AC2: generation_params.json is written with correct fields."""

    def test_generation_params_written(self, tmp_path: Path) -> None:
        """generation_params.json exists in version directory."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        params_path = output_dir / "v1" / "generation_params.json"
        assert params_path.exists()

    def test_generation_params_has_version_id(self, tmp_path: Path) -> None:
        """generation_params.json records version_id."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        params = json.loads((output_dir / "v1" / "generation_params.json").read_text())
        assert params["version_id"] == "v1"

    def test_generation_params_validates_against_schema(self, tmp_path: Path) -> None:
        """generation_params.json validates against GenerationParams model."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        params = json.loads((output_dir / "v1" / "generation_params.json").read_text())
        gp = GenerationParams.model_validate(params)
        assert gp.version_id == "v1"
        assert 0.0 <= gp.contradiction_rate_intra_doc <= 1.0
        assert 0.0 <= gp.contradiction_rate_inter_doc <= 1.0

    def test_custom_params_file(self, tmp_path: Path) -> None:
        """--params-file loads custom GenerationParams from JSON."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        custom_params = GenerationParams(
            version_id="v1",
            contradiction_rate_intra_doc=0.3,
            contradiction_rate_inter_doc=0.2,
            distractor_ratio=0.5,
            mechanism_distribution={"numeric_drift": 0.5, "entity_swap": 0.5},
            difficulty_distribution={"easy": 0.3, "medium": 0.4, "hard": 0.3},
            extraction_model="test-model",
            reasoning_model="test-model-2",
        )
        params_file = tmp_path / "custom_params.json"
        params_file.write_text(custom_params.model_dump_json(indent=2), encoding="utf-8")

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
            params_file=params_file,
        )

        written = json.loads((output_dir / "v1" / "generation_params.json").read_text())
        assert written["contradiction_rate_intra_doc"] == 0.3
        assert written["contradiction_rate_inter_doc"] == 0.2
        assert written["distractor_ratio"] == 0.5
        assert written["extraction_model"] == "test-model"

    def test_generation_params_has_base_version(self, tmp_path: Path) -> None:
        """AC3: base_version is recorded when provided."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v2",
            case_dirs=[case_dir],
            output_dir=output_dir,
            base_version="v1",
        )

        params = json.loads((output_dir / "v2" / "generation_params.json").read_text())
        assert params["base_version"] == "v1"


# ---------------------------------------------------------------------------
# Task 2: Dataset manifest (AC4)
# ---------------------------------------------------------------------------


class TestDatasetManifest:
    """AC4: dataset_manifest.json has correct aggregate statistics."""

    def test_manifest_written(self, tmp_path: Path) -> None:
        """dataset_manifest.json exists in version directory."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest_path = output_dir / "v1" / "dataset_manifest.json"
        assert manifest_path.exists()

    def test_manifest_case_count(self, tmp_path: Path) -> None:
        """Manifest records correct case count."""
        source = tmp_path / "source"
        case1 = _setup_source_case(source, "case_001")
        case2 = _setup_source_case(source, "case_002")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case1, case2],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["case_count"] == 2

    def test_manifest_document_count(self, tmp_path: Path) -> None:
        """Manifest records correct total document count."""
        source = tmp_path / "source"
        case1 = _setup_source_case(source, "case_001", num_docs=3)
        case2 = _setup_source_case(source, "case_002", num_docs=2)
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case1, case2],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["document_count"] == 5

    def test_manifest_contradiction_counts_per_scope(self, tmp_path: Path) -> None:
        """Manifest has correct contradiction counts per scope."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(
            source, "case_001", num_intra=3, num_inter=2,
        )
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["contradictions_per_scope"]["intra_doc"] == 3
        assert manifest["contradictions_per_scope"]["inter_doc"] == 2

    def test_manifest_distractor_count(self, tmp_path: Path) -> None:
        """Manifest has correct distractor count."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001", num_distractors=4)
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["distractor_count"] == 4

    def test_manifest_mechanism_distribution(self, tmp_path: Path) -> None:
        """Manifest records mechanism distribution."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(
            source, "case_001", num_intra=2, num_inter=1,
        )
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        mech = manifest["mechanism_distribution"]
        assert "numeric_drift" in mech
        assert "temporal_contradiction" in mech
        # 2 numeric_drift (intra) + 1 temporal_contradiction (inter) = 3 total
        assert mech["numeric_drift"] == pytest.approx(2 / 3, abs=0.01)
        assert mech["temporal_contradiction"] == pytest.approx(1 / 3, abs=0.01)

    def test_manifest_detectability_distribution(self, tmp_path: Path) -> None:
        """Manifest records detectability distribution."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(
            source, "case_001", num_intra=2, num_inter=1,
        )
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        det = manifest["detectability_distribution"]
        assert "single_hop" in det
        assert "multi_hop" in det

    def test_manifest_multiple_cases_aggregated(self, tmp_path: Path) -> None:
        """Manifest aggregates stats across multiple cases."""
        source = tmp_path / "source"
        case1 = _setup_source_case(
            source, "case_001", num_intra=2, num_inter=1, num_distractors=1, num_docs=3,
        )
        case2 = _setup_source_case(
            source, "case_002", num_intra=1, num_inter=2, num_distractors=2, num_docs=2,
        )
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case1, case2],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["case_count"] == 2
        assert manifest["document_count"] == 5
        assert manifest["contradictions_per_scope"]["intra_doc"] == 3
        assert manifest["contradictions_per_scope"]["inter_doc"] == 3
        assert manifest["distractor_count"] == 3


# ---------------------------------------------------------------------------
# Task 2: compute_manifest unit tests
# ---------------------------------------------------------------------------


class TestComputeManifest:
    """Unit tests for the compute_manifest function."""

    def test_empty_version_dir(self, tmp_path: Path) -> None:
        """Manifest of an empty version dir has zero counts."""
        version_dir = tmp_path / "v_empty"
        version_dir.mkdir()

        manifest = compute_manifest(version_dir)
        assert manifest["case_count"] == 0
        assert manifest["document_count"] == 0
        assert manifest["distractor_count"] == 0

    def test_case_with_no_contradictions(self, tmp_path: Path) -> None:
        """Case with empty JSONL files yields zero contradiction counts."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(
            source, "case_001", num_intra=0, num_inter=0, num_distractors=0,
        )
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        manifest = json.loads((output_dir / "v1" / "dataset_manifest.json").read_text())
        assert manifest["contradictions_per_scope"]["intra_doc"] == 0
        assert manifest["contradictions_per_scope"]["inter_doc"] == 0
        assert manifest["distractor_count"] == 0


# ---------------------------------------------------------------------------
# Task 3: Re-injection / base-version (AC3)
# ---------------------------------------------------------------------------


class TestBaseVersion:
    """AC3: --base-version records lineage for re-injection."""

    def test_base_version_in_params(self, tmp_path: Path) -> None:
        """base_version is stored in generation_params.json."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v2",
            case_dirs=[case_dir],
            output_dir=output_dir,
            base_version="v1",
        )

        params = json.loads((output_dir / "v2" / "generation_params.json").read_text())
        assert params["base_version"] == "v1"

    def test_no_base_version_is_null(self, tmp_path: Path) -> None:
        """base_version is null when not provided."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v1",
            case_dirs=[case_dir],
            output_dir=output_dir,
        )

        params = json.loads((output_dir / "v1" / "generation_params.json").read_text())
        assert params["base_version"] is None

    def test_base_version_in_manifest(self, tmp_path: Path) -> None:
        """Manifest also records base_version for traceability."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        output_dir = tmp_path / "datasets"

        package_dataset(
            version="v2",
            case_dirs=[case_dir],
            output_dir=output_dir,
            base_version="v1",
        )

        manifest = json.loads((output_dir / "v2" / "dataset_manifest.json").read_text())
        assert manifest["base_version"] == "v1"


# ---------------------------------------------------------------------------
# Task 1: copy_case unit tests
# ---------------------------------------------------------------------------


class TestCopyCase:
    """Unit tests for the copy_case function."""

    def test_copy_case_creates_subdirs(self, tmp_path: Path) -> None:
        """copy_case creates the expected subdirectory structure."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        dest_dir = tmp_path / "dest" / "case_001"

        copy_case(case_dir, dest_dir)

        assert (dest_dir / "anonymized_docs").is_dir()
        assert (dest_dir / "contradictions").is_dir()
        assert (dest_dir / "distractors").is_dir()
        assert (dest_dir / "metadata").is_dir()
        assert (dest_dir / "validation").is_dir()

    def test_copy_case_file_contents_match(self, tmp_path: Path) -> None:
        """Copied files have identical content to source."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        dest_dir = tmp_path / "dest" / "case_001"

        copy_case(case_dir, dest_dir)

        src_kg = (case_dir / "metadata" / "knowledge_graph.json").read_text()
        dst_kg = (dest_dir / "metadata" / "knowledge_graph.json").read_text()
        assert src_kg == dst_kg

    def test_copy_case_missing_optional_subdir(self, tmp_path: Path) -> None:
        """copy_case handles missing optional subdirectories gracefully."""
        source = tmp_path / "source"
        case_dir = _setup_source_case(source, "case_001")
        # Remove validation dir to simulate optional missing subdir
        import shutil
        shutil.rmtree(case_dir / "validation")
        dest_dir = tmp_path / "dest" / "case_001"

        copy_case(case_dir, dest_dir)

        assert (dest_dir / "anonymized_docs").is_dir()
        assert not (dest_dir / "validation").exists()
