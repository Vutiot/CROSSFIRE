"""Entity graph builder — generates a gold entity graph with configurable connectivity.

Connectivity levels control entity sharing across subcorpora:
  Level 0: Fully isolated subcorpora (no shared entities)
  Level 1: ~30% shared, identical naming (easy entity resolution)
  Level 2: ~35% shared, alias variation per subcorpus (requires entity resolution)
  Level 3: ~60% shared, dense + aggressive alias variation (hard resolution)

Entity pools are grounded in real NTSB data from Story 2.1 analysis.
"""

import random

from loguru import logger

from crossfire.shared.schemas.config import GeneratorConfig
from crossfire.shared.schemas.entities import EntityEdge, EntityGraph, EntityNode
from crossfire.shared.seed_manager import SeedManager

# ---------------------------------------------------------------------------
# Entity pools — sourced from scraper/entity_extractor.py _KNOWN_ORGS
# and data/ntsb_analysis/analysis_report.json
# ---------------------------------------------------------------------------

ORGANIZATION_POOL: list[tuple[str, list[str]]] = [
    ("Boeing", ["The Boeing Company", "Boeing Commercial Airplanes", "BCA", "Boeing Co"]),
    ("FAA", ["Federal Aviation Administration", "the FAA"]),
    ("NTSB", ["National Transportation Safety Board", "the NTSB", "Safety Board"]),
    ("Spirit AeroSystems", ["Spirit Aerosystems", "Spirit"]),
    ("Alaska Airlines", ["Alaska Air", "Alaska Airlines Inc"]),
    ("Ethiopian Airlines", ["Ethiopian Airlines Group"]),
    ("Lion Air", ["Lion Mentari Airlines", "PT Lion Mentari"]),
    ("Atlas Air", ["Atlas Air Inc", "Atlas Air Worldwide"]),
    ("Southwest Airlines", ["Southwest Airlines Co"]),
    ("CFM International", ["CFMI", "CFM"]),
    ("GE Aviation", ["General Electric Aviation", "GE Aerospace"]),
    ("Textron Aviation", ["Textron", "Cessna", "Beechcraft"]),
    ("Sikorsky", ["Sikorsky Aircraft"]),
    ("Airbus", ["Airbus SAS", "Airbus SE"]),
    ("Pratt & Whitney", ["P&W", "Pratt and Whitney"]),
    ("Honeywell", ["Honeywell Aerospace"]),
    ("Rolls-Royce", ["Rolls Royce"]),
    ("Island Express Helicopters", ["Island Express"]),
]

EQUIPMENT_POOL: list[tuple[str, list[str]]] = [
    ("Boeing 737 MAX 9", ["737 MAX 9", "737-9", "BOEING 737-9"]),
    ("Boeing 737 MAX 8", ["737 MAX 8", "737-8", "BOEING 737-8"]),
    ("Boeing 767-300", ["767-300", "BOEING 767-300", "Boeing 767"]),
    ("MED plug", ["mid-exit door plug", "door plug", "MED Plug", "DOOR PLUG"]),
    ("MCAS", ["Maneuvering Characteristics Augmentation System"]),
    ("CFM56-7B", ["CFM56 engine", "CFM56"]),
    ("LEAP-1B", ["LEAP-1B engine", "LEAP engine"]),
    ("DHC-8", ["Dash 8", "de Havilland Dash 8"]),
    ("Sikorsky S-76B", ["S-76B", "S-76"]),
    ("King Air 350", ["King Air", "Beechcraft King Air", "King Air series"]),
    ("Flight Data Recorder", ["FDR", "flight recorder"]),
    ("Cockpit Voice Recorder", ["CVR", "voice recorder"]),
]

REGULATION_POOL: list[tuple[str, list[str]]] = [
    ("14 CFR Part 121", ["Part 121", "14 CFR part 121"]),
    ("14 CFR Part 135", ["Part 135", "14 CFR part 135"]),
    ("14 CFR Part 91", ["Part 91", "14 CFR part 91"]),
    ("14 CFR Part 25", ["Part 25", "14 CFR part 25"]),
    ("14 CFR Part 21", ["Part 21", "14 CFR Part 21"]),
    ("14 CFR 25.783", ["Section 25.783"]),
    ("14 CFR 25.571", ["Section 25.571", "damage tolerance requirements"]),
    ("14 CFR 121.344", ["Section 121.344"]),
    ("14 CFR Part 5", ["Part 5", "SMS regulation", "14 CFR part 5"]),
    ("14 CFR Part 193", ["Part 193", "14 CFR part 193"]),
    ("AD 2024-02-51", ["Airworthiness Directive 2024-02-51"]),
    ("AD 2012-09-04", ["Airworthiness Directive 2012-09-04"]),
    ("AC 120-16G", ["Advisory Circular 120-16G"]),
    ("Order 8900.1", ["FAA Order 8900.1", "Flight Standards Order"]),
    ("SFAR 88", ["Special Federal Aviation Regulation 88"]),
]

LOCATION_POOL: list[tuple[str, list[str]]] = [
    ("Portland, Oregon", ["Portland International Airport", "PDX", "Portland OR"]),
    ("Renton, Washington", ["Boeing Renton facility", "Renton plant"]),
    ("Wichita, Kansas", ["Spirit AeroSystems Wichita", "Wichita KS"]),
    ("Washington, D.C.", ["NTSB headquarters", "Washington DC"]),
    ("Oklahoma City, Oklahoma", ["FAA Mike Monroney Center", "OKC"]),
]

PERSON_POOL: list[tuple[str, list[str]]] = [
    ("Captain", ["the Captain", "PIC", "pilot in command"]),
    ("First Officer", ["the First Officer", "FO", "SIC", "second in command"]),
    ("Lead Investigator", ["IIC", "Investigator-in-Charge"]),
    ("Chief Inspector", ["the Chief Inspector", "Principal Inspector"]),
]

_ALL_POOLS: dict[str, list[tuple[str, list[str]]]] = {
    "organization": ORGANIZATION_POOL,
    "equipment": EQUIPMENT_POOL,
    "regulation": REGULATION_POOL,
    "location": LOCATION_POOL,
    "person": PERSON_POOL,
}

# Per-subcorpus entity count targets per type
_ENTITY_COUNTS: dict[str, tuple[int, int]] = {
    "organization": (4, 6),
    "equipment": (3, 5),
    "regulation": (5, 8),
    "location": (1, 3),
    "person": (1, 2),
}

# Sharing fractions per connectivity level
_SHARED_FRACTIONS: dict[int, float] = {0: 0.0, 1: 0.3, 2: 0.35, 3: 0.6}

# Relationship types between entity type pairs
_RELATIONSHIP_TYPES: dict[tuple[str, str], list[str]] = {
    ("organization", "equipment"): ["manufactures", "operates"],
    ("organization", "regulation"): ["regulated_by", "issued_by"],
    ("organization", "location"): ["headquartered_in", "operates_from"],
    ("organization", "person"): ["employs"],
    ("equipment", "regulation"): ["certified_under"],
}


def build_entity_graph(
    config: GeneratorConfig,
    seed_mgr: SeedManager,
) -> EntityGraph:
    """Build a gold entity graph with configurable connectivity.

    Returns an EntityGraph with entities distributed across subcorpora
    according to the connectivity_level in config.
    """
    level = config.connectivity_level
    n_sub = config.subcorpora_count
    subcorpus_ids = [f"sc-{i}" for i in range(n_sub)]

    rng = random.Random(seed_mgr.get_seed("entity_graph", 0))
    shared_fraction = _SHARED_FRACTIONS[level]

    logger.info(
        f"Building entity graph: {n_sub} subcorpora, "
        f"connectivity_level={level}, shared_fraction={shared_fraction:.0%}"
    )

    # Step 1: Select entities from pools
    all_entities = _select_entity_pool(rng, n_sub)

    # Step 2: Partition into shared vs local
    shared, local = _partition_entities(rng, all_entities, shared_fraction)

    # Step 3: Assign subcorpus memberships
    nodes = []
    nodes.extend(_assign_shared_memberships(rng, shared, subcorpus_ids, level))
    nodes.extend(_assign_local_memberships(rng, local, subcorpus_ids))

    # Step 4: Assign aliases per connectivity level
    _assign_aliases(rng, nodes, level)

    # Step 5: Build edges
    edges = _build_edges(rng, nodes)

    graph = EntityGraph(nodes=nodes, edges=edges)

    n_shared = sum(1 for n in nodes if len(n.subcorpus_memberships) > 1)
    logger.info(
        f"Entity graph built: {len(nodes)} nodes ({n_shared} shared), "
        f"{len(edges)} edges"
    )
    return graph


def _select_entity_pool(
    rng: random.Random,
    n_subcorpora: int,
) -> list[tuple[str, str, list[str]]]:
    """Select entities from pools. Returns list of (canonical, type, all_known_aliases)."""
    entities: list[tuple[str, str, list[str]]] = []

    for entity_type, pool in _ALL_POOLS.items():
        lo, hi = _ENTITY_COUNTS[entity_type]
        # Scale count with subcorpora — more subcorpora need more entities
        target = min(rng.randint(lo, hi) * max(1, n_subcorpora // 2), len(pool))
        selected = rng.sample(pool, target)
        for canonical, aliases in selected:
            entities.append((canonical, entity_type, list(aliases)))

    return entities


def _partition_entities(
    rng: random.Random,
    entities: list[tuple[str, str, list[str]]],
    shared_fraction: float,
) -> tuple[list[tuple[str, str, list[str]]], list[tuple[str, str, list[str]]]]:
    """Split entities into shared and local pools."""
    if shared_fraction == 0.0:
        return [], list(entities)

    shuffled = list(entities)
    rng.shuffle(shuffled)
    split_idx = max(1, int(len(shuffled) * shared_fraction))
    return shuffled[:split_idx], shuffled[split_idx:]


def _assign_shared_memberships(
    rng: random.Random,
    shared: list[tuple[str, str, list[str]]],
    subcorpus_ids: list[str],
    level: int,
) -> list[EntityNode]:
    """Create EntityNodes for shared entities with multi-subcorpus membership."""
    nodes = []
    for i, (canonical, entity_type, known_aliases) in enumerate(shared):
        # Shared entities appear in 2 to N subcorpora
        min_memberships = 2
        max_memberships = len(subcorpus_ids) if level == 3 else max(2, len(subcorpus_ids) // 2 + 1)
        n_memberships = rng.randint(min_memberships, max_memberships)
        memberships = sorted(rng.sample(subcorpus_ids, min(n_memberships, len(subcorpus_ids))))

        nodes.append(EntityNode(
            id=f"{entity_type}_{i:03d}",
            entity_type=entity_type,
            canonical_name=canonical,
            aliases=known_aliases,
            subcorpus_memberships=memberships,
        ))
    return nodes


def _assign_local_memberships(
    rng: random.Random,
    local: list[tuple[str, str, list[str]]],
    subcorpus_ids: list[str],
) -> list[EntityNode]:
    """Create EntityNodes for local entities with single subcorpus membership."""
    nodes = []
    for i, (canonical, entity_type, known_aliases) in enumerate(local):
        # Round-robin across subcorpora
        sc = subcorpus_ids[i % len(subcorpus_ids)]
        # Offset ID to avoid collision with shared entities
        nodes.append(EntityNode(
            id=f"{entity_type}_local_{i:03d}",
            entity_type=entity_type,
            canonical_name=canonical,
            aliases=known_aliases,
            subcorpus_memberships=[sc],
        ))
    return nodes


def _assign_aliases(
    rng: random.Random,
    nodes: list[EntityNode],
    level: int,
) -> None:
    """Adjust aliases based on connectivity level (mutates nodes in place)."""
    for node in nodes:
        if level <= 1:
            # Levels 0-1: only canonical name (trivial resolution)
            node.aliases = [node.canonical_name]
        elif level == 2:
            # Level 2: subset of known aliases + canonical (moderate resolution)
            all_forms = [node.canonical_name] + node.aliases
            unique = list(dict.fromkeys(all_forms))  # dedupe preserving order
            if len(unique) > 2:
                keep = rng.randint(2, min(4, len(unique)))
                node.aliases = rng.sample(unique, keep)
            else:
                node.aliases = unique
        else:
            # Level 3: all known aliases + case-swapped variants (hard resolution)
            all_forms = [node.canonical_name] + node.aliases
            # Add case variants
            for form in list(all_forms):
                upper = form.upper()
                lower = form.lower()
                title = form.title()
                for v in (upper, lower, title):
                    if v not in all_forms:
                        all_forms.append(v)
            node.aliases = list(dict.fromkeys(all_forms))


def _build_edges(
    rng: random.Random,
    nodes: list[EntityNode],
) -> list[EntityEdge]:
    """Build typed edges between entities that share subcorpus membership."""
    edges: list[EntityEdge] = []
    seen: set[tuple[str, str]] = set()

    # Index nodes by type for efficient pairing
    by_type: dict[str, list[EntityNode]] = {}
    for node in nodes:
        by_type.setdefault(node.entity_type, []).append(node)

    for (type_a, type_b), rel_types in _RELATIONSHIP_TYPES.items():
        nodes_a = by_type.get(type_a, [])
        nodes_b = by_type.get(type_b, [])

        for a in nodes_a:
            for b in nodes_b:
                # Only edge if they share at least 1 subcorpus
                shared_sc = set(a.subcorpus_memberships) & set(b.subcorpus_memberships)
                if not shared_sc:
                    continue

                pair = (min(a.id, b.id), max(a.id, b.id))
                if pair in seen:
                    continue
                seen.add(pair)

                rel = rng.choice(rel_types)
                edges.append(EntityEdge(source=a.id, target=b.id, relationship_type=rel))

    return edges
