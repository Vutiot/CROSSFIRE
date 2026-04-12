"""Contradiction injector — injects controlled contradictions into case corpora.

Uses the 4D design space (scope x mechanism x detectability x system_affinity)
to inject factual contradictions with minimal-pair construction and full metadata
tracking for gold annotation.

Operates on per-case directory layout:
    case_dir/anonymized_docs/*.jsonl

Bug fixes applied (from code review):
    P1: Phantom labels — return failure when original_text not found
    P2: Stale char offsets — compute AFTER replacement
    P3: Bogus fallback — sentinel -1 instead of char_start=0
    P4: File write overwrites — preserve original source filenames
    P6: Markdown fences — strip before JSON parsing
    P7: Forced min 1 — zero rate yields zero injections
    P8: Zero weights crash — fall back to uniform
    P11: Random affinity — use affinity_distribution from params
"""

import json
import re
import random
import shutil
from pathlib import Path
from typing import get_args

from loguru import logger

from crossfire.shared.llm import llm_call
from crossfire.shared.schemas.config import GenerationParams
from crossfire.shared.schemas.contradictions import (
    ContradictionLabel,
    Detectability,
    Difficulty,
    Mechanism,
    Scope,
    SystemAffinity,
)
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.seed_manager import SeedManager

# All valid values from Literal types
_ALL_MECHANISMS: list[str] = list(get_args(Mechanism))
_ALL_SCOPES: list[str] = list(get_args(Scope))
_ALL_DETECTABILITIES: list[str] = list(get_args(Detectability))
_ALL_DIFFICULTIES: list[str] = list(get_args(Difficulty))
_ALL_AFFINITIES: list[str] = list(get_args(SystemAffinity))

# Regex to strip markdown code fences from LLM responses
_FENCE_RE = re.compile(
    r"^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$",
    re.DOTALL,
)


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM responses.

    Handles variations: ```json, ```, triple backticks with/without language tag.
    Returns the inner content if fences are found, otherwise the original text.
    """
    m = _FENCE_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


def _backup_originals(case_dir: Path) -> None:
    """Back up anonymized_docs/ to anonymized_docs_original/ before injection.

    Only creates the backup if it doesn't already exist (idempotent).
    This gives the diff-based verifier a baseline to compare against.
    """
    original_dir = case_dir / "anonymized_docs_original"
    if not original_dir.exists():
        source_dir = case_dir / "anonymized_docs"
        if source_dir.exists():
            shutil.copytree(source_dir, original_dir)
            logger.info(f"Backed up originals to {original_dir}")


def inject_contradictions(
    case_dir: Path,
    params: GenerationParams,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[ContradictionLabel] | None, str | None]:
    """Inject controlled contradictions into a case corpus.

    Args:
        case_dir: Case directory containing ``anonymized_docs/*.jsonl``.
        params: Generation parameters with distribution settings.
        seed_mgr: SeedManager for reproducibility.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (list[ContradictionLabel], None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    # Backup originals before any modifications (for diff-based verification)
    _backup_originals(case_dir)

    rng = random.Random(seed_mgr.get_seed("injector", 0))

    # Step 1: Load all documents from case (P4 fix: track source filenames)
    all_docs, source_map = _load_docs(case_dir)
    if not all_docs:
        return None, f"No documents found in {case_dir / 'anonymized_docs'}"

    total_docs = len(all_docs)

    # Step 2: Compute injection counts per scope (P7 fix: zero rate -> zero count)
    intra_count = round(total_docs * params.contradiction_rate_intra_doc) if params.contradiction_rate_intra_doc > 0 else 0
    # Story 3.2: enable inter_doc injection
    inter_count = round(total_docs * params.contradiction_rate_inter_doc) if params.contradiction_rate_inter_doc > 0 else 0
    if len(all_docs) < 2:
        if inter_count > 0:
            logger.warning("inter_count forced to 0: need at least 2 documents for inter_doc scope")
        inter_count = 0
    count = intra_count + inter_count

    logger.info(
        f"Injecting {count} contradictions ({intra_count} intra_doc, "
        f"{inter_count} inter_doc) into {total_docs} documents"
    )

    if count == 0:
        # Write docs unchanged, return empty labels
        _write_docs(case_dir, all_docs, source_map)
        return [], None

    # Step 3: Build injection plan (P11 fix: use affinity_distribution)
    plan = _build_injection_plan(intra_count, inter_count, params, rng)

    # Step 4: Execute injections
    labels: list[ContradictionLabel] = []
    success_count = 0
    fail_count = 0

    for idx, injection in enumerate(plan):
        logger.debug(f"Injection {idx + 1}/{count}: {injection}")

        label, error = _execute_injection(
            idx=idx,
            injection=injection,
            all_docs=all_docs,
            params=params,
            rng=rng,
            llm=llm,
        )

        if error:
            logger.warning(f"Injection {idx + 1}/{count} failed: {error}")
            fail_count += 1
            continue

        labels.append(label)
        success_count += 1

    # Step 5: Write modified corpus back to disk (P4 fix: preserve source files)
    _write_docs(case_dir, all_docs, source_map)

    # Step 6: Log summary
    scope_counts: dict[str, int] = {}
    for label in labels:
        scope_counts[label.scope] = scope_counts.get(label.scope, 0) + 1

    logger.info(
        f"Injection complete: {success_count}/{count} successful, {fail_count} failed"
    )
    for scope, n in sorted(scope_counts.items()):
        logger.info(f"  {scope}: {n}")

    return labels, None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_docs(case_dir: Path) -> tuple[list[Document], dict[str, str]]:
    """Load all documents from ``case_dir/anonymized_docs/*.jsonl``.

    Returns:
        (docs, source_map) where source_map maps document_id -> source filename.
        P4 fix: tracks original source filename for each document.
    """
    docs: list[Document] = []
    source_map: dict[str, str] = {}
    docs_dir = case_dir / "anonymized_docs"
    if not docs_dir.exists():
        return docs, source_map

    for jsonl_path in sorted(docs_dir.glob("*.jsonl")):
        filename = jsonl_path.name
        for line_num, line in enumerate(jsonl_path.read_text(encoding="utf-8").strip().split("\n"), 1):
            if not line.strip():
                continue
            try:
                doc = Document.model_validate_json(line)
                docs.append(doc)
                source_map[doc.document_id] = filename
            except Exception as e:
                logger.warning(f"Skipping malformed line {line_num} in {filename}: {e}")

    return docs, source_map


def _weighted_choice(distribution: dict[str, float], choices: list[str], rng: random.Random) -> str:
    """Pick a value from *choices* using *distribution* weights (uniform fallback).

    P8 fix: handles all-zero weights by falling back to uniform.
    """
    if distribution:
        weighted = [k for k in choices if k in distribution]
        if weighted:
            weights = [distribution[k] for k in weighted]
            # P8 fix: check sum(weights) > 0 to avoid ValueError
            if sum(weights) > 0:
                return rng.choices(weighted, weights=weights, k=1)[0]
            else:
                logger.warning("All distribution weights are zero, falling back to uniform selection")
                return rng.choice(weighted)
        else:
            logger.warning(
                f"Distribution keys {list(distribution.keys())} "
                f"don't match valid choices {choices}, falling back to uniform"
            )
    return rng.choice(choices)


def _build_injection_plan(
    intra_count: int,
    inter_count: int,
    params: GenerationParams,
    rng: random.Random,
) -> list[dict]:
    """Build a list of injection descriptors.

    P11 fix: uses affinity_distribution from params for system_affinity selection.
    """
    plan: list[dict] = []

    for _ in range(intra_count):
        plan.append({
            "scope": "intra_doc",
            "mechanism": _weighted_choice(params.mechanism_distribution, _ALL_MECHANISMS, rng),
            "detectability": rng.choice(_ALL_DETECTABILITIES),
            "system_affinity": _weighted_choice(params.affinity_distribution, _ALL_AFFINITIES, rng),
            "difficulty": _weighted_choice(params.difficulty_distribution, _ALL_DIFFICULTIES, rng),
        })

    for _ in range(inter_count):
        plan.append({
            "scope": "inter_doc",
            "mechanism": _weighted_choice(params.mechanism_distribution, _ALL_MECHANISMS, rng),
            "detectability": rng.choice(_ALL_DETECTABILITIES),
            "system_affinity": _weighted_choice(params.affinity_distribution, _ALL_AFFINITIES, rng),
            "difficulty": _weighted_choice(params.difficulty_distribution, _ALL_DIFFICULTIES, rng),
        })

    rng.shuffle(plan)
    return plan


def _execute_injection(
    idx: int,
    injection: dict,
    all_docs: list[Document],
    params: GenerationParams,
    rng: random.Random,
    llm,
) -> tuple[ContradictionLabel | None, str | None]:
    """Execute a single injection. Returns (label, None) or (None, error).

    Fixes applied:
        P1: Return failure when original_text not found in document
        P2: Compute char offsets AFTER replacement
        P3: Use sentinel -1/-1 for impossible offset (defensive)
        AC10: Use params.extraction_model / params.reasoning_model
    """
    scope = injection["scope"]
    mechanism = injection["mechanism"]

    # Select target documents based on scope
    target_docs, error = _select_targets(scope, all_docs, rng)
    if error:
        return None, f"Target selection failed: {error}"

    if scope == "inter_doc":
        return _execute_inter_doc_injection(
            idx=idx,
            injection=injection,
            target_docs=target_docs,
            params=params,
            rng=rng,
            llm=llm,
        )

    # --- Intra-doc flow ---
    primary_doc = target_docs[0]

    # Extract facts from primary document (AC10: use extraction_model)
    facts, error = _extract_facts(primary_doc, mechanism, llm, model=params.extraction_model)
    if error:
        return None, f"Fact extraction failed: {error}"

    if not facts:
        return None, "No suitable facts found in document"

    # Select a fact to modify
    selected_fact = rng.choice(facts)

    # Apply minimal-pair modification (AC10: use reasoning_model)
    result, error = _apply_modification(
        doc=primary_doc,
        fact=selected_fact,
        mechanism=mechanism,
        detectability=injection["detectability"],
        rng=rng,
        llm=llm,
        model=params.reasoning_model,
    )
    if error:
        return None, f"Modification failed: {error}"

    original_text, modified_text = result

    # P1 fix: If original_text not found in document, return failure (no phantom label)
    if original_text not in primary_doc.content:
        return None, "original_text not found in document"

    # Apply the modification to the document content
    primary_doc.content = primary_doc.content.replace(original_text, modified_text, 1)

    # P2 fix: Compute char_start/char_end AFTER replacement
    char_start = primary_doc.content.find(modified_text)
    if char_start < 0:
        # P3 fix: defensive sentinel — should not happen after successful replace
        logger.warning(
            f"Injection {idx}: modified_text not found after replacement (defensive sentinel)"
        )
        return None, "modified_text not found after replacement"
    else:
        char_end = char_start + len(modified_text)

    # Build label
    doc_refs = [d.document_id for d in target_docs]
    label = ContradictionLabel(
        scope=scope,
        mechanism=mechanism,
        detectability=injection["detectability"],
        system_affinity=injection["system_affinity"],
        difficulty=injection["difficulty"],
        char_start=char_start,
        char_end=char_end,
        original_text=original_text,
        modified_text=modified_text,
        rationale=f"{mechanism} applied to fact in document {doc_refs[0]}",
        ground_truth=True,
        document_references=doc_refs,
    )

    return label, None


def _execute_inter_doc_injection(
    idx: int,
    injection: dict,
    target_docs: list[Document],
    params: GenerationParams,
    rng: random.Random,
    llm,
) -> tuple[ContradictionLabel | None, str | None]:
    """Execute an inter-document injection.

    target_docs[0] = doc_a (source: original fact lives here)
    target_docs[1] = doc_b (target: contradicting version inserted here)

    The modification prompt references the original fact from doc_a and
    instructs the LLM to insert a contradicting version into doc_b.
    Char offsets reference doc_b (where the modification was made).
    """
    mechanism = injection["mechanism"]
    doc_a = target_docs[0]  # source document
    doc_b = target_docs[1]  # target document

    # Extract facts from doc_a (source)
    facts, error = _extract_facts(doc_a, mechanism, llm, model=params.extraction_model)
    if error:
        return None, f"Fact extraction from source doc failed: {error}"

    if not facts:
        return None, "No suitable facts found in source document"

    selected_fact = rng.choice(facts)

    # Apply inter-doc modification: modify doc_b to contradict fact from doc_a
    result, error = _apply_inter_doc_modification(
        source_doc=doc_a,
        target_doc=doc_b,
        fact=selected_fact,
        mechanism=mechanism,
        detectability=injection["detectability"],
        rng=rng,
        llm=llm,
        model=params.reasoning_model,
    )
    if error:
        return None, f"Inter-doc modification failed: {error}"

    insertion_point, modified_text = result

    # Insert the contradicting text into doc_b at the insertion point
    doc_b.content = doc_b.content[:insertion_point] + modified_text + doc_b.content[insertion_point:]

    # Char offsets reference doc_b
    char_start = insertion_point
    char_end = insertion_point + len(modified_text)

    # Build label with references to both documents
    doc_refs = [doc_a.document_id, doc_b.document_id]
    label = ContradictionLabel(
        scope="inter_doc",
        mechanism=mechanism,
        detectability=injection["detectability"],
        system_affinity=injection["system_affinity"],
        difficulty=injection["difficulty"],
        char_start=char_start,
        char_end=char_end,
        original_text=selected_fact.get("fact", ""),
        modified_text=modified_text,
        rationale=f"{mechanism} applied: fact from document {doc_a.document_id} contradicted in document {doc_b.document_id}",
        ground_truth=True,
        document_references=doc_refs,
    )

    return label, None


_KEY_TERM_RE = re.compile(
    r"""
    (?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)  # Capitalized multi-word phrases (proper nouns)
    | (?:[A-Z]{2,}(?:\s+[A-Z]{2,})*)     # Acronyms (2+ uppercase letters)
    | (?:\d+[,.]?\d*\s*(?:feet|ft|km|m|mph|knots|UTC|hours?|minutes?|seconds?|kg|lbs?|%))  # Numbers with units
    """,
    re.VERBOSE,
)


def _extract_key_terms(content: str) -> set[str]:
    """Extract key terms from document content for entity overlap computation.

    Uses lightweight regex heuristics — no LLM call. Extracts:
    - Capitalized multi-word phrases (proper nouns, names)
    - Acronyms
    - Numbers with units
    """
    return {m.strip().lower() for m in _KEY_TERM_RE.findall(content) if m.strip()}


def _select_inter_doc_targets(
    all_docs: list[Document],
    rng: random.Random,
) -> list[Document]:
    """Select a pair of documents for inter-doc injection, preferring entity overlap.

    Strategy:
    1. Extract key terms from each document
    2. Compute Jaccard similarity between all pairs
    3. Select from top pairs weighted by similarity
    4. Fall back to random pair if no overlap found
    """
    n = len(all_docs)
    if n < 2:
        raise ValueError("Need at least 2 documents for inter-doc selection")

    # Extract terms for each doc
    term_sets = [_extract_key_terms(doc.content) for doc in all_docs]

    # Compute pairwise Jaccard similarity
    pairs: list[tuple[int, int]] = []
    similarities: list[float] = []

    for i in range(n):
        for j in range(i + 1, n):
            if not term_sets[i] and not term_sets[j]:
                sim = 0.0
            else:
                intersection = term_sets[i] & term_sets[j]
                union = term_sets[i] | term_sets[j]
                sim = len(intersection) / len(union) if union else 0.0
            pairs.append((i, j))
            similarities.append(sim)

    # Check if any pair has non-zero overlap
    max_sim = max(similarities) if similarities else 0.0
    if max_sim > 0:
        # Weighted random selection from pairs with overlap
        positive_pairs = [(p, s) for p, s in zip(pairs, similarities) if s > 0]
        selected_pair = rng.choices(
            [p for p, _ in positive_pairs],
            weights=[s for _, s in positive_pairs],
            k=1,
        )[0]
    else:
        # No entity overlap — fall back to random pairing
        selected_pair = rng.choice(pairs)

    i, j = selected_pair
    # Randomly assign source vs target role
    if rng.random() < 0.5:
        return [all_docs[i], all_docs[j]]
    return [all_docs[j], all_docs[i]]


def _select_targets(
    scope: str,
    all_docs: list[Document],
    rng: random.Random,
) -> tuple[list[Document] | None, str | None]:
    """Select target documents based on scope."""
    if scope == "intra_doc":
        if not all_docs:
            return None, "No documents available"
        doc = rng.choice(all_docs)
        return [doc], None

    elif scope == "inter_doc":
        if len(all_docs) < 2:
            return None, "Need at least 2 documents for inter_doc scope"
        pair = _select_inter_doc_targets(all_docs, rng)
        return pair, None

    return None, f"Unknown scope: {scope}"


def _extract_facts(
    doc: Document,
    mechanism: str,
    llm,
    model: str = "claude-sonnet-4-20250514",
) -> tuple[list[dict] | None, str | None]:
    """Extract modifiable facts from a document using LLM.

    AC10: Uses params.extraction_model (passed as model arg).
    """
    prompt = (
        "Extract key factual claims from the following document passage. "
        "For each fact, identify its type (numeric, entity, temporal, causal, "
        "qualification, revision).\n\n"
        f"Document content:\n{doc.content[:2000]}\n\n"
        "Return a JSON object with a 'facts' array. Each fact should have:\n"
        '- "fact": the exact factual statement from the text\n'
        '- "type": one of "numeric", "entity", "temporal", "causal", '
        '"qualification", "revision"\n\n'
        "Return ONLY valid JSON."
    )

    response, error = llm(prompt, model=model, temperature=0)
    if error:
        return None, error

    try:
        # P6 fix: strip markdown fences before parsing
        cleaned = strip_json_fences(response)
        data = json.loads(cleaned)
        facts = data.get("facts", [])
        if not facts:
            return None, "LLM returned no facts"

        # Filter facts by mechanism compatibility
        filtered = _filter_facts_for_mechanism(facts, mechanism)
        return filtered if filtered else facts, None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse fact extraction response: {e}"


def _filter_facts_for_mechanism(facts: list[dict], mechanism: str) -> list[dict]:
    """Filter facts to those compatible with the given mechanism."""
    type_map = {
        "numeric_drift": ["numeric"],
        "entity_swap": ["entity"],
        "causal_inversion": ["causal"],
        "temporal_contradiction": ["temporal"],
        "omission_based_implicit": ["qualification"],
        "temporal_revision_conflict": ["revision", "temporal"],
    }
    target_types = type_map.get(mechanism, [])
    if not target_types:
        return facts

    return [f for f in facts if f.get("type") in target_types]


def _apply_modification(
    doc: Document,
    fact: dict,
    mechanism: str,
    detectability: str,
    rng: random.Random,
    llm,
    model: str = "claude-opus-4-20250514",
) -> tuple[tuple[str, str] | None, str | None]:
    """Apply minimal-pair modification. Returns ((original_text, modified_text), None).

    AC10: Uses params.reasoning_model (passed as model arg).
    """
    fact_text = fact.get("fact", "")
    mechanism_instruction = _mechanism_instruction(mechanism, fact_text, rng)
    detectability_instruction = _detectability_instruction(detectability)

    prompt = (
        "You are modifying a single fact in a document to create a controlled "
        "factual contradiction. You MUST change ONLY the target fact — preserve "
        "all surrounding text, style, and formatting exactly.\n\n"
        f"Document passage:\n{doc.content[:2000]}\n\n"
        f'Target fact to modify: "{fact_text}"\n\n'
        f"Modification type: {mechanism_instruction}\n\n"
        f"Detectability guidance: {detectability_instruction}\n\n"
        "Return a JSON object with exactly these fields:\n"
        '- "original_text": the original factual statement\n'
        '- "modified_text": the new contradictory statement\n\n'
        "Return ONLY valid JSON. Change NOTHING except the target fact."
    )

    response, error = llm(prompt, model=model, temperature=0)
    if error:
        return None, error

    try:
        # P6 fix: strip markdown fences before parsing
        cleaned = strip_json_fences(response)
        data = json.loads(cleaned)
        original_text = data["original_text"]
        modified_text = data["modified_text"]
        return (original_text, modified_text), None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse modification response: {e}"


def _apply_inter_doc_modification(
    source_doc: Document,
    target_doc: Document,
    fact: dict,
    mechanism: str,
    detectability: str,
    rng: random.Random,
    llm,
    model: str = "claude-opus-4-20250514",
) -> tuple[tuple[int, str] | None, str | None]:
    """Apply inter-doc modification: insert contradicting text into target_doc.

    Returns ((insertion_point, modified_text), None) on success.
    The insertion_point is a char offset in target_doc where the contradicting
    text will be inserted. The LLM generates a contradicting version of the
    source fact that fits naturally into the target document.
    """
    fact_text = fact.get("fact", "")
    mechanism_instruction = _mechanism_instruction(mechanism, fact_text, rng)
    detectability_instruction = _detectability_instruction(detectability)

    prompt = (
        "You are inserting a contradicting fact into a target document to create a "
        "cross-document factual contradiction.\n\n"
        f"SOURCE DOCUMENT (contains the original fact):\n{source_doc.content[:1500]}\n\n"
        f'Original fact from source: "{fact_text}"\n\n'
        f"TARGET DOCUMENT (where the contradiction should be inserted):\n{target_doc.content[:1500]}\n\n"
        f"Modification type: {mechanism_instruction}\n\n"
        f"Detectability guidance: {detectability_instruction}\n\n"
        "Generate a sentence that CONTRADICTS the original fact from the source document. "
        "The sentence should fit naturally into the target document's style and context.\n\n"
        "Return a JSON object with exactly these fields:\n"
        '- "modified_text": the contradicting sentence to insert into the target document\n'
        '- "insertion_paragraph": 0-indexed paragraph number in the target document '
        "where the sentence fits best\n\n"
        "Return ONLY valid JSON."
    )

    response, error = llm(prompt, model=model, temperature=0)
    if error:
        return None, error

    try:
        cleaned = strip_json_fences(response)
        data = json.loads(cleaned)
        modified_text = data["modified_text"]
        insertion_paragraph = data.get("insertion_paragraph", 0)

        # Compute insertion point based on paragraph index
        paragraphs = target_doc.content.split("\n")
        # Clamp to valid range
        insertion_paragraph = max(0, min(insertion_paragraph, len(paragraphs) - 1))

        # Insert after the chosen paragraph
        char_pos = 0
        for i in range(min(insertion_paragraph + 1, len(paragraphs))):
            char_pos += len(paragraphs[i]) + 1  # +1 for the newline

        # Clamp to content length
        char_pos = min(char_pos, len(target_doc.content))

        # Add spacing around insertion
        modified_text = " " + modified_text.strip() + " "

        return (char_pos, modified_text), None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse inter-doc modification response: {e}"


def _mechanism_instruction(mechanism: str, fact_text: str, rng: random.Random) -> str:
    """Generate mechanism-specific instruction for the LLM."""
    if mechanism == "numeric_drift":
        return (
            "Change a numeric value in this fact to a different but plausible number. "
            "The new number should be different enough to be wrong but plausible "
            "in the domain (e.g., change altitude, speed, date, or count)."
        )
    elif mechanism == "entity_swap":
        return "Replace an entity name with a different entity of the same type."
    elif mechanism == "causal_inversion":
        return (
            "Reverse the cause-effect relationship in this fact. "
            "If A caused B, change it so B caused A, or introduce a contradictory "
            "causal chain."
        )
    elif mechanism == "temporal_contradiction":
        return (
            "Change the temporal information to create a timeline contradiction. "
            "Modify dates, sequence of events, or temporal relationships."
        )
    elif mechanism == "omission_based_implicit":
        return (
            "Remove or modify a qualifying statement so that the remaining facts "
            "become implicitly contradictory. For example, remove 'preliminary' "
            "from 'preliminary findings' to conflict with a differing final report."
        )
    elif mechanism == "temporal_revision_conflict":
        return (
            "Create a conflict between preliminary and final assessments. "
            "Change the fact so it contradicts what another assessment stage concluded."
        )
    return f"Apply {mechanism} modification to this fact."


def _detectability_instruction(detectability: str) -> str:
    """Generate detectability-specific guidance for the LLM."""
    if detectability == "single_hop":
        return (
            "Make the contradiction detectable by comparing two directly related "
            "statements. The change should be obvious when the two facts are compared."
        )
    elif detectability == "multi_hop":
        return (
            "Make the contradiction require combining multiple pieces of evidence. "
            "The change should not be obvious from any single comparison."
        )
    elif detectability == "entity_resolution_dependent":
        return (
            "Make the contradiction dependent on recognizing that two differently-named "
            "entities refer to the same thing. Use an alias or abbreviation."
        )
    return "Make the contradiction appropriately detectable."


def _write_docs(case_dir: Path, docs: list[Document], source_map: dict[str, str]) -> None:
    """Write modified documents back to JSONL files, preserving original filenames.

    P4 fix: Uses source_map to write each document back to its original source file,
    instead of grouping by document_type which would lose the original file structure.
    """
    docs_dir = case_dir / "anonymized_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Group docs by their original source file
    by_file: dict[str, list[Document]] = {}
    for doc in docs:
        filename = source_map.get(doc.document_id, f"{doc.document_type}.jsonl")
        by_file.setdefault(filename, []).append(doc)

    for filename, file_docs in by_file.items():
        jsonl_path = docs_dir / filename
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for doc in file_docs:
                f.write(doc.model_dump_json() + "\n")

    logger.info(f"Modified corpus written to {docs_dir}")
