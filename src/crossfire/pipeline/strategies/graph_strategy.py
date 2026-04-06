"""Graph-native auditing strategy — KG construction + structural anomaly detection (FR19).

Builds a knowledge graph from corpus documents, then detects structural
anomalies (conflicting attributes, contradictory relationships) as incoherences.
Exposes the internal graph for Layer 1 representation quality evaluation (FR27).

This story is contingent on experimental feasibility. If graph-native proves
unviable, delete this file — no changes needed to HybridPipeline.
"""

import json
from pathlib import Path
from typing import Callable

from loguru import logger

from crossfire.pipeline.strategies.base import GraphResult, GraphStrategy
from crossfire.shared.schemas.corpus import Document
from crossfire.shared.schemas.entities import EntityEdge, EntityGraph, EntityNode
from crossfire.shared.schemas.reports import DetectedIncoherence
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
- "entities": array of {{"name": str, "type": str, "attributes": {{key: value}}}}
- "relationships": array of {{"source": str, "target": str, "type": str}}

Return ONLY the JSON object, no other text."""

_DETECT_ANOMALIES_PROMPT = """\
Analyze the following knowledge graph for structural anomalies — conflicting \
attribute values, contradictory relationships, or inconsistent facts about \
the same entities across different source documents.

Entities and their attributes by source document:
{entity_summary}

Relationships:
{relationship_summary}

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

    def run(self, corpus_path: str) -> tuple[GraphResult | None, str | None]:
        """Build KG from corpus, detect anomalies, return results + internal graph."""
        corpus_dir = Path(corpus_path)
        if not corpus_dir.is_dir():
            return None, f"Corpus path is not a directory: {corpus_path}"

        documents = self._load_documents(corpus_dir)
        if not documents:
            return GraphResult(), None

        logger.info(f"Graph strategy: extracting entities from {len(documents)} documents")

        # Phase 1: Extract entities and relationships from each document
        all_entities: list[EntityNode] = []
        all_edges: list[EntityEdge] = []
        entities_by_doc: dict[str, list[dict]] = {}
        relationships_by_doc: dict[str, list[dict]] = {}
        node_idx = 0

        for doc in documents:
            extracted, error = self._extract_entities(doc)
            if error:
                logger.warning(f"Entity extraction failed for {doc.id}: {error}")
                continue

            doc_entities = extracted.get("entities", [])
            doc_relationships = extracted.get("relationships", [])
            entities_by_doc[doc.id] = doc_entities
            relationships_by_doc[doc.id] = doc_relationships

            for ent in doc_entities:
                all_entities.append(EntityNode(
                    id=f"entity_{node_idx:04d}",
                    entity_type=ent.get("type", "unknown"),
                    canonical_name=ent.get("name", "unknown"),
                    aliases=[],
                    subcorpus_memberships=[doc.subcorpus_id],
                ))
                node_idx += 1

            for rel in doc_relationships:
                all_edges.append(EntityEdge(
                    source=rel.get("source", ""),
                    target=rel.get("target", ""),
                    relationship_type=rel.get("type", "related_to"),
                ))

        internal_graph = EntityGraph(nodes=all_entities, edges=all_edges)
        logger.info(
            f"Built knowledge graph: {len(all_entities)} entities, {len(all_edges)} edges"
        )

        if len(entities_by_doc) < 2:
            return GraphResult(internal_graph=internal_graph), None

        # Phase 2: Detect structural anomalies
        detections = self._detect_anomalies(entities_by_doc, relationships_by_doc)

        logger.info(f"Graph strategy complete: {len(detections)} anomalies found")
        return GraphResult(
            detected_incoherences=detections,
            internal_graph=internal_graph,
        ), None

    def _load_documents(self, corpus_dir: Path) -> list[Document]:
        docs: list[Document] = []
        for jsonl_path in sorted(corpus_dir.glob("subcorpus_*.jsonl")):
            text = jsonl_path.read_text(encoding="utf-8").strip()
            for line in text.split("\n"):
                if line:
                    docs.append(Document.model_validate_json(line))
        return docs

    def _extract_entities(self, doc: Document) -> tuple[dict | None, str | None]:
        prompt = _EXTRACT_ENTITIES_PROMPT.format(
            doc_id=doc.id,
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
        entities_by_doc: dict[str, list[dict]],
        relationships_by_doc: dict[str, list[dict]],
    ) -> list[DetectedIncoherence]:
        entity_summary = json.dumps(
            {doc_id: ents for doc_id, ents in entities_by_doc.items()},
            indent=1,
        )
        relationship_summary = json.dumps(
            {doc_id: rels for doc_id, rels in relationships_by_doc.items()},
            indent=1,
        )

        prompt = _DETECT_ANOMALIES_PROMPT.format(
            entity_summary=entity_summary,
            relationship_summary=relationship_summary,
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

        detections: list[DetectedIncoherence] = []
        for idx, anomaly in enumerate(anomalies):
            doc_a = anomaly.get("doc_a", "")
            doc_b = anomaly.get("doc_b", "")
            refs = [r for r in [doc_a, doc_b] if r]
            if not refs:
                continue

            detections.append(DetectedIncoherence(
                id=f"graph_{idx:04d}",
                evidence_references=refs,
                confidence=min(max(anomaly.get("confidence", 0.5), 0.0), 1.0),
                description=anomaly.get("description", "Structural anomaly detected"),
            ))

        return detections
