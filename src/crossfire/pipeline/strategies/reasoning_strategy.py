"""LLM-based reasoning strategy for agentic auditing mode (FR18).

Extracts atomic claims from documents via LLM, then cross-checks claims
across document pairs to detect contradictions.
"""

import json
from itertools import combinations
from pathlib import Path
from typing import Callable

from loguru import logger

from crossfire.pipeline.strategies.base import ReasoningResult, ReasoningStrategy
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.reports import DetectedContradiction
from crossfire.shared.seed_manager import SeedManager

_EXTRACT_CLAIMS_PROMPT = """\
Extract all atomic factual claims from this document. Each claim should be a \
single verifiable statement of fact.

Document ID: {doc_id}
Document type: {doc_type}

--- DOCUMENT ---
{content}
--- END ---

Return a JSON array of claim strings. Example:
["The engine failed at 14:32 UTC", "The aircraft was a Boeing 737-800"]

Return ONLY the JSON array, no other text."""

_CHECK_CONTRADICTIONS_PROMPT = """\
Compare the following two sets of claims from different documents and identify \
any factual contradictions between them.

Document A ({doc_a_id}):
{claims_a}

Document B ({doc_b_id}):
{claims_b}

For each contradiction found, return a JSON array of objects with:
- "claim_a": the claim from Document A
- "claim_b": the contradicting claim from Document B
- "confidence": float 0.0-1.0 indicating how certain the contradiction is
- "description": brief explanation of the contradiction

If no contradictions are found, return an empty array: []

Return ONLY the JSON array, no other text."""


class LLMReasoningStrategy(ReasoningStrategy):
    """Claim extraction + cross-checking via LLM calls (CLAIRE-style)."""

    def __init__(
        self,
        llm: Callable,
        seed_manager: SeedManager,
        model: str = "gpt-4o-mini",
    ):
        self.llm = llm
        self.seed_manager = seed_manager
        self.model = model

    def run(self, case_dir: str) -> tuple[ReasoningResult | None, str | None]:
        """Extract claims from all documents, then cross-check for contradictions."""
        case_path = Path(case_dir)
        if not case_path.is_dir():
            return None, f"Case directory is not a directory: {case_dir}"

        # Load documents
        documents = self._load_documents(case_path)
        if not documents:
            return ReasoningResult(), None

        logger.info(f"Reasoning strategy: extracting claims from {len(documents)} documents")

        # Phase 1: Extract claims from each document
        claims_by_doc: dict[str, list[str]] = {}
        for doc in documents:
            claims, error = self._extract_claims(doc)
            if error:
                logger.warning(f"Claim extraction failed for {doc.document_id}: {error}")
                continue
            if claims:
                claims_by_doc[doc.document_id] = claims

        logger.info(
            f"Extracted claims from {len(claims_by_doc)}/{len(documents)} documents"
        )

        if len(claims_by_doc) < 2:
            return ReasoningResult(), None

        # Phase 2: Cross-check claims across document pairs
        detections = self._cross_check_all(claims_by_doc)

        logger.info(f"Reasoning strategy complete: {len(detections)} contradictions found")
        return ReasoningResult(detected_contradictions=detections), None

    def _load_documents(self, case_path: Path) -> list[Document]:
        docs: list[Document] = []
        anon_dir = case_path / "anonymized_docs"
        if not anon_dir.is_dir():
            return docs
        for jsonl_path in sorted(anon_dir.glob("*.jsonl")):
            text = jsonl_path.read_text(encoding="utf-8").strip()
            for line in text.split("\n"):
                if line:
                    docs.append(Document.model_validate_json(line))
        return docs

    def _extract_claims(self, doc: Document) -> tuple[list[str] | None, str | None]:
        prompt = _EXTRACT_CLAIMS_PROMPT.format(
            doc_id=doc.document_id,
            doc_type=doc.document_type,
            content=doc.content,
        )
        response, error = self.llm(prompt, model=self.model, temperature=0)
        if error:
            return None, error

        try:
            claims = json.loads(response)
            if not isinstance(claims, list):
                return None, f"Expected JSON array, got {type(claims).__name__}"
            return [str(c) for c in claims], None
        except json.JSONDecodeError as e:
            return None, f"Failed to parse claims JSON: {e}"

    def _cross_check_all(
        self, claims_by_doc: dict[str, list[str]]
    ) -> list[DetectedContradiction]:
        doc_ids = sorted(claims_by_doc.keys())
        detections: list[DetectedContradiction] = []

        for doc_a_id, doc_b_id in combinations(doc_ids, 2):
            contradictions, error = self._check_pair(
                doc_a_id,
                claims_by_doc[doc_a_id],
                doc_b_id,
                claims_by_doc[doc_b_id],
            )
            if error:
                logger.warning(
                    f"Cross-check failed for ({doc_a_id}, {doc_b_id}): {error}"
                )
                continue

            for c in contradictions:
                detections.append(
                    DetectedContradiction(
                        scope="inter_doc",
                        document_references=[doc_a_id, doc_b_id],
                        text_span_start=0,
                        text_span_end=0,
                        evidence_text=c.get("description", "Contradiction detected"),
                        confidence=c.get("confidence", 0.5),
                        description=c.get("description", "Contradiction detected"),
                    )
                )

        return detections

    def _check_pair(
        self,
        doc_a_id: str,
        claims_a: list[str],
        doc_b_id: str,
        claims_b: list[str],
    ) -> tuple[list[dict] | None, str | None]:
        prompt = _CHECK_CONTRADICTIONS_PROMPT.format(
            doc_a_id=doc_a_id,
            claims_a=json.dumps(claims_a, indent=1),
            doc_b_id=doc_b_id,
            claims_b=json.dumps(claims_b, indent=1),
        )
        response, error = self.llm(prompt, model=self.model, temperature=0)
        if error:
            return None, error

        try:
            results = json.loads(response)
            if not isinstance(results, list):
                return None, f"Expected JSON array, got {type(results).__name__}"
            return results, None
        except json.JSONDecodeError as e:
            return None, f"Failed to parse contradictions JSON: {e}"
