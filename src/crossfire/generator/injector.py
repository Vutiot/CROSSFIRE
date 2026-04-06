"""Incoherence injector — injects controlled incoherences into generated corpora.

Uses the 4D design space (scope × mechanism × detectability × system_affinity)
to inject factual incoherences with minimal-pair construction and full metadata
tracking for gold annotation.

FRs covered: FR6, FR7, FR8, FR9, FR10, FR11, FR12
"""

import json
import random
from pathlib import Path
from typing import get_args

from loguru import logger

from crossfire.shared.llm import llm_call
from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityGraph, EntityNode
from crossfire.shared.schemas.incoherences import (
    Detectability,
    IncoherenceLabel,
    Mechanism,
    Scope,
    SystemAffinity,
)
from crossfire.shared.seed_manager import SeedManager

# All valid mechanism values from the Literal type
_ALL_MECHANISMS: list[str] = list(get_args(Mechanism))

# All valid scope values
_ALL_SCOPES: list[str] = list(get_args(Scope))

# All valid detectability values
_ALL_DETECTABILITIES: list[str] = list(get_args(Detectability))


def inject_incoherences(
    corpus_dir: Path,
    config: GeneratorConfig,
    entity_graph: EntityGraph,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[list[IncoherenceLabel] | None, str | None]:
    """Inject controlled incoherences into a generated corpus.

    Args:
        corpus_dir: Directory containing subcorpus JSONL files and entity graph.
        config: Generator configuration with incoherence settings.
        entity_graph: Gold entity graph for entity-aware injection.
        seed_mgr: SeedManager for reproducibility.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (list[IncoherenceLabel], None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    rng = random.Random(seed_mgr.get_seed("injector", 0))

    # Step 1: Load all documents from corpus
    docs_by_subcorpus, all_docs = _load_corpus(corpus_dir)
    if not all_docs:
        return None, f"No documents found in {corpus_dir}"

    total_docs = len(all_docs)
    inc_config = config.incoherences

    # Step 2: Compute injection count
    count = _compute_count(inc_config.count, total_docs)
    logger.info(
        f"Injecting {count} incoherences into {total_docs} documents "
        f"across {len(docs_by_subcorpus)} subcorpora"
    )

    # Step 3: Normalize system_affinity (hyphens → underscores)
    affinity = inc_config.system_affinity.replace("-", "_")

    # Step 4: Distribute across scope axis
    scope_alloc = _distribute(
        count,
        {
            "intra_doc": inc_config.scope_distribution.intra_doc,
            "intra_corpus": inc_config.scope_distribution.intra_corpus,
            "inter_corpus": inc_config.scope_distribution.inter_corpus,
        },
        rng,
    )

    # Step 5: Distribute across detectability axis
    detect_alloc = _distribute(
        count,
        {
            "single_hop": inc_config.detectability_distribution.single_hop,
            "multi_hop": inc_config.detectability_distribution.multi_hop,
            "entity_resolution_dependent": inc_config.detectability_distribution.entity_resolution,
        },
        rng,
    )

    # Step 6: Assign mechanisms
    mechanisms = _assign_mechanisms(inc_config.mechanism, count, rng)

    # Step 7: Build injection plan
    plan = _build_injection_plan(
        scope_alloc, detect_alloc, mechanisms, affinity, rng
    )

    # Step 8: Execute injections
    labels: list[IncoherenceLabel] = []
    success_count = 0
    fail_count = 0

    # Index shared entities for scope selection
    shared_nodes = [n for n in entity_graph.nodes if len(n.subcorpus_memberships) > 1]
    subcorpus_ids = sorted(docs_by_subcorpus.keys())

    for idx, injection in enumerate(plan):
        logger.debug(f"Injection {idx + 1}/{count}: {injection}")

        label, error = _execute_injection(
            idx=idx,
            injection=injection,
            docs_by_subcorpus=docs_by_subcorpus,
            entity_graph=entity_graph,
            shared_nodes=shared_nodes,
            subcorpus_ids=subcorpus_ids,
            rng=rng,
            llm=llm,
            affinity=affinity,
        )

        if error:
            logger.warning(f"Injection {idx + 1}/{count} failed: {error}")
            fail_count += 1
            continue

        labels.append(label)
        success_count += 1

    # Step 9: Write modified corpus back to disk
    _write_corpus(corpus_dir, docs_by_subcorpus)

    # Step 10: Log summary
    scope_counts = {}
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


def _load_corpus(corpus_dir: Path) -> tuple[dict[str, list[Document]], list[Document]]:
    """Load all subcorpus JSONL files. Returns (docs_by_subcorpus, all_docs)."""
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


def _compute_count(count_config, total_docs: int) -> int:
    """Compute injection count from config value."""
    if isinstance(count_config, int):
        return count_config
    # "auto" heuristic
    return max(10, total_docs // 10)


def _distribute(
    total: int,
    weights: dict[str, float],
    rng: random.Random,
) -> dict[str, int]:
    """Distribute total across categories proportionally to weights."""
    result: dict[str, int] = {}
    keys = list(weights.keys())
    weight_sum = sum(weights.values())

    if weight_sum == 0:
        # Uniform fallback
        per_key = total // len(keys)
        for k in keys:
            result[k] = per_key
        result[keys[-1]] += total - sum(result.values())
        return result

    allocated = 0
    for i, k in enumerate(keys):
        if i == len(keys) - 1:
            # Last bucket gets remainder
            result[k] = total - allocated
        else:
            n = round(total * weights[k] / weight_sum)
            result[k] = n
            allocated += n

    return result


def _assign_mechanisms(mechanism_config: str, count: int, rng: random.Random) -> list[str]:
    """Assign mechanism to each injection."""
    if mechanism_config == "uniform":
        # Distribute uniformly across all 6 mechanisms
        mechanisms = []
        for i in range(count):
            mechanisms.append(_ALL_MECHANISMS[i % len(_ALL_MECHANISMS)])
        rng.shuffle(mechanisms)
        return mechanisms

    # Specific mechanism for all injections
    if mechanism_config in _ALL_MECHANISMS:
        return [mechanism_config] * count

    # Unknown mechanism — default to uniform with warning
    logger.warning(f"Unknown mechanism '{mechanism_config}', falling back to uniform")
    return _assign_mechanisms("uniform", count, rng)


def _build_injection_plan(
    scope_alloc: dict[str, int],
    detect_alloc: dict[str, int],
    mechanisms: list[str],
    affinity: str,
    rng: random.Random,
) -> list[dict]:
    """Build a plan of injections with assigned scope, detectability, mechanism, and affinity."""
    # Expand scope allocation into a list
    scopes: list[str] = []
    for scope, n in scope_alloc.items():
        scopes.extend([scope] * n)

    # Expand detectability allocation into a list
    detectabilities: list[str] = []
    for detect, n in detect_alloc.items():
        detectabilities.extend([detect] * n)

    # Shuffle to randomize pairing
    rng.shuffle(scopes)
    rng.shuffle(detectabilities)

    count = len(mechanisms)
    plan = []
    for i in range(count):
        plan.append({
            "scope": scopes[i] if i < len(scopes) else scopes[-1],
            "mechanism": mechanisms[i],
            "detectability": detectabilities[i] if i < len(detectabilities) else detectabilities[-1],
            "affinity": affinity,
        })

    return plan


def _execute_injection(
    idx: int,
    injection: dict,
    docs_by_subcorpus: dict[str, list[Document]],
    entity_graph: EntityGraph,
    shared_nodes: list[EntityNode],
    subcorpus_ids: list[str],
    rng: random.Random,
    llm,
    affinity: str,
) -> tuple[IncoherenceLabel | None, str | None]:
    """Execute a single injection. Returns (label, None) or (None, error)."""
    scope = injection["scope"]
    mechanism = injection["mechanism"]
    detectability = injection["detectability"]

    # Select target documents based on scope
    target_docs, error = _select_targets(
        scope=scope,
        affinity=affinity,
        docs_by_subcorpus=docs_by_subcorpus,
        entity_graph=entity_graph,
        shared_nodes=shared_nodes,
        subcorpus_ids=subcorpus_ids,
        rng=rng,
    )
    if error:
        return None, f"Target selection failed: {error}"

    primary_doc = target_docs[0]

    # Extract facts from primary document
    facts, error = _extract_facts(primary_doc, mechanism, llm)
    if error:
        return None, f"Fact extraction failed: {error}"

    if not facts:
        return None, "No suitable facts found in document"

    # Select a fact to modify
    selected_fact = rng.choice(facts)

    # Apply minimal-pair modification
    result, error = _apply_modification(
        doc=primary_doc,
        fact=selected_fact,
        mechanism=mechanism,
        detectability=detectability,
        entity_graph=entity_graph,
        rng=rng,
        llm=llm,
    )
    if error:
        return None, f"Modification failed: {error}"

    modified_passage, original_fact, modified_fact = result

    # Apply the modification to the document content
    if original_fact in primary_doc.content:
        primary_doc.content = primary_doc.content.replace(
            original_fact, modified_fact, 1
        )
    else:
        # Fallback: use the full passage replacement
        logger.warning(
            f"Injection {idx}: exact fact not found in content, "
            f"applying passage-level replacement"
        )
        # Find approximate location and do best-effort replacement
        primary_doc.content = modified_passage

    # Build label
    doc_refs = [d.id for d in target_docs]
    label = IncoherenceLabel(
        id=f"incoherence_{idx:04d}",
        scope=scope,
        mechanism=mechanism,
        detectability=detectability,
        system_affinity=affinity,
        document_references=doc_refs,
        modified_fact=modified_fact,
        original_fact=original_fact,
    )

    return label, None


def _select_targets(
    scope: str,
    affinity: str,
    docs_by_subcorpus: dict[str, list[Document]],
    entity_graph: EntityGraph,
    shared_nodes: list[EntityNode],
    subcorpus_ids: list[str],
    rng: random.Random,
) -> tuple[list[Document] | None, str | None]:
    """Select target documents based on scope and affinity."""
    if scope == "intra_doc":
        # Pick a single document
        all_docs = [d for docs in docs_by_subcorpus.values() for d in docs]
        if not all_docs:
            return None, "No documents available"
        doc = rng.choice(all_docs)
        return [doc], None

    elif scope == "intra_corpus":
        # Pick two documents from the same subcorpus
        # Prefer subcorpora with entity overlap if graph_favoring
        if affinity == "graph_favoring" and shared_nodes:
            # Pick a subcorpus with shared entities
            sc_with_shared = set()
            for node in shared_nodes:
                for sc in node.subcorpus_memberships:
                    if sc in docs_by_subcorpus:
                        sc_with_shared.add(sc)
            if sc_with_shared:
                sc_id = rng.choice(sorted(sc_with_shared))
            else:
                sc_id = rng.choice(subcorpus_ids)
        else:
            sc_id = rng.choice(subcorpus_ids)

        docs = docs_by_subcorpus.get(sc_id, [])
        if len(docs) < 2:
            return None, f"Subcorpus {sc_id} has fewer than 2 documents"
        pair = rng.sample(docs, 2)
        return pair, None

    elif scope == "inter_corpus":
        # Pick two documents from different subcorpora
        if len(subcorpus_ids) < 2:
            return None, "Need at least 2 subcorpora for inter_corpus scope"

        # Pick two different subcorpora
        if affinity == "graph_favoring" and shared_nodes:
            # Pick subcorpora connected by shared entities
            node = rng.choice(shared_nodes)
            available = [s for s in node.subcorpus_memberships if s in docs_by_subcorpus]
            if len(available) >= 2:
                sc_pair = rng.sample(available, 2)
            else:
                sc_pair = rng.sample(subcorpus_ids, 2)
        else:
            sc_pair = rng.sample(subcorpus_ids, 2)

        doc_a = rng.choice(docs_by_subcorpus[sc_pair[0]])
        doc_b = rng.choice(docs_by_subcorpus[sc_pair[1]])
        return [doc_a, doc_b], None

    return None, f"Unknown scope: {scope}"


def _extract_facts(
    doc: Document,
    mechanism: str,
    llm,
) -> tuple[list[dict] | None, str | None]:
    """Extract modifiable facts from a document using LLM."""
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

    response, error = llm(prompt, model="gpt-4o-mini", temperature=0)
    if error:
        return None, error

    try:
        data = json.loads(response)
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
        return facts  # No filtering for unknown mechanisms

    return [f for f in facts if f.get("type") in target_types]


def _apply_modification(
    doc: Document,
    fact: dict,
    mechanism: str,
    detectability: str,
    entity_graph: EntityGraph,
    rng: random.Random,
    llm,
) -> tuple[tuple[str, str, str] | None, str | None]:
    """Apply minimal-pair modification to a fact. Returns ((modified_passage, original, modified), None)."""
    fact_text = fact.get("fact", "")
    mechanism_instruction = _mechanism_instruction(mechanism, fact_text, entity_graph, rng)
    detectability_instruction = _detectability_instruction(detectability)

    prompt = (
        "You are modifying a single fact in a document to create a controlled "
        "factual incoherence. You MUST change ONLY the target fact — preserve "
        "all surrounding text, style, and formatting exactly.\n\n"
        f"Document passage:\n{doc.content[:2000]}\n\n"
        f"Target fact to modify: \"{fact_text}\"\n\n"
        f"Modification type: {mechanism_instruction}\n\n"
        f"Detectability guidance: {detectability_instruction}\n\n"
        "Return a JSON object with exactly these fields:\n"
        '- "modified_passage": the full passage with ONLY the target fact changed\n'
        '- "original_fact": the original factual statement\n'
        '- "modified_fact": the new contradictory statement\n\n'
        "Return ONLY valid JSON. Change NOTHING except the target fact."
    )

    response, error = llm(prompt, model="gpt-4o-mini", temperature=0)
    if error:
        return None, error

    try:
        data = json.loads(response)
        modified_passage = data["modified_passage"]
        original_fact = data["original_fact"]
        modified_fact = data["modified_fact"]
        return (modified_passage, original_fact, modified_fact), None
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None, f"Failed to parse modification response: {e}"


def _mechanism_instruction(
    mechanism: str,
    fact_text: str,
    entity_graph: EntityGraph,
    rng: random.Random,
) -> str:
    """Generate mechanism-specific instruction for the LLM."""
    if mechanism == "numeric_drift":
        return (
            f"Change a numeric value in this fact to a different but plausible number. "
            f"The new number should be different enough to be wrong but plausible "
            f"in the domain (e.g., change altitude, speed, date, or count)."
        )
    elif mechanism == "entity_swap":
        # Try to find an alternative entity from the graph
        alt_entities = [
            n.canonical_name for n in entity_graph.nodes
            if n.canonical_name.lower() not in fact_text.lower()
        ]
        if alt_entities:
            alt = rng.choice(alt_entities)
            return (
                f"Replace an entity reference in this fact with '{alt}'. "
                f"The replacement should be a different entity of similar type."
            )
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
