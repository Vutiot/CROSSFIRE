"""Layer 1 representation quality evaluation — system graph vs gold graph (FR27)."""

from loguru import logger

from crossfire.shared.schemas.entities import EntityGraph
from crossfire.shared.schemas.evaluation import (
    EvaluationResult,
    RepresentationQualityResult,
)


def _normalize(name: str) -> str:
    """Normalize entity name for comparison."""
    return name.strip().lower()


def _build_gold_index(
    gold_graph: EntityGraph,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    """Build lookup structures from gold graph.

    Returns:
        name_to_gold_id: normalized name/alias -> gold entity id
        gold_aliases: gold entity id -> set of normalized aliases
    """
    name_to_gold_id: dict[str, str] = {}
    gold_aliases: dict[str, set[str]] = {}

    for node in sorted(gold_graph.nodes, key=lambda n: n.id):
        canon = _normalize(node.canonical_name)
        name_to_gold_id[canon] = node.id
        aliases_norm: set[str] = set()
        for alias in node.aliases:
            norm = _normalize(alias)
            name_to_gold_id[norm] = node.id
            aliases_norm.add(norm)
        gold_aliases[node.id] = aliases_norm

    return name_to_gold_id, gold_aliases


def _compute_entity_coverage(
    system_graph: EntityGraph,
    gold_graph: EntityGraph,
    name_to_gold_id: dict[str, str],
) -> float:
    """Fraction of gold entities matched by at least one system entity."""
    if not gold_graph.nodes:
        return 0.0

    covered_gold_ids: set[str] = set()
    for sys_node in system_graph.nodes:
        canon = _normalize(sys_node.canonical_name)
        gold_id = name_to_gold_id.get(canon)
        if gold_id:
            covered_gold_ids.add(gold_id)
        for alias in sys_node.aliases:
            gold_id = name_to_gold_id.get(_normalize(alias))
            if gold_id:
                covered_gold_ids.add(gold_id)

    return len(covered_gold_ids) / len(gold_graph.nodes)


def _build_system_name_to_id(system_graph: EntityGraph) -> dict[str, str]:
    """Map normalized system entity names to system entity IDs."""
    mapping: dict[str, str] = {}
    for node in sorted(system_graph.nodes, key=lambda n: n.id):
        canon = _normalize(node.canonical_name)
        if canon not in mapping:
            mapping[canon] = node.id
        for alias in node.aliases:
            norm = _normalize(alias)
            if norm not in mapping:
                mapping[norm] = node.id
    return mapping


def _compute_relationship_accuracy(
    system_graph: EntityGraph,
    gold_graph: EntityGraph,
    name_to_gold_id: dict[str, str],
) -> float:
    """Fraction of system edges that match a gold edge."""
    if not system_graph.edges:
        return 1.0 if not gold_graph.edges else 0.0

    # Build gold edge set: (gold_id_a, gold_id_b, rel_type) — undirected
    gold_edge_set: set[tuple[str, str, str]] = set()
    for edge in gold_graph.edges:
        a, b = sorted([edge.source, edge.target])
        gold_edge_set.add((a, b, edge.relationship_type))

    # Map system entity IDs to gold entity IDs via name
    sys_id_to_gold_id: dict[str, str | None] = {}
    for node in system_graph.nodes:
        canon = _normalize(node.canonical_name)
        sys_id_to_gold_id[node.id] = name_to_gold_id.get(canon)

    matched = 0
    for edge in system_graph.edges:
        gold_src = sys_id_to_gold_id.get(edge.source)
        gold_tgt = sys_id_to_gold_id.get(edge.target)
        if gold_src and gold_tgt:
            a, b = sorted([gold_src, gold_tgt])
            if (a, b, edge.relationship_type) in gold_edge_set:
                matched += 1

    return matched / len(system_graph.edges)


def _compute_entity_resolution_quality(
    system_graph: EntityGraph,
    gold_graph: EntityGraph,
    name_to_gold_id: dict[str, str],
    gold_aliases: dict[str, set[str]],
) -> float:
    """Fraction of gold aliases correctly resolved to the same system entity."""
    # Collect all gold aliases across all gold entities
    total_aliases = sum(len(aliases) for aliases in gold_aliases.values())
    if total_aliases == 0:
        return 1.0

    # Build system name -> system entity id mapping
    sys_name_to_id = _build_system_name_to_id(system_graph)

    correctly_resolved = 0
    for gold_node in sorted(gold_graph.nodes, key=lambda n: n.id):
        aliases = gold_aliases.get(gold_node.id, set())
        if not aliases:
            continue

        # Find system entity for the canonical name
        canon = _normalize(gold_node.canonical_name)
        canonical_sys_id = sys_name_to_id.get(canon)

        for alias_norm in sorted(aliases):
            alias_sys_id = sys_name_to_id.get(alias_norm)
            if (
                canonical_sys_id is not None
                and alias_sys_id is not None
                and canonical_sys_id == alias_sys_id
            ):
                correctly_resolved += 1

    return correctly_resolved / total_aliases


def score_representation(
    system_graph: EntityGraph,
    gold_graph: EntityGraph,
) -> EvaluationResult:
    """Evaluate pipeline's internal knowledge graph against gold entity graph.

    Computes three metrics:
    - Entity coverage: fraction of gold entities found in system graph
    - Relationship accuracy: fraction of system edges matching gold edges
    - Entity resolution quality: fraction of gold aliases correctly resolved

    Returns EvaluationResult with representation_quality populated.
    """
    logger.info(
        f"Representation eval: system={len(system_graph.nodes)} nodes "
        f"{len(system_graph.edges)} edges, "
        f"gold={len(gold_graph.nodes)} nodes {len(gold_graph.edges)} edges"
    )

    # Handle both-empty case
    if not system_graph.nodes and not gold_graph.nodes:
        rq = RepresentationQualityResult(
            entity_coverage=0.0,
            relationship_accuracy=0.0,
            entity_resolution_quality=0.0,
        )
        logger.info(
            f"Representation result: coverage={rq.entity_coverage:.4f} "
            f"accuracy={rq.relationship_accuracy:.4f} "
            f"resolution={rq.entity_resolution_quality:.4f}"
        )
        return EvaluationResult(
            overall_precision=0.0,
            overall_recall=0.0,
            overall_f1=0.0,
            representation_quality=rq,
        )

    name_to_gold_id, gold_aliases = _build_gold_index(gold_graph)

    coverage = _compute_entity_coverage(system_graph, gold_graph, name_to_gold_id)
    accuracy = _compute_relationship_accuracy(
        system_graph, gold_graph, name_to_gold_id
    )
    resolution = _compute_entity_resolution_quality(
        system_graph, gold_graph, name_to_gold_id, gold_aliases
    )

    rq = RepresentationQualityResult(
        entity_coverage=coverage,
        relationship_accuracy=accuracy,
        entity_resolution_quality=resolution,
    )
    logger.info(
        f"Representation result: coverage={rq.entity_coverage:.4f} "
        f"accuracy={rq.relationship_accuracy:.4f} "
        f"resolution={rq.entity_resolution_quality:.4f}"
    )
    return EvaluationResult(
        overall_precision=0.0,
        overall_recall=0.0,
        overall_f1=0.0,
        representation_quality=rq,
    )
