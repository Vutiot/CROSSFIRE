"""Scraper configuration."""

from pathlib import Path

from pydantic import BaseModel, Field


class DocketTarget(BaseModel):
    """A target docket, identified by NTSBNumber or ProjectID."""

    ntsb_id: str
    project_id: int | None = None
    description: str = ""


# Major NTSB accident dockets selected for entity overlap (Boeing, FAA, airlines)
# Mix of NTSBNumber-accessible and ProjectID-accessible dockets
DEFAULT_TARGET_DOCKETS: list[DocketTarget] = [
    # Primary: accessible via NTSBNumber (newer docket system)
    DocketTarget(ntsb_id="DCA24MA063", description="Alaska Airlines 1282 — Boeing 737 MAX 9 door plug"),
    DocketTarget(ntsb_id="DCA19MA086", description="Ethiopian Airlines 302 — Boeing 737 MAX 8"),
    # Secondary: accessible via ProjectID (found via scan)
    DocketTarget(ntsb_id="ERA18MA099", project_id=96850, description="Major aviation — 79 docs, FAA"),
    DocketTarget(ntsb_id="CEN17MA183", project_id=95175, description="Major aviation — 67 docs, FAA"),
    DocketTarget(ntsb_id="ERA18FA120", project_id=96975, description="Fatal aviation — 44 docs, FAA"),
    DocketTarget(ntsb_id="DCA19FA089", project_id=99050, description="DCA fatal aviation — 32 docs, FAA"),
    DocketTarget(ntsb_id="WPR19FA080", project_id=98950, description="Fatal aviation — 32 docs, FAA"),
    DocketTarget(ntsb_id="ERA19FA034", project_id=98575, description="Fatal aviation — 31 docs"),
]

PROJECT_ROOT = Path(__file__).resolve().parents[4]


class QualityThresholds(BaseModel):
    """Thresholds for text extraction quality assessment."""

    min_char_ratio: float = Field(default=0.85, ge=0.0, le=1.0)
    min_word_count: int = Field(default=100, ge=0)
    min_avg_word_length: float = Field(default=2.5, ge=0.0)
    max_avg_word_length: float = Field(default=12.0, ge=0.0)
    min_clean_extraction_rate: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Fraction of docs that must pass quality"
    )


class QualityGates(BaseModel):
    """Thresholds for the iterative pipeline quality gates."""

    min_dockets_with_docs: int = Field(default=5, ge=1)
    min_docs_per_docket: int = Field(default=10, ge=1)
    min_document_types: int = Field(default=6, ge=1)
    min_shared_entities: int = Field(default=10, ge=1)


class ScraperConfig(BaseModel):
    """Configuration for the NTSB scraper pipeline."""

    target_dockets: list[DocketTarget] = Field(default_factory=lambda: list(DEFAULT_TARGET_DOCKETS))
    raw_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "ntsb_raw")
    extracted_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "ntsb_extracted")
    analysis_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "data" / "ntsb_analysis")
    request_delay: float = Field(default=1.5, ge=0.0, description="Seconds between HTTP requests")
    max_retries: int = Field(default=3, ge=0)
    timeout: float = Field(default=30.0, ge=1.0, description="HTTP request timeout in seconds")
    max_iterations: int = Field(default=3, ge=1, description="Max iterative refinement passes")
    quality: QualityThresholds = Field(default_factory=QualityThresholds)
    gates: QualityGates = Field(default_factory=QualityGates)
