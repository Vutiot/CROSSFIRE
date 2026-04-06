"""Corpus generator orchestrator — generates a complete corpus from a config.

Ties together Story 2.3 (entity graph) and Story 2.2 (document templates)
to produce JSONL per subcorpus + entity graph JSON + metadata JSON.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

from loguru import logger

from crossfire.shared.llm import get_usage_summary, llm_call, log_usage_summary
from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.corpus import Document, DocumentType
from crossfire.shared.seed_manager import SeedManager

from .entity_graph_builder import build_entity_graph
from .templates.document_factory import create_document

# All 8 document types from the Literal
_ALL_DOC_TYPES: list[str] = list(get_args(DocumentType))

# Pool of NTSB-style incident scenarios for subcorpus context
_INCIDENT_SCENARIOS = [
    (
        "On January 5, 2024, a Boeing 737 MAX 9 operated by a major U.S. airline "
        "experienced a rapid decompression event when the left mid-exit door plug "
        "separated from the fuselage during climb through 16,000 feet after departure "
        "from a Pacific Northwest airport. The aircraft returned safely with no fatalities."
    ),
    (
        "On March 10, 2019, a Boeing 737 MAX 8 operated by an East African carrier "
        "crashed shortly after takeoff, killing all 157 persons on board. The aircraft "
        "entered an uncommanded nose-down pitch attributed to the Maneuvering "
        "Characteristics Augmentation System (MCAS) receiving erroneous angle-of-attack data."
    ),
    (
        "On October 29, 2018, a Boeing 737 MAX 8 operated by a Southeast Asian carrier "
        "crashed into the Java Sea minutes after takeoff, killing all 189 persons on board. "
        "Investigators found repeated MCAS activation driven by a faulty angle-of-attack sensor."
    ),
    (
        "On April 17, 2018, a Boeing 737-700 suffered an uncontained engine failure "
        "during cruise flight at 32,500 feet. Debris from the left engine struck the "
        "fuselage and a cabin window, resulting in rapid decompression and one fatality."
    ),
    (
        "On February 23, 2019, a Boeing 767-300 cargo aircraft crashed into Trinity Bay, "
        "Texas, while on approach, killing all three crew members. The aircraft entered a "
        "rapid descent from 6,000 feet with no distress call from the flight crew."
    ),
    (
        "On January 26, 2020, a Sikorsky S-76B helicopter crashed into terrain in "
        "Calabasas, California, during instrument meteorological conditions, killing all "
        "nine persons on board. The pilot had continued VFR flight into an area of "
        "reduced visibility and rising terrain."
    ),
    (
        "On June 30, 2019, a Beechcraft King Air 350 crashed immediately after takeoff "
        "from a regional airport, striking a hangar and resulting in multiple fatalities. "
        "Witnesses reported the aircraft failed to gain altitude after rotation."
    ),
    (
        "On March 3, 2023, a regional turboprop aircraft experienced a loss of control "
        "during approach in icing conditions. The flight crew reported severe airframe "
        "icing and requested a diversion, but the aircraft impacted terrain short of "
        "the alternate runway."
    ),
    (
        "On November 12, 2022, a corporate jet overran the runway during landing in "
        "wet conditions at a coastal airport. The aircraft departed the runway surface "
        "and came to rest in soft terrain. Two occupants sustained serious injuries."
    ),
    (
        "On August 15, 2021, a Boeing 737-800 experienced a hard landing that collapsed "
        "the nose landing gear during a gusty crosswind approach. The aircraft sustained "
        "substantial damage but all passengers and crew evacuated safely."
    ),
]


def generate_corpus(
    config: GeneratorConfig,
    seed_mgr: SeedManager,
    llm=None,
) -> tuple[dict | None, str | None]:
    """Generate a complete corpus from configuration.

    Args:
        config: Generator configuration loaded from YAML preset.
        seed_mgr: SeedManager for reproducibility.
        llm: LLM call function (defaults to shared llm_call).

    Returns:
        (metadata_dict, None) on success, (None, error_message) on failure.
    """
    if llm is None:
        llm = llm_call

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    n_sub = config.subcorpora_count
    n_docs = config.docs_per_subcorpus
    total_docs = n_sub * n_docs

    logger.info(f"Generating corpus: {n_sub} subcorpora × {n_docs} docs = {total_docs} total")
    logger.info(f"Config: {config.name}, seed={config.master_seed}, connectivity={config.connectivity_level}")

    # Step 1: Build entity graph
    graph = build_entity_graph(config, seed_mgr)

    # Save entity graph
    graph_path = output_dir / "entity_graph.json"
    graph_path.write_text(graph.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"Entity graph saved: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    # Step 2: Select incident scenarios (1 per subcorpus)
    scenario_rng = random.Random(seed_mgr.get_seed("scenarios", 0))
    scenarios = scenario_rng.sample(
        _INCIDENT_SCENARIOS, min(n_sub, len(_INCIDENT_SCENARIOS))
    )
    # Pad if more subcorpora than scenarios
    while len(scenarios) < n_sub:
        scenarios.append(scenario_rng.choice(_INCIDENT_SCENARIOS))

    # Step 3: Generate documents per subcorpus
    doc_type_sequence = _build_doc_type_sequence(config.doc_type_mix, n_docs, seed_mgr)
    node_map = {n.id: n for n in graph.nodes}
    generated_count = 0
    errors = []

    for sub_idx in range(n_sub):
        sc_id = f"sc-{sub_idx}"

        # Filter entities for this subcorpus
        sc_entities = [n for n in graph.nodes if sc_id in n.subcorpus_memberships]

        context = {
            "subcorpus_id": sc_id,
            "incident_scenario": scenarios[sub_idx],
            "connectivity_level": config.connectivity_level,
        }

        jsonl_path = output_dir / f"subcorpus_{sc_id}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for doc_idx in range(n_docs):
                doc_type = doc_type_sequence[doc_idx % len(doc_type_sequence)]

                doc, error = create_document(
                    doc_type=doc_type,
                    entities=sc_entities,
                    context=context,
                    llm=llm,
                    seed_mgr=seed_mgr,
                    index=sub_idx * n_docs + doc_idx,
                )

                if error:
                    logger.warning(f"  {sc_id} doc {doc_idx}: {error}")
                    errors.append(f"{sc_id}/{doc_type}/{doc_idx}: {error}")
                    continue

                f.write(doc.model_dump_json() + "\n")
                generated_count += 1

        logger.info(f"Subcorpus {sub_idx + 1}/{n_sub} ({sc_id}) complete — {n_docs} documents")

    # Step 4: Write metadata
    usage = get_usage_summary()
    metadata = {
        "benchmark_version": "1.0",
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
        "master_seed": config.master_seed,
        "config": config.model_dump(mode="json"),
        "generation_summary": {
            "total_documents": generated_count,
            "total_errors": len(errors),
            "total_entities": len(graph.nodes),
            "total_edges": len(graph.edges),
            "total_tokens_used": usage["total_tokens"],
            "estimated_cost_usd": usage["estimated_cost_usd"],
        },
    }

    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Step 5: Log summary
    log_usage_summary()
    logger.info(
        f"Corpus generation complete: {generated_count}/{total_docs} documents, "
        f"{len(errors)} errors"
    )

    return metadata, None


def _build_doc_type_sequence(
    doc_type_mix: str,
    n_docs: int,
    seed_mgr: SeedManager,
) -> list[str]:
    """Build a sequence of document types based on the mix strategy."""
    if doc_type_mix == "balanced":
        # Round-robin across all 8 types
        sequence = []
        while len(sequence) < n_docs:
            sequence.extend(_ALL_DOC_TYPES)
        return sequence[:n_docs]

    # Default fallback: balanced
    logger.warning(f"Unknown doc_type_mix '{doc_type_mix}', falling back to balanced")
    return _build_doc_type_sequence("balanced", n_docs, seed_mgr)
