"""Graph-native auditing strategy — KG construction + structural anomaly detection (FR19).

Builds a knowledge graph from corpus documents, then detects structural
anomalies (conflicting attributes, contradictory relationships) as contradictions.
Exposes internal claims for Layer 1 representation quality evaluation (FR27).

This story is contingent on experimental feasibility. If graph-native proves
unviable, delete this file — no changes needed to HybridPipeline.
"""

import json
from pathlib import Path
from typing import Callable

from loguru import logger

from crossfire.pipeline.strategies.base import GraphResult, GraphStrategy
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.knowledge_graph import KnowledgeGraphClaim
from crossfire.shared.schemas.reports import DetectedContradiction
from crossfire.shared.seed_manager import SeedManager

_EXTRACT_ENTITIES_PROMPT = """\
Extract all entities and their relationships from this document. \
Entities include: people, organizations, equipment, locations, dates, \
technical components, regulations, and measurements.

Document ID: {doc_id}

--- DOCUMENT ---
{content}
--- END ---

Return a JSON object with:
- "claims": array of {{"subject": str, "predicate": str, "object": str, "confidence": float}}
- "relationships": array of {{"source": str, "target": str, "type": str}}

Return ONLY the JSON object, no other text."""

_DETECT_ANOMALIES_PROMPT = """\
Analyze the following knowledge graph claims for structural anomalies — conflicting \
attribute values, contradictory relationships, or inconsistent facts about \
the same entities across different source documents.

Claims by source document:
{claims_summary}

For each anomaly found, return a JSON array of objects with:
- "entity_or_relationship": what is inconsistent
- "doc_a": first source document ID
- "doc_b": second source document ID
- "confidence": float 0.0-1.0
- "description": explanation of the anomaly

If no anomalies are found, return an empty array: []

Return ONLY the JSON array, no other text."""


class LLMGraphStrategy(GraphStrategy):
    """KG construction from corpus + structural anomaly detection."""

    def __init__(
        self,
        llm: Callable,
        seed_manager: SeedManager,
        model: str = "gpt-4o-mini",
    ):
        self.llm = llm
        self.seed_manager = seed_manager
        self.model = model

    def run(self, case_dir: str) -> tuple[GraphResult | None, str | None]:
        """Build KG from corpus, detect anomalies, return results + internal claims."""
        case_path = Path(case_dir)
        if not case_path.is_dir():
            return None, f"Case directory is not a directory: {case_dir}"

        documents = self._load_documents(case_path)
        if not documents:
            return GraphResult(), None

        logger.info(f"Graph strategy: extracting entities from {len(documents)} documents")

        # Phase 1: Extract claims from each document
        all_claims: list[KnowledgeGraphClaim] = []
        claims_by_doc: dict[str, list[dict]] = {}
        claim_idx = 0

        for doc in documents:
            extracted, error = self._extract_entities(doc)
            if error:
                logger.warning(f"Entity extraction failed for {doc.document_id}: {error}")
                continue

            doc_claims = extracted.get("claims", [])
            claims_by_doc[doc.document_id] = doc_claims

            for claim_data in doc_claims:
                all_claims.append(KnowledgeGraphClaim(
                    claim_id=f"claim_{claim_idx:04d}",
                    subject=claim_data.get("subject", "unknown"),
                    predicate=claim_data.get("predicate", "unknown"),
                    object=claim_data.get("object", "unknown"),
                    source_document=doc.document_id,
                    confidence=min(max(claim_data.get("confidence", 0.5), 0.0), 1.0),
                ))
                claim_idx += 1

        logger.info(f"Built knowledge graph: {len(all_claims)} claims")

        if len(claims_by_doc) < 2:
            return GraphResult(internal_claims=all_claims), None

        # Phase 2: Detect structural anomalies
        detections = self._detect_anomalies(claims_by_doc)

        logger.info(f"Graph strategy complete: {len(detections)} anomalies found")
        return GraphResult(
            detected_contradictions=detections,
            internal_claims=all_claims,
        ), None

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

    def _extract_entities(self, doc: Document) -> tuple[dict | None, str | None]:
        prompt = _EXTRACT_ENTITIES_PROMPT.format(
            doc_id=doc.document_id,
            content=doc.content,
        )
        response, error = self.llm(prompt, model=self.model, temperature=0)
        if error:
            return None, error

        try:
            data = json.loads(response)
            if not isinstance(data, dict):
                return None, f"Expected JSON object, got {type(data).__name__}"
            return data, None
        except json.JSONDecodeError as e:
            return None, f"Failed to parse entity JSON: {e}"

    def _detect_anomalies(
        self,
        claims_by_doc: dict[str, list[dict]],
    ) -> list[DetectedContradiction]:
        claims_summary = json.dumps(
            {doc_id: claims for doc_id, claims in claims_by_doc.items()},
            indent=1,
        )

        prompt = _DETECT_ANOMALIES_PROMPT.format(
            claims_summary=claims_summary,
        )
        response, error = self.llm(prompt, model=self.model, temperature=0)
        if error:
            logger.warning(f"Anomaly detection LLM call failed: {error}")
            return []

        try:
            anomalies = json.loads(response)
            if not isinstance(anomalies, list):
                logger.warning(f"Expected JSON array for anomalies, got {type(anomalies).__name__}")
                return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse anomaly JSON: {e}")
            return []

        detections: list[DetectedContradiction] = []
        for anomaly in anomalies:
            doc_a = anomaly.get("doc_a", "")
            doc_b = anomaly.get("doc_b", "")
            refs = [r for r in [doc_a, doc_b] if r]
            if not refs:
                continue

            detections.append(DetectedContradiction(
                scope="inter_doc" if len(refs) > 1 else "intra_doc",
                document_references=refs,
                text_span_start=0,
                text_span_end=0,
                evidence_text=anomaly.get("description", "Structural anomaly detected"),
                confidence=min(max(anomaly.get("confidence", 0.5), 0.0), 1.0),
                description=anomaly.get("description", "Structural anomaly detected"),
            ))

        return detections
