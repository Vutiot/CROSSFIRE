"""Distractor generator — plants legitimate perspective divergences into corpora.

Produces DistractorLabel records for legitimate disagreements that should NOT
be flagged as incoherences. Runs after incoherence injection (Story 3.1).

FRs covered: FR11, FR15
"""

import json
import random
from pathlib import Path

from loguru import logger

from crossfire.shared.llm import llm_call
from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.schemas.incoherences import DistractorLabel
from crossfire.shared.seed_manager import SeedManager

# The 4 divergence types
_DIVERGENCE_TYPES = [
    "expert_opinion",
    "preliminary_vs_final",
    "measurement_methodology",
    "uncertainty_expression",
]


def generate_distractors(
    corpus_dir: Path,
    config: GeneratorConfig,
    entity_graph: EntityGraph,
    incoherence_count: int,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[DistractorLabel] | None, str | None]:
    """Generate legitimate perspective divergences in a corpus.

    Args:
        corpus_dir: Directory containing subcorpus JSONL files.
        config: Generator configuration with distractor_ratio.
        entity_graph: Gold entity graph for context.
        incoherence_count: Number of injected incoherences (used to compute count).
        seed_mgr: SeedManager for reproducibility.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (list[DistractorLabel], None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    rng = random.Random(seed_mgr.get_seed("distractor_generator", 0))

    # Compute distractor count
    count = round(incoherence_count * config.distractor_ratio)
    if count == 0:
        logger.info("Distractor ratio produces 0 distractors — skipping")
        return [], None

    # Load corpus
    docs_by_subcorpus, all_docs = _load_corpus(corpus_dir)
    if not all_docs:
        return None, f"No documents found in {corpus_dir}"

    logger.info(
        f"Generating {count} distractors (ratio={config.distractor_ratio}, "
        f"incoherence_count={incoherence_count}) across {len(all_docs)} documents"
    )

    # Assign divergence types — round-robin then shuffle
    div_types = _assign_divergence_types(count, rng)

    # Execute distractor generation
    labels: list[DistractorLabel] = []
    success_count = 0
    fail_count = 0
    subcorpus_ids = sorted(docs_by_subcorpus.keys())

    for idx in range(count):
        div_type = div_types[idx]

        # Select target document(s)
        scope, target_docs = _select_targets(
            docs_by_subcorpus, subcorpus_ids, rng
        )

        primary_doc = target_docs[0]

        # Generate the distractor via LLM
        label, error = _generate_single_distractor(
            idx=idx,
            div_type=div_type,
            scope=scope,
            target_docs=target_docs,
            primary_doc=primary_doc,
            entity_graph=entity_graph,
            rng=rng,
            llm=llm,
        )

        if error:
            logger.warning(f"Distractor {idx + 1}/{count} failed: {error}")
            fail_count += 1
            continue

        labels.append(label)
        success_count += 1

    # Write modified corpus back
    _write_corpus(corpus_dir, docs_by_subcorpus)

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


def _load_corpus(corpus_dir: Path) -> tuple[dict[str, list[Document]], list[Document]]:
    """Load all subcorpus JSONL files."""
    docs_by_subcorpus: dict[str, list[Document]] = {}
    all_docs: list[Document] = []

    for jsonl_path in sorted(corpus_dir.glob("subcorpus_*.jsonl")):
        docs = []
        for line in jsonl_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                doc = Document.model_validate_json(line)
                docs.append(doc)
                all_docs.append(doc)
        if docs:
            sc_id = docs[0].subcorpus_id
            docs_by_subcorpus[sc_id] = docs

    return docs_by_subcorpus, all_docs


def _assign_divergence_types(count: int, rng: random.Random) -> list[str]:
    """Assign divergence types — round-robin then shuffle for variety."""
    types = []
    for i in range(count):
        types.append(_DIVERGENCE_TYPES[i % len(_DIVERGENCE_TYPES)])
    rng.shuffle(types)
    return types


def _select_targets(
    docs_by_subcorpus: dict[str, list[Document]],
    subcorpus_ids: list[str],
    rng: random.Random,
) -> tuple[str, list[Document]]:
    """Select target documents. Returns (scope, [docs])."""
    # Alternate between intra_doc and intra_corpus scope
    # (inter_corpus less common for legitimate divergences)
    scope_choice = rng.random()
    if scope_choice < 0.5:
        # intra_doc: single document
        sc_id = rng.choice(subcorpus_ids)
        doc = rng.choice(docs_by_subcorpus[sc_id])
        return "intra_doc", [doc]
    elif scope_choice < 0.85:
        # intra_corpus: two docs same subcorpus
        sc_id = rng.choice(subcorpus_ids)
        docs = docs_by_subcorpus[sc_id]
        if len(docs) >= 2:
            pair = rng.sample(docs, 2)
            return "intra_corpus", pair
        return "intra_doc", [rng.choice(docs)]
    else:
        # inter_corpus: two docs different subcorpora
        if len(subcorpus_ids) >= 2:
            sc_pair = rng.sample(subcorpus_ids, 2)
            doc_a = rng.choice(docs_by_subcorpus[sc_pair[0]])
            doc_b = rng.choice(docs_by_subcorpus[sc_pair[1]])
            return "inter_corpus", [doc_a, doc_b]
        sc_id = rng.choice(subcorpus_ids)
        return "intra_doc", [rng.choice(docs_by_subcorpus[sc_id])]


def _generate_single_distractor(
    idx: int,
    div_type: str,
    scope: str,
    target_docs: list[Document],
    primary_doc: Document,
    entity_graph: EntityGraph,
    rng: random.Random,
    llm,
) -> tuple[DistractorLabel | None, str | None]:
    """Generate a single distractor and modify the document."""
    type_instruction = _divergence_instruction(div_type)

    prompt = (
        "You are adding a legitimate perspective divergence to a document. "
        "This is NOT a factual contradiction — it is a valid professional "
        "disagreement, methodological difference, or uncertainty expression "
        "that should NOT be flagged as an incoherence.\n\n"
        f"Divergence type: {div_type}\n"
        f"Instruction: {type_instruction}\n\n"
        f"Document passage:\n{primary_doc.content[:2000]}\n\n"
        "Modify the passage to include this divergence naturally. "
        "Keep the same writing style and voice. The divergence should be "
        "subtle enough that an automated system might consider flagging it, "
        "but a human would recognize it as legitimate.\n\n"
        "Return a JSON object with:\n"
        '- "modified_passage": the full passage with the divergence added\n'
        '- "description": a brief description of the divergence\n\n'
        "Return ONLY valid JSON."
    )

    response, error = llm(prompt, model="gpt-4o-mini", temperature=0)
    if error:
        return None, error

    try:
        data = json.loads(response)
        modified_passage = data["modified_passage"]
        description = data["description"]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse distractor response: {e}"

    # Apply modification to document
    primary_doc.content = modified_passage

    # Build label
    doc_refs = [d.id for d in target_docs]
    label = DistractorLabel(
        id=f"distractor_{idx:04d}",
        scope=scope,
        document_references=doc_refs,
        divergence_type=div_type,
        description=description,
    )

    return label, None


def _divergence_instruction(div_type: str) -> str:
    """Generate type-specific instruction for the LLM."""
    if div_type == "expert_opinion":
        return (
            "Add a sentence where a different expert or investigator offers "
            "a different but plausible interpretation of the evidence. Both "
            "opinions should be professionally valid — this is a disagreement, "
            "not an error. Example: 'While Investigator A attributed the failure "
            "to metal fatigue, Investigator B suggested a manufacturing defect "
            "may have been the primary factor.'"
        )
    elif div_type == "preliminary_vs_final":
        return (
            "Add a reference to a preliminary finding that legitimately differs "
            "from a later conclusion. This represents normal investigation "
            "evolution, not contradiction. Example: 'Initial assessments focused "
            "on pilot error, though subsequent analysis identified mechanical "
            "failure as the primary cause.'"
        )
    elif div_type == "measurement_methodology":
        return (
            "Add a measurement or data point that differs from another due to "
            "different measurement methods or instruments. Both values are valid. "
            "Example: 'Radar indicated an altitude of 16,200 feet, while the "
            "barometric altimeter read 16,450 feet — a discrepancy consistent "
            "with known instrument calibration differences.'"
        )
    elif div_type == "uncertainty_expression":
        return (
            "Add a qualified or hedged statement that expresses legitimate "
            "uncertainty about a finding. Example: 'Evidence suggests the "
            "component may have experienced pre-existing stress, though "
            "definitive confirmation awaits metallurgical analysis.'"
        )
    return f"Add a legitimate {div_type} divergence."


def _write_corpus(
    corpus_dir: Path,
    docs_by_subcorpus: dict[str, list[Document]],
) -> None:
    """Write modified documents back to JSONL files."""
    for sc_id, docs in docs_by_subcorpus.items():
        jsonl_path = corpus_dir / f"subcorpus_{sc_id}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for doc in docs:
                f.write(doc.model_dump_json() + "\n")
    logger.info(f"Modified corpus written to {corpus_dir}")
