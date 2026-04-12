"""BM25 keyword contradiction baseline (FR22).

Uses TF-IDF-based keyword matching to find potentially contradictory passages
across documents. Purely computational — no LLM calls.
"""

import math
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

from loguru import logger

from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction, PipelineReport
from crossfire.shared.seed_manager import SeedManager

# Negation and contradiction signal words
_CONTRADICTION_SIGNALS = {
    "not", "no", "never", "none", "neither", "nor", "without",
    "denied", "failed", "incorrect", "false", "contrary", "opposite",
    "however", "but", "although", "despite", "unlike",
}


def run_bm25_baseline(
    case_dir: str,
    seed_manager: SeedManager,
    top_k: int = 10,
) -> tuple[PipelineReport | None, str | None]:
    """Run BM25 keyword-contradiction baseline.

    For each document pair, computes keyword overlap + contradiction signal
    score. Top-scoring pairs are flagged as potential contradictions.

    Args:
        case_dir: Path to case directory.
        seed_manager: For reproducibility (used in tie-breaking).
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
            pipeline_mode="baseline-bm25",
            case_dir=case_dir,
            detections=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
        ), None

    # Build document term frequencies and IDF
    doc_terms = {doc.document_id: _tokenize(doc.content) for doc in documents}
    idf = _compute_idf(doc_terms)

    # Score all document pairs
    scored_pairs: list[tuple[str, str, float]] = []
    for doc_a, doc_b in combinations(documents, 2):
        score = _contradiction_score(
            doc_terms[doc_a.document_id], doc_terms[doc_b.document_id], idf
        )
        if score > 0:
            scored_pairs.append((doc_a.document_id, doc_b.document_id, score))

    # Sort by score descending, take top_k
    scored_pairs.sort(key=lambda x: x[2], reverse=True)
    top_pairs = scored_pairs[:top_k]

    # Normalize scores to 0-1 confidence
    max_score = top_pairs[0][2] if top_pairs else 1.0
    detections = [
        DetectedContradiction(
            scope="inter_doc",
            document_references=[pair[0], pair[1]],
            text_span_start=0,
            text_span_end=0,
            evidence_text="BM25 keyword contradiction signal",
            confidence=min(pair[2] / max_score, 1.0) if max_score > 0 else 0.0,
            description="BM25 keyword contradiction signal",
        )
        for pair in top_pairs
    ]

    from datetime import datetime, timezone

    report = PipelineReport(
        pipeline_mode="baseline-bm25",
        case_dir=case_dir,
        detections=detections,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    logger.info(f"BM25 baseline: flagged {len(detections)} pairs")
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


def _tokenize(text: str) -> Counter:
    """Simple whitespace + punctuation tokenizer, lowercased."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return Counter(words)


def _compute_idf(doc_terms: dict[str, Counter]) -> dict[str, float]:
    """Compute inverse document frequency for all terms."""
    n_docs = len(doc_terms)
    df: Counter = Counter()
    for terms in doc_terms.values():
        for term in terms:
            df[term] += 1
    return {term: math.log((n_docs + 1) / (freq + 1)) for term, freq in df.items()}


def _contradiction_score(
    terms_a: Counter, terms_b: Counter, idf: dict[str, float]
) -> float:
    """Score a document pair by keyword overlap weighted by contradiction signals."""
    shared_terms = set(terms_a) & set(terms_b)
    if not shared_terms:
        return 0.0

    # Base score: shared term IDF overlap
    overlap_score = sum(idf.get(t, 0) for t in shared_terms)

    # Contradiction signal boost: if one doc has negation words near shared terms
    all_terms_a = set(terms_a)
    all_terms_b = set(terms_b)
    signal_a = all_terms_a & _CONTRADICTION_SIGNALS
    signal_b = all_terms_b & _CONTRADICTION_SIGNALS

    # Asymmetric contradiction: one doc has signals the other doesn't
    asymmetric_signals = signal_a.symmetric_difference(signal_b)
    contradiction_boost = len(asymmetric_signals) * 0.5

    return overlap_score * (1.0 + contradiction_boost)
