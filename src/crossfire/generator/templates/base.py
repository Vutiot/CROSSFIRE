"""Base template with shared logic for all document type templates."""

import hashlib
import random

from loguru import logger

from crossfire.shared.schemas.entities import EntityNode
from crossfire.shared.seed_manager import SeedManager


class BaseTemplate:
    """Base class for document type templates.

    Subclasses must set `doc_type`, `word_count_range`, and implement
    `_system_prompt()` and `_content_instructions()`.
    """

    doc_type: str = ""
    word_count_range: tuple[int, int] = (500, 1500)
    # Base reliability range — subclasses can override
    reliability_range: tuple[float, float] = (0.6, 1.0)

    def generate(
        self,
        entities: list[EntityNode],
        context: dict,
        llm,
        seed_mgr: SeedManager,
        index: int = 0,
    ) -> tuple[str | None, str | None]:
        """Generate document content. Returns (text, error)."""
        seed = seed_mgr.get_seed(f"template_{self.doc_type}", index)
        selected = self.select_entities(entities, seed)
        prompt = self.build_prompt(selected, context, seed)

        logger.debug(f"Generating {self.doc_type} (index={index}, entities={len(selected)})")
        text, error = llm(prompt)
        if error:
            return None, f"LLM call failed for {self.doc_type}: {error}"
        return text, None

    def build_prompt(self, entities: list[EntityNode], context: dict, seed: int) -> str:
        """Build the full LLM prompt."""
        entity_block = self._format_entity_references(entities, seed)
        scenario = context.get("incident_scenario", "an aviation incident under investigation")
        word_min, word_max = self.word_count_range

        return (
            f"{self._system_prompt()}\n\n"
            f"INCIDENT CONTEXT:\n{scenario}\n\n"
            f"ENTITIES TO REFERENCE (use varied naming — abbreviations, full names, acronyms):\n"
            f"{entity_block}\n\n"
            f"{self._content_instructions()}\n\n"
            f"LENGTH: Write approximately {word_min}-{word_max} words.\n"
            f"OUTPUT: Write only the document content. No meta-commentary."
        )

    def select_entities(self, entities: list[EntityNode], seed: int) -> list[EntityNode]:
        """Deterministically select a subset of entities for this document."""
        if not entities:
            return []

        rng = random.Random(seed)
        subcorpus_entities = list(entities)

        # Select 3-8 entities
        count = min(rng.randint(3, 8), len(subcorpus_entities))

        # Prioritize: at least 1 org + 1 equipment when available
        orgs = [e for e in subcorpus_entities if e.entity_type == "organization"]
        equip = [e for e in subcorpus_entities if e.entity_type == "equipment"]
        others = [e for e in subcorpus_entities if e.entity_type not in ("organization", "equipment")]

        selected = []
        if orgs:
            selected.append(rng.choice(orgs))
        if equip:
            selected.append(rng.choice(equip))

        remaining = [e for e in subcorpus_entities if e not in selected]
        rng.shuffle(remaining)
        while len(selected) < count and remaining:
            selected.append(remaining.pop())

        return selected

    def compute_reliability(self, seed: int) -> float:
        """Compute a deterministic reliability signal for this document."""
        rng = random.Random(seed)
        lo, hi = self.reliability_range
        return round(lo + rng.random() * (hi - lo), 3)

    def _format_entity_references(self, entities: list[EntityNode], seed: int) -> str:
        """Format entities with alias variation."""
        if not entities:
            return "(no specific entities)"

        rng = random.Random(seed + 1)
        lines = []
        for e in entities:
            # Pick a random alias or canonical name
            forms = [e.canonical_name] + e.aliases if e.aliases else [e.canonical_name]
            chosen = rng.choice(forms)
            lines.append(f"- {chosen} (type: {e.entity_type})")
        return "\n".join(lines)

    def _system_prompt(self) -> str:
        """Return the system/role prompt. Override in subclasses."""
        raise NotImplementedError

    def _content_instructions(self) -> str:
        """Return content and structure instructions. Override in subclasses."""
        raise NotImplementedError
