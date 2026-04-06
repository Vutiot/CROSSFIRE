"""Shared fixtures for template tests."""

import pytest

from crossfire.shared.schemas.entities import EntityNode
from crossfire.shared.seed_manager import SeedManager


@pytest.fixture
def seed_mgr():
    return SeedManager(master_seed=42)


@pytest.fixture
def sample_entities():
    return [
        EntityNode(
            id="org_001",
            entity_type="organization",
            canonical_name="Boeing",
            aliases=["The Boeing Company", "Boeing Commercial Airplanes", "BCA"],
            subcorpus_memberships=["sub_001"],
        ),
        EntityNode(
            id="org_002",
            entity_type="organization",
            canonical_name="FAA",
            aliases=["Federal Aviation Administration", "the FAA"],
            subcorpus_memberships=["sub_001"],
        ),
        EntityNode(
            id="org_003",
            entity_type="organization",
            canonical_name="Alaska Airlines",
            aliases=["Alaska Air"],
            subcorpus_memberships=["sub_001"],
        ),
        EntityNode(
            id="equip_001",
            entity_type="equipment",
            canonical_name="Boeing 737 MAX 9",
            aliases=["737 MAX 9", "737-9"],
            subcorpus_memberships=["sub_001"],
        ),
        EntityNode(
            id="equip_002",
            entity_type="equipment",
            canonical_name="MED plug",
            aliases=["mid-exit door plug", "door plug"],
            subcorpus_memberships=["sub_001"],
        ),
        EntityNode(
            id="reg_001",
            entity_type="regulation",
            canonical_name="14 CFR Part 121",
            aliases=["Part 121"],
            subcorpus_memberships=["sub_001"],
        ),
    ]


@pytest.fixture
def sample_context():
    return {
        "subcorpus_id": "sub_001",
        "incident_scenario": (
            "On January 5, 2024, Alaska Airlines flight 1282, a Boeing 737 MAX 9, "
            "experienced a rapid decompression when the left mid-exit door plug "
            "separated from the fuselage during climb through 16,000 feet after "
            "departure from Portland International Airport."
        ),
        "connectivity_level": 2,
        "doc_index": 0,
    }


def mock_llm_call(prompt: str, model: str = "gpt-4o-mini", temperature: float = 0, dry_run: bool = False):
    """Mock LLM that returns a canned response based on prompt content."""
    if dry_run:
        return "Dry-run estimate: ~500 tokens", None
    # Return a response that includes some entities from the prompt
    return (
        "FACTUAL REPORT\n\n"
        "1. ACCIDENT INFORMATION\n\n"
        "On the date in question, the aircraft experienced a structural failure. "
        "The Boeing 737 MAX 9 operated by Alaska Airlines was climbing through "
        "16,000 feet when the mid-exit door plug separated. The FAA subsequently "
        "issued an Airworthiness Directive grounding all affected aircraft. "
        "The investigation was conducted under 14 CFR Part 121.\n\n"
        "2. FINDINGS\n\n"
        "The examination revealed manufacturing deficiencies at the Boeing "
        "Commercial Airplanes facility."
    ), None
