"""Random baseline — randomly flags document pairs as incoherences (FR22).

Establishes a lower bound for comparison. Uses SeedManager for reproducibility.
"""

import random
from itertools import combinations
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedIncoherence, PipelineReport
from crossfire.shared.seed_manager import SeedManager


def run_random_baseline(
    corpus_path: str,
    seed_manager: SeedManager,
    detection_rate: float = 0.1,
) -> tuple[PipelineReport | None, str | None]:
    """Run random baseline — flag random document pairs as incoherences.

    Args:
        corpus_path: Path to corpus directory.
        seed_manager: For reproducible random selection.
        detection_rate: Fraction of document pairs to flag (0.0-1.0).

    Returns (PipelineReport, None) on success, (None, error) on failure.
    """
    corpus_dir = Path(corpus_path)
    if not corpus_dir.is_dir():
        return None, f"Corpus path is not a directory: {corpus_path}"

    documents = _load_documents(corpus_dir)
    if len(documents) < 2:
        from datetime import datetime, timezone

        return PipelineReport(
            pipeline_mode="baseline-random",
            corpus_path=corpus_path,
            detections=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        ), None

    rng = random.Random(seed_manager.get_seed("random_baseline", 0))
    doc_ids = [d.id for d in documents]
    all_pairs = list(combinations(doc_ids, 2))
    n_flag = max(1, int(len(all_pairs) * detection_rate))
    flagged_pairs = rng.sample(all_pairs, min(n_flag, len(all_pairs)))

    detections = [
        DetectedIncoherence(
            id=f"random_{idx:04d}",
            evidence_references=list(pair),
            confidence=rng.uniform(0.1, 0.9),
            description="Randomly flagged document pair",
        )
        for idx, pair in enumerate(flagged_pairs)
    ]

    from datetime import datetime, timezone

    report = PipelineReport(
        pipeline_mode="baseline-random",
        corpus_path=corpus_path,
        detections=detections,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(f"Random baseline: flagged {len(detections)} pairs from {len(all_pairs)} total")
    return report, None


def _load_documents(corpus_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for jsonl_path in sorted(corpus_dir.glob("subcorpus_*.jsonl")):
        text = jsonl_path.read_text(encoding="utf-8").strip()
        for line in text.split("\n"):
            if line:
                docs.append(Document.model_validate_json(line))
    return docs
