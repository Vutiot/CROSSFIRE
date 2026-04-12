"""Random baseline — randomly flags document pairs as contradictions (FR22).

Establishes a lower bound for comparison. Uses SeedManager for reproducibility.
"""

import random
from itertools import combinations
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.seed_manager import SeedManager


def run_random_baseline(
    case_dir: str,
    seed_manager: SeedManager,
    detection_rate: float = 0.1,
) -> tuple[PipelineReport | None, str | None]:
    """Run random baseline — flag random document pairs as contradictions.

    Args:
        case_dir: Path to case directory.
        seed_manager: For reproducible random selection.
        detection_rate: Fraction of document pairs to flag (0.0-1.0).

    Returns (PipelineReport, None) on success, (None, error) on failure.
    """
    case_path = Path(case_dir)
    if not case_path.is_dir():
        return None, f"Case directory is not a directory: {case_dir}"

    documents = _load_documents(case_path)
    if len(documents) < 2:
        from datetime import datetime, timezone

        return PipelineReport(
            pipeline_mode="baseline-random",
            case_dir=case_dir,
            detections=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        ), None

    rng = random.Random(seed_manager.get_seed("random_baseline", 0))
    doc_ids = [d.document_id for d in documents]
    all_pairs = list(combinations(doc_ids, 2))
    n_flag = max(1, int(len(all_pairs) * detection_rate))
    flagged_pairs = rng.sample(all_pairs, min(n_flag, len(all_pairs)))

    detections = [
        DetectedContradiction(
            scope="inter_doc",
            document_references=list(pair),
            text_span_start=0,
            text_span_end=0,
            evidence_text="Randomly flagged document pair",
            confidence=rng.uniform(0.1, 0.9),
            description="Randomly flagged document pair",
        )
        for pair in flagged_pairs
    ]

    from datetime import datetime, timezone

    report = PipelineReport(
        pipeline_mode="baseline-random",
        case_dir=case_dir,
        detections=detections,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(f"Random baseline: flagged {len(detections)} pairs from {len(all_pairs)} total")
    return report, None


def _load_documents(case_path: Path) -> list[Document]:
    docs: list[Document] = []
    anon_dir = case_path / "anonymized_docs"
    if not anon_dir.is_dir():
        return docs
    for jsonl_path in sorted(anon_dir.glob("*.jsonl")):
        text = jsonl_path.read_text(encoding="utf-8").strip()
        for line in text.split("\n"):
            if line:
                docs.append(Document.model_validate_json(line))
    return docs
