"""Hypothesis-only baseline — surface feature detection for contamination validation (FR21).

Evaluates whether contradictions are detectable from surface features alone
(document length, vocabulary complexity, formatting) without reading actual
content meaning. If this baseline scores significantly above random, it
indicates contamination in the generated corpus.
"""

import math
import re
from itertools import combinations
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.seed_manager import SeedManager


def run_hypothesis_only_baseline(
    case_dir: str,
    seed_manager: SeedManager,
    top_k: int = 10,
) -> tuple[PipelineReport | None, str | None]:
    """Run hypothesis-only baseline using surface features.

    Extracts surface features from each document (length, vocabulary stats,
    formatting patterns) and flags document pairs with unusual feature
    divergence as potential contradictions.

    Args:
        case_dir: Path to case directory.
        seed_manager: For reproducibility.
        top_k: Maximum number of pairs to flag.

    Returns (PipelineReport, None) on success, (None, error) on failure.
    """
    case_path = Path(case_dir)
    if not case_path.is_dir():
        return None, f"Case directory is not a directory: {case_dir}"

    documents = _load_documents(case_path)
    if len(documents) < 2:
        from datetime import datetime, timezone

        return PipelineReport(
            pipeline_mode="baseline-hypothesis-only",
            case_dir=case_dir,
            detections=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        ), None

    # Extract surface features for each document
    features = {doc.document_id: _extract_features(doc) for doc in documents}

    # Score pairs by feature divergence
    scored_pairs: list[tuple[str, str, float]] = []
    for doc_a, doc_b in combinations(documents, 2):
        score = _feature_divergence(features[doc_a.document_id], features[doc_b.document_id])
        if score > 0:
            scored_pairs.append((doc_a.document_id, doc_b.document_id, score))

    scored_pairs.sort(key=lambda x: x[2], reverse=True)
    top_pairs = scored_pairs[:top_k]

    max_score = top_pairs[0][2] if top_pairs else 1.0
    detections = [
        DetectedContradiction(
            scope="inter_doc",
            document_references=[pair[0], pair[1]],
            text_span_start=0,
            text_span_end=0,
            evidence_text="Surface feature divergence detected",
            confidence=min(pair[2] / max_score, 1.0) if max_score > 0 else 0.0,
            description="Surface feature divergence detected",
        )
        for pair in top_pairs
    ]

    from datetime import datetime, timezone

    report = PipelineReport(
        pipeline_mode="baseline-hypothesis-only",
        case_dir=case_dir,
        detections=detections,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(f"Hypothesis-only baseline: flagged {len(detections)} pairs")
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


def _extract_features(doc: Document) -> dict[str, float]:
    """Extract surface-level features without reading content meaning."""
    content = doc.content
    words = re.findall(r"[a-z0-9]+", content.lower())
    word_count = len(words)
    unique_words = len(set(words))
    char_count = len(content)
    sentence_count = max(1, len(re.findall(r"[.!?]+", content)))
    paragraph_count = max(1, len(content.split("\n\n")))
    digit_ratio = sum(c.isdigit() for c in content) / max(1, char_count)
    upper_ratio = sum(c.isupper() for c in content) / max(1, char_count)

    return {
        "word_count": float(word_count),
        "unique_ratio": unique_words / max(1, word_count),
        "avg_word_length": sum(len(w) for w in words) / max(1, word_count),
        "avg_sentence_length": word_count / sentence_count,
        "paragraph_count": float(paragraph_count),
        "digit_ratio": digit_ratio,
        "upper_ratio": upper_ratio,
    }


def _feature_divergence(features_a: dict[str, float], features_b: dict[str, float]) -> float:
    """Compute divergence between two feature vectors (Euclidean distance, normalized)."""
    total = 0.0
    for key in features_a:
        a = features_a[key]
        b = features_b.get(key, 0.0)
        # Normalize by max to prevent scale bias
        scale = max(abs(a), abs(b), 1.0)
        total += ((a - b) / scale) ** 2
    return math.sqrt(total)
