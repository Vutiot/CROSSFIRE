"""Analyze entity sharing patterns across NTSB dockets."""

from collections import defaultdict

from loguru import logger

from .models import CrossDocketPatterns, EntityProfile


def analyze_cross_docket_patterns(
    profiles: list[EntityProfile],
) -> CrossDocketPatterns:
    """Analyze entity sharing across dockets."""
    # Sharing matrix: entity → list of docket IDs
    sharing_matrix: dict[str, list[str]] = {}
    for p in profiles:
        sharing_matrix[p.canonical_name] = p.docket_ids

    # Shared entities: those appearing in 2+ dockets
    shared = {name: dockets for name, dockets in sharing_matrix.items() if len(dockets) >= 2}
    shared_count = len(shared)

    # Connectivity score: average number of dockets per shared entity
    connectivity = 0.0
    if shared:
        connectivity = sum(len(d) for d in shared.values()) / len(shared)

    # Naming variations
    naming_variations: dict[str, list[str]] = {}
    for p in profiles:
        if len(p.aliases) > 1:
            naming_variations[p.canonical_name] = p.aliases

    logger.info(
        f"Cross-docket analysis: {shared_count} shared entities, "
        f"connectivity score {connectivity:.2f}, "
        f"{len(naming_variations)} entities with naming variations"
    )

    # Log top shared entities
    for name, dockets in sorted(shared.items(), key=lambda x: -len(x[1]))[:10]:
        logger.info(f"  {name}: {len(dockets)} dockets — {', '.join(dockets)}")

    return CrossDocketPatterns(
        sharing_matrix=sharing_matrix,
        shared_entity_count=shared_count,
        connectivity_score=round(connectivity, 4),
        naming_variations=naming_variations,
    )
