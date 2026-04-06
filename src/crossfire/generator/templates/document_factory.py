"""Document factory — dispatches to the correct template and assembles Document objects."""

from loguru import logger

from crossfire.shared.schemas.corpus import Document, DocumentType
from crossfire.shared.schemas.entities import EntityNode
from crossfire.shared.seed_manager import SeedManager

from .base import BaseTemplate
from .expert_deposition import ExpertDepositionTemplate
from .internal_memo import InternalMemoTemplate
from .investigation_report import InvestigationReportTemplate
from .preliminary_report import PreliminaryReportTemplate
from .press_coverage import PressCoverageTemplate
from .regulatory_filing import RegulatoryFilingTemplate
from .technical_analysis import TechnicalAnalysisTemplate
from .witness_testimony import WitnessTestimonyTemplate

_TEMPLATES: dict[str, BaseTemplate] = {
    "investigation_report": InvestigationReportTemplate(),
    "technical_analysis": TechnicalAnalysisTemplate(),
    "witness_testimony": WitnessTestimonyTemplate(),
    "regulatory_filing": RegulatoryFilingTemplate(),
    "press_coverage": PressCoverageTemplate(),
    "expert_deposition": ExpertDepositionTemplate(),
    "internal_memo": InternalMemoTemplate(),
    "preliminary_report": PreliminaryReportTemplate(),
}


def create_document(
    doc_type: DocumentType,
    entities: list[EntityNode],
    context: dict,
    llm,
    seed_mgr: SeedManager,
    index: int = 0,
) -> tuple[Document | None, str | None]:
    """Create a single document using the appropriate template.

    Args:
        doc_type: One of the 8 DocumentType values.
        entities: Available entities for this subcorpus.
        context: Dict with subcorpus_id, incident_scenario, connectivity_level.
        llm: The llm_call function.
        seed_mgr: SeedManager for reproducibility.
        index: Document index within subcorpus (for seed derivation).

    Returns:
        (Document, None) on success, (None, error_message) on failure.
    """
    template = _TEMPLATES.get(doc_type)
    if template is None:
        return None, f"Unknown document type: {doc_type}"

    subcorpus_id = context.get("subcorpus_id", "unknown")

    content, error = template.generate(entities, context, llm, seed_mgr, index)
    if error:
        return None, error

    seed = seed_mgr.get_seed(f"doc_meta_{doc_type}", index)
    reliability = template.compute_reliability(seed)
    doc_id = f"{subcorpus_id}_{doc_type}_{index:03d}"

    doc = Document(
        id=doc_id,
        document_type=doc_type,
        subcorpus_id=subcorpus_id,
        reliability_signal=reliability,
        content=content,
    )

    logger.debug(f"Created document {doc_id} ({len(content.split())} words)")
    return doc, None
