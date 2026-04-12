"""Distractor generator — labels legitimate perspective divergences in case corpora.

Produces DistractorLabel records for legitimate disagreements that should NOT
be flagged as contradictions. Runs after contradiction injection.

KEY DESIGN: Distractors do NOT modify documents. Unlike contradictions (which
alter doc content), a distractor labels an *existing* passage as a legitimate
divergence. The LLM identifies naturally divergent content and describes it.

Operates on per-case directory layout:
    case_dir/anonymized_docs/*.jsonl
    case_dir/distractors/distractor_labels.jsonl  (output)

Bug fixes applied (from code review):
    P5: No longer replaces doc.content — documents stay unchanged.
"""

import json
import random
from pathlib import Path

from loguru import logger

from crossfire.generator.injector import strip_json_fences
from crossfire.shared.llm import llm_call
from crossfire.shared.schemas.config import GenerationParams
from crossfire.shared.schemas.contradictions import DistractorLabel, Scope
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.seed_manager import SeedManager

# The 4 divergence types
_DIVERGENCE_TYPES = [
    "expert_opinion",
    "preliminary_vs_final",
    "measurement_methodology",
    "uncertainty_expression",
]


def generate_distractors(
    case_dir: Path,
    contradiction_count: int,
    params: GenerationParams,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[DistractorLabel] | None, str | None]:
    """Generate legitimate perspective divergence labels for a case corpus.

    Distractors do NOT modify document content. The LLM reads existing docs
    and identifies passages that represent legitimate professional disagreement,
    methodological differences, or uncertainty expressions.

    Args:
        case_dir: Case directory containing ``anonymized_docs/*.jsonl``.
        contradiction_count: Number of injected contradictions (used to compute count).
        params: Generation parameters with ``distractor_ratio``.
        seed_mgr: SeedManager for reproducibility.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (list[DistractorLabel], None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    rng = random.Random(seed_mgr.get_seed("distractor_generator", 0))

    # Compute distractor count
    count = round(contradiction_count * params.distractor_ratio)
    if count == 0:
        logger.info("Distractor ratio produces 0 distractors — skipping")
        return [], None

    # Load documents (read-only — distractors don't modify content)
    all_docs = _load_docs(case_dir)
    if not all_docs:
        return None, f"No documents found in {case_dir / 'anonymized_docs'}"

    logger.info(
        f"Generating {count} distractors (ratio={params.distractor_ratio}, "
        f"contradiction_count={contradiction_count}) across {len(all_docs)} documents"
    )

    # Assign divergence types — round-robin then shuffle for variety
    div_types = _assign_divergence_types(count, rng)

    # Execute distractor generation
    labels: list[DistractorLabel] = []
    success_count = 0
    fail_count = 0

    for idx in range(count):
        div_type = div_types[idx]

        # Select target document(s) — intra_doc or inter_doc scope
        scope, target_docs = _select_targets(all_docs, rng)

        primary_doc = target_docs[0]

        # Generate the distractor via LLM (read-only: no document mutation)
        label, error = _generate_single_distractor(
            idx=idx,
            div_type=div_type,
            scope=scope,
            target_docs=target_docs,
            primary_doc=primary_doc,
            rng=rng,
            llm=llm,
            model=params.reasoning_model,
        )

        if error:
            logger.warning(f"Distractor {idx + 1}/{count} failed: {error}")
            fail_count += 1
            continue

        labels.append(label)
        success_count += 1

    # Write distractor labels to JSONL (no _write_docs — documents stay unchanged)
    _write_labels(case_dir, labels)

    # Log summary
    type_counts: dict[str, int] = {}
    for label in labels:
        type_counts[label.divergence_type] = type_counts.get(label.divergence_type, 0) + 1

    logger.info(
        f"Distractor generation complete: {success_count}/{count} successful, "
        f"{fail_count} failed"
    )
    for dt, n in sorted(type_counts.items()):
        logger.info(f"  {dt}: {n}")

    return labels, None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_docs(case_dir: Path) -> list[Document]:
    """Load all documents from ``case_dir/anonymized_docs/*.jsonl``."""
    docs: list[Document] = []
    docs_dir = case_dir / "anonymized_docs"
    if not docs_dir.exists():
        return docs

    for jsonl_path in sorted(docs_dir.glob("*.jsonl")):
        for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                doc = Document.model_validate_json(line)
                docs.append(doc)

    return docs


def _assign_divergence_types(count: int, rng: random.Random) -> list[str]:
    """Assign divergence types — round-robin then shuffle for variety."""
    types = []
    for i in range(count):
        types.append(_DIVERGENCE_TYPES[i % len(_DIVERGENCE_TYPES)])
    rng.shuffle(types)
    return types


def _select_targets(
    all_docs: list[Document],
    rng: random.Random,
) -> tuple[str, list[Document]]:
    """Select target documents. Returns (scope, [docs])."""
    # 50/50 split between intra_doc and inter_doc
    if rng.random() < 0.5:
        doc = rng.choice(all_docs)
        return "intra_doc", [doc]
    else:
        if len(all_docs) >= 2:
            pair = rng.sample(all_docs, 2)
            return "inter_doc", pair
        return "intra_doc", [rng.choice(all_docs)]


def _generate_single_distractor(
    idx: int,
    div_type: str,
    scope: str,
    target_docs: list[Document],
    primary_doc: Document,
    rng: random.Random,
    llm,
    model: str,
) -> tuple[DistractorLabel | None, str | None]:
    """Identify a legitimate perspective divergence in an existing document.

    Does NOT modify document content. The LLM reads the document and describes
    an existing or plausible divergence passage.
    """
    type_instruction = _divergence_instruction(div_type)

    # Build context from target docs
    if scope == "inter_doc" and len(target_docs) >= 2:
        doc_context = (
            f"Document A ({target_docs[0].document_id}):\n"
            f"{target_docs[0].content}\n\n"
            f"Document B ({target_docs[1].document_id}):\n"
            f"{target_docs[1].content}"
        )
    else:
        doc_context = (
            f"Document ({primary_doc.document_id}):\n"
            f"{primary_doc.content}"
        )

    prompt = (
        "You are identifying a legitimate perspective divergence in a document. "
        "This is NOT a factual contradiction — it is a valid professional "
        "disagreement, methodological difference, or uncertainty expression "
        "that should NOT be flagged as a contradiction.\n\n"
        f"Divergence type: {div_type}\n"
        f"Instruction: {type_instruction}\n\n"
        f"{doc_context}\n\n"
        "Identify an existing passage or aspect of the document(s) that represents "
        "a legitimate perspective divergence. Describe the divergence you found.\n\n"
        "Return a JSON object with:\n"
        '- "divergence_type": the type of divergence (must be exactly: '
        f'"{div_type}")\n'
        '- "description": a clear description of the legitimate divergence\n'
        f'- "scope": "{scope}"\n\n'
        "Return ONLY valid JSON."
    )

    response, error = llm(prompt, model=model, temperature=0)
    if error:
        return None, error

    try:
        cleaned = strip_json_fences(response)
        data = json.loads(cleaned)
        description = data["description"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse distractor response: {e}"

    # Build label — no document mutation
    doc_refs = [d.document_id for d in target_docs]
    label = DistractorLabel(
        scope=scope,
        divergence_type=div_type,
        document_references=doc_refs,
        description=description,
    )

    return label, None


def _divergence_instruction(div_type: str) -> str:
    """Generate type-specific instruction for the LLM."""
    if div_type == "expert_opinion":
        return (
            "Look for a passage where different experts or investigators offer "
            "different but plausible interpretations of the evidence. Both "
            "opinions should be professionally valid — this is a disagreement, "
            "not an error. Example: 'While Investigator A attributed the failure "
            "to metal fatigue, Investigator B suggested a manufacturing defect "
            "may have been the primary factor.'"
        )
    elif div_type == "preliminary_vs_final":
        return (
            "Look for a reference to a preliminary finding that legitimately differs "
            "from a later conclusion. This represents normal investigation "
            "evolution, not contradiction. Example: 'Initial assessments focused "
            "on pilot error, though subsequent analysis identified mechanical "
            "failure as the primary cause.'"
        )
    elif div_type == "measurement_methodology":
        return (
            "Look for a measurement or data point that differs from another due to "
            "different measurement methods or instruments. Both values are valid. "
            "Example: 'Radar indicated an altitude of 16,200 feet, while the "
            "barometric altimeter read 16,450 feet — a discrepancy consistent "
            "with known instrument calibration differences.'"
        )
    elif div_type == "uncertainty_expression":
        return (
            "Look for a qualified or hedged statement that expresses legitimate "
            "uncertainty about a finding. Example: 'Evidence suggests the "
            "component may have experienced pre-existing stress, though "
            "definitive confirmation awaits metallurgical analysis.'"
        )
    return f"Identify a legitimate {div_type} divergence."


def _write_labels(case_dir: Path, labels: list[DistractorLabel]) -> None:
    """Write distractor labels to ``case_dir/distractors/distractor_labels.jsonl``."""
    out_dir = case_dir / "distractors"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "distractor_labels.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for label in labels:
            f.write(label.model_dump_json() + "\n")

    logger.info(f"Wrote {len(labels)} distractor labels to {out_path}")
