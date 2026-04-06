"""Pydantic models for NTSB scraper data structures."""

from pydantic import BaseModel, Field


# --- Docket & Document models ---


class DocumentEntry(BaseModel):
    """A single document listed in an NTSB docket."""

    item_number: int
    title: str
    file_type: str
    page_count: int = 0
    download_url: str
    group: str = ""


class DocketManifest(BaseModel):
    """Parsed document listing for one NTSB docket."""

    ntsb_id: str
    url: str
    document_count: int = 0
    documents: list[DocumentEntry] = Field(default_factory=list)


# --- Extraction & Quality models ---


class ExtractionQuality(BaseModel):
    """Quality metrics for extracted text from a single document."""

    char_ratio: float = Field(ge=0.0, le=1.0, description="Ratio of printable chars to total")
    avg_word_length: float = Field(ge=0.0)
    word_count: int = Field(ge=0)
    line_count: int = Field(ge=0)
    passed: bool = False


class ExtractedDocument(BaseModel):
    """An extracted document with metadata and quality info."""

    ntsb_id: str
    item_number: int
    title: str
    file_type: str
    document_type: str = ""
    text: str = ""
    quality: ExtractionQuality | None = None
    group: str = ""


# --- Classification models ---


class TypeDistribution(BaseModel):
    """Document type frequency for a docket or corpus."""

    counts: dict[str, int] = Field(default_factory=dict)
    total: int = 0


# --- Entity models ---


class EntityMention(BaseModel):
    """An entity found in a document."""

    name: str
    entity_type: str
    ntsb_id: str
    document_title: str


class EntityProfile(BaseModel):
    """Aggregated info about a unique entity across the corpus."""

    canonical_name: str
    entity_type: str
    aliases: list[str] = Field(default_factory=list)
    docket_ids: list[str] = Field(default_factory=list)
    mention_count: int = 0


# --- Analysis Report models ---


class DocumentTypeProfile(BaseModel):
    """Structure characteristics for one document type."""

    document_type: str
    count: int = 0
    word_count_min: int = 0
    word_count_max: int = 0
    word_count_mean: float = 0.0
    avg_line_count: float = 0.0
    example_titles: list[str] = Field(default_factory=list)
    structural_notes: list[str] = Field(default_factory=list)


class DocumentTypeTaxonomy(BaseModel):
    """Discovered document type taxonomy."""

    types: list[str] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    total_documents: int = 0
    discovery_notes: list[str] = Field(default_factory=list)


class EntityAnalysis(BaseModel):
    """Entity extraction summary."""

    entity_types: list[str] = Field(default_factory=list)
    total_unique_entities: int = 0
    entities_by_type: dict[str, list[str]] = Field(default_factory=dict)
    top_entities: list[EntityProfile] = Field(default_factory=list)


class CrossDocketPatterns(BaseModel):
    """Cross-docket entity sharing analysis."""

    sharing_matrix: dict[str, list[str]] = Field(
        default_factory=dict, description="entity_name → list of docket IDs"
    )
    shared_entity_count: int = Field(default=0, description="Entities appearing in 2+ dockets")
    connectivity_score: float = Field(default=0.0, description="Avg dockets per shared entity")
    naming_variations: dict[str, list[str]] = Field(
        default_factory=dict, description="canonical_name → list of surface forms"
    )


class DocketSummary(BaseModel):
    """Summary of one scraped docket."""

    ntsb_id: str
    total_documents: int = 0
    extracted_documents: int = 0
    clean_documents: int = 0
    clean_rate: float = 0.0
    type_distribution: dict[str, int] = Field(default_factory=dict)


class NTSBAnalysisReport(BaseModel):
    """Final structured analysis report — output of Story 2.1."""

    generated_at: str
    dockets_analyzed: list[DocketSummary] = Field(default_factory=list)
    document_type_taxonomy: DocumentTypeTaxonomy = Field(default_factory=DocumentTypeTaxonomy)
    entity_analysis: EntityAnalysis = Field(default_factory=EntityAnalysis)
    cross_docket_patterns: CrossDocketPatterns = Field(default_factory=CrossDocketPatterns)
    document_characteristics: dict[str, DocumentTypeProfile] = Field(default_factory=dict)
    data_quality_notes: list[str] = Field(default_factory=list)
    synthesis_recommendations: list[str] = Field(default_factory=list)


# --- Quality Gate models ---


class GateResult(BaseModel):
    """Result of a single quality gate check."""

    name: str
    passed: bool
    metric: str
    threshold: str
    actual: str
    action: str = ""


class QualityGateResults(BaseModel):
    """Aggregated results of all quality gate checks."""

    passed: bool = False
    gates: list[GateResult] = Field(default_factory=list)
    failed_gates: list[str] = Field(default_factory=list)
