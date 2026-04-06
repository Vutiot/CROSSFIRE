"""Extract named entities from NTSB documents using domain-specific patterns."""

import re
from collections import defaultdict

from loguru import logger

from .models import EntityMention, EntityProfile, ExtractedDocument

# --- Organization patterns ---
_KNOWN_ORGS = [
    ("Boeing", ["The Boeing Company", "Boeing Commercial Airplanes", "BCA", "Boeing Co"]),
    ("Spirit AeroSystems", ["Spirit Aerosystems", "Spirit"]),
    ("FAA", ["Federal Aviation Administration", "the FAA"]),
    ("NTSB", ["National Transportation Safety Board", "the NTSB", "Safety Board"]),
    ("Alaska Airlines", ["Alaska Air", "Alaska Airlines Inc"]),
    ("Ethiopian Airlines", ["Ethiopian Airlines Group"]),
    ("Lion Air", ["Lion Mentari Airlines", "PT Lion Mentari"]),
    ("Atlas Air", ["Atlas Air Inc", "Atlas Air Worldwide"]),
    ("Southwest Airlines", ["Southwest Airlines Co"]),
    ("CFM International", ["CFMI", "CFM"]),
    ("GE Aviation", ["General Electric Aviation", "GE Aerospace"]),
    ("Textron Aviation", ["Textron", "Cessna", "Beechcraft"]),
    ("Sikorsky", ["Sikorsky Aircraft", "Sikorsky, a Lockheed Martin Company"]),
    ("Island Express Helicopters", ["Island Express"]),
    ("Airbus", ["Airbus SAS", "Airbus SE"]),
    ("Pratt & Whitney", ["P&W", "Pratt and Whitney"]),
    ("Honeywell", ["Honeywell Aerospace"]),
    ("Rolls-Royce", ["Rolls Royce"]),
]

# --- Equipment patterns ---
_EQUIPMENT_PATTERNS = [
    re.compile(r"\bBoeing\s+7[0-9]{2}(?:-\d{1,4})?(?:\s*MAX\s*\d+)?\b", re.I),
    re.compile(r"\b737\s*MAX\s*\d?\b", re.I),
    re.compile(r"\bMCAS\b"),
    re.compile(r"\bCFM56-\w+\b", re.I),
    re.compile(r"\bLEAP-\w+\b", re.I),
    re.compile(r"\bS-76[A-Z]?\b", re.I),
    re.compile(r"\bDHC-[0-9]+[A-Z]?\b", re.I),
    re.compile(r"\bKing Air\s*[A-Z0-9]*\b", re.I),
    re.compile(r"\bMED\s+plug\b", re.I),
    re.compile(r"\bdoor\s+plug\b", re.I),
]

# --- Regulation patterns ---
_REGULATION_RE = re.compile(r"\b14\s+CFR\s+(?:Part\s+)?\d+(?:\.\d+)?\b", re.I)
_AD_RE = re.compile(r"\bAD\s+\d{4}-\d{2}-\d{2}\b", re.I)
_AC_RE = re.compile(r"\bAC\s+\d{2,3}-\d+[A-Z]?\b", re.I)


def extract_entities_from_text(
    text: str, ntsb_id: str, document_title: str
) -> list[EntityMention]:
    """Extract named entities from a single document's text."""
    if not text:
        return []

    mentions = []

    # Organizations
    for canonical, aliases in _KNOWN_ORGS:
        all_forms = [canonical] + aliases
        for form in all_forms:
            if form.lower() in text.lower():
                mentions.append(
                    EntityMention(
                        name=canonical,
                        entity_type="organization",
                        ntsb_id=ntsb_id,
                        document_title=document_title,
                    )
                )
                break  # one mention per org per document

    # Equipment
    for pattern in _EQUIPMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            mentions.append(
                EntityMention(
                    name=match.group(0).strip(),
                    entity_type="equipment",
                    ntsb_id=ntsb_id,
                    document_title=document_title,
                )
            )

    # Regulations
    for reg_match in _REGULATION_RE.finditer(text):
        mentions.append(
            EntityMention(
                name=reg_match.group(0).strip(),
                entity_type="regulation",
                ntsb_id=ntsb_id,
                document_title=document_title,
            )
        )
        if len([m for m in mentions if m.entity_type == "regulation"]) >= 10:
            break  # cap regulation mentions per doc

    for ad_match in _AD_RE.finditer(text):
        mentions.append(
            EntityMention(
                name=ad_match.group(0).strip(),
                entity_type="regulation",
                ntsb_id=ntsb_id,
                document_title=document_title,
            )
        )

    return mentions


def extract_entities_from_documents(
    documents: list[ExtractedDocument],
) -> list[EntityMention]:
    """Extract entities from all documents."""
    all_mentions = []
    for doc in documents:
        if doc.quality and doc.quality.passed and doc.text:
            mentions = extract_entities_from_text(doc.text, doc.ntsb_id, doc.title)
            all_mentions.extend(mentions)
    logger.info(f"Extracted {len(all_mentions)} entity mentions from {len(documents)} documents")
    return all_mentions


def build_entity_profiles(mentions: list[EntityMention]) -> list[EntityProfile]:
    """Aggregate entity mentions into unique entity profiles."""
    # Group by (canonical_name, entity_type)
    groups: dict[tuple[str, str], dict] = {}

    for m in mentions:
        key = (_normalize_entity_name(m.name), m.entity_type)
        if key not in groups:
            groups[key] = {
                "canonical": key[0],
                "type": m.entity_type,
                "aliases": set(),
                "dockets": set(),
                "count": 0,
            }
        groups[key]["aliases"].add(m.name)
        groups[key]["dockets"].add(m.ntsb_id)
        groups[key]["count"] += 1

    profiles = []
    for data in groups.values():
        profiles.append(
            EntityProfile(
                canonical_name=data["canonical"],
                entity_type=data["type"],
                aliases=sorted(data["aliases"]),
                docket_ids=sorted(data["dockets"]),
                mention_count=data["count"],
            )
        )

    profiles.sort(key=lambda p: (-len(p.docket_ids), -p.mention_count))
    return profiles


def _normalize_entity_name(name: str) -> str:
    """Normalize entity name for deduplication."""
    # Lowercase, strip articles, collapse whitespace
    n = name.strip().lower()
    for prefix in ["the ", "a "]:
        if n.startswith(prefix):
            n = n[len(prefix):]
    return " ".join(n.split())
