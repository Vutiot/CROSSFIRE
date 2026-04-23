#!/usr/bin/env python3
"""Lightweight data server for the CROSSFIRE KG viewer.

Usage:
    python tools/kg_viewer/serve.py [datasets_dir] [--port PORT]

Discovers all datasets under the given directory (default: data/datasets/)
and serves them all from a single server. Switch between datasets in the UI.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def detect_layout(dataset_path: Path) -> str | None:
    for child in dataset_path.iterdir():
        if child.is_dir() and (child / "metadata" / "knowledge_graph.json").exists():
            return "claims"
    return None


def discover_datasets(root: Path) -> dict[str, Path]:
    """Find all valid dataset directories under root."""
    datasets = {}
    if not root.is_dir():
        return datasets
    # Check if root itself is a dataset
    if detect_layout(root) is not None:
        datasets[root.name] = root
        return datasets
    # Otherwise scan children
    for child in sorted(root.iterdir()):
        if child.is_dir() and detect_layout(child) is not None:
            datasets[child.name] = child
    return datasets


def load_dataset(dataset_path: Path) -> dict:
    all_claims = []
    all_cross_refs = []
    all_claim_clusters = []
    all_contradictions = []
    all_distractors = []

    for case_dir in sorted(dataset_path.iterdir()):
        kg_file = case_dir / "metadata" / "knowledge_graph.json"
        if not case_dir.is_dir() or not kg_file.exists():
            continue

        with open(kg_file) as f:
            kg = json.load(f)
        all_claims.extend(kg.get("claims", []))
        all_cross_refs.extend(kg.get("cross_references", []))
        all_claim_clusters.extend(kg.get("claim_clusters", []))

        contra_dir = case_dir / "contradictions"
        if contra_dir.exists():
            gold_file = contra_dir / "gold_labels.jsonl"
            if gold_file.exists():
                sources = [gold_file]
            else:
                sources = sorted(
                    f for f in contra_dir.glob("*.jsonl")
                    if f.name not in ("all_contradictions.jsonl", "gold_labels.jsonl")
                )
            for jl_file in sources:
                with open(jl_file) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            c = json.loads(line)
                            if "id" not in c:
                                c["id"] = f"c_{len(all_contradictions)}"
                            all_contradictions.append(c)

    doc_claims = defaultdict(list)
    for claim in all_claims:
        doc_claims[claim["source_document"]].append(claim)

    doc_categories = defaultdict(lambda: defaultdict(int))
    for claim in all_claims:
        cat = claim.get("category", "unknown")
        doc_categories[claim["source_document"]][cat] += 1

    nodes = []
    for doc_name, claims in sorted(doc_claims.items()):
        top_cat = max(doc_categories[doc_name], key=doc_categories[doc_name].get)
        nodes.append({
            "id": doc_name,
            "entity_type": top_cat,
            "canonical_name": doc_name.replace("_", " ").title(),
            "aliases": [],
            "claim_count": len(claims),
            "category_breakdown": dict(doc_categories[doc_name]),
        })

    # Shared entities: docs mentioning the same subject
    subject_docs = defaultdict(set)
    for claim in all_claims:
        subject_docs[claim["subject"]].add(claim["source_document"])

    entity_edges = Counter()
    for subject, docs in subject_docs.items():
        doc_list = sorted(docs)
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                entity_edges[(doc_list[i], doc_list[j])] += 1

    # Shared facts: docs with same (subject, predicate) — same fact stated across docs
    fact_docs = defaultdict(set)
    for claim in all_claims:
        fact_key = (claim["subject"], claim["predicate"])
        fact_docs[fact_key].add(claim["source_document"])

    fact_edges = Counter()
    for fact_key, docs in fact_docs.items():
        doc_list = sorted(docs)
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                fact_edges[(doc_list[i], doc_list[j])] += 1

    edges = []
    edge_set = set()
    for (d1, d2), count in fact_edges.most_common():
        edge_set.add((d1, d2))
        edges.append({
            "source": d1, "target": d2,
            "relationship_type": "shared_facts",
            "weight": count,
        })
    for (d1, d2), count in entity_edges.most_common():
        if (d1, d2) not in edge_set:
            edges.append({
                "source": d1, "target": d2,
                "relationship_type": "shared_entities",
                "weight": count,
            })

    graph = {"nodes": nodes, "edges": edges}

    annotations = {}
    for node in nodes:
        annotations[node["id"]] = {
            "contradiction_ids": [], "distractor_ids": [],
            "contradiction_count": 0, "distractor_count": 0,
        }

    for i, c in enumerate(all_contradictions):
        cid = c.get("id", f"c_{i}")
        for doc_ref in c.get("document_references", []):
            if doc_ref in annotations:
                annotations[doc_ref]["contradiction_ids"].append(cid)
                annotations[doc_ref]["contradiction_count"] += 1

    # Merge pairwise cross-references and multi-claim clusters into a single
    # list of "link records" that both graph builders iterate over. Clusters
    # contribute N(N-1)/2 pairwise edges that all share the cluster's
    # categorical relation as `relationship_type` and the prose `theme` as
    # `rationale` — so the rel-type filter stays clean and the prose lives
    # on the edge's sidebar detail rather than being used as a category.
    links = _merge_links(all_cross_refs, all_claim_clusters)

    # Build entity-centric view (subjects with 3+ claims as nodes)
    entity_graph, entity_annotations = build_entity_graph(
        all_claims, links, all_contradictions
    )

    # Build claim-level graph
    claims_graph, claims_annotations = build_claims_graph(
        all_claims, links, all_contradictions
    )

    return {
        "dataset_name": dataset_path.name,
        "layout": "claims",
        "graph": graph,
        "entity_graph": entity_graph,
        "entity_annotations": entity_annotations,
        "claims_graph": claims_graph,
        "claims_annotations": claims_annotations,
        "contradictions": all_contradictions,
        "distractors": all_distractors,
        "claims": all_claims,
        "cross_references": all_cross_refs,
        "claim_clusters": all_claim_clusters,
        "node_annotations": annotations,
        "stats": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_claims": len(all_claims),
            "total_cross_references": len(all_cross_refs),
            "total_claim_clusters": len(all_claim_clusters),
            "total_contradictions": len(all_contradictions),
            "total_distractors": len(all_distractors),
        },
    }


def _merge_links(cross_refs: list[dict], clusters: list[dict]) -> list[dict]:
    """Unify pairwise cross-refs and multi-claim clusters into one list of
    link records with a consistent shape: {claim_ids, relationship_type,
    rationale}. Tolerates the legacy xref shapes (source_claim/target_claim,
    from_claim/to_claim) and the raw free-text `relationship` field.
    """
    out: list[dict] = []
    for x in cross_refs:
        claim_ids = x.get("claim_ids") or []
        if not claim_ids:
            src = x.get("source_claim") or x.get("from_claim") or ""
            tgt = x.get("target_claim") or x.get("to_claim") or ""
            if src and tgt:
                claim_ids = [src, tgt]
            elif src:
                claim_ids = [src]
        rel = x.get("relationship_type") or x.get("relationship") or "cross_reference"
        rationale = x.get("rationale") or x.get("description") or None
        out.append({
            "claim_ids": list(claim_ids),
            "relationship_type": rel,
            "rationale": rationale,
        })
    for cl in clusters:
        out.append({
            "claim_ids": list(cl.get("claim_ids") or []),
            "relationship_type": cl.get("relation") or "cross_reference",
            "rationale": cl.get("theme") or None,
        })
    return out


def build_entity_graph(claims, links, contradictions, min_claims=3):
    """Build an entity-centric graph from KG claims.

    Nodes = unique subjects with >= min_claims mentions.
    Edges = subjects linked via cross-references / claim-clusters, or strong
    document co-occurrence. `links` is the unified list produced by
    _merge_links().
    """

    # Count claims per subject and gather metadata
    subject_claims = defaultdict(list)
    for c in claims:
        subject_claims[c["subject"]].append(c)

    # Filter to subjects with enough claims
    entities = {s: cs for s, cs in subject_claims.items() if len(cs) >= min_claims}

    # Build nodes
    nodes = []
    for subject, cs in sorted(entities.items(), key=lambda x: -len(x[1])):
        cats = Counter(c.get("category", "unknown") for c in cs)
        top_cat = cats.most_common(1)[0][0]
        docs = sorted(set(c["source_document"] for c in cs))
        predicates = sorted(set(c["predicate"] for c in cs))
        nodes.append({
            "id": subject,
            "entity_type": top_cat,
            "canonical_name": subject.replace("_", " "),
            "aliases": predicates[:5],  # show top predicates as "aliases"
            "subcorpus_memberships": docs,
            "claim_count": len(cs),
            "category_breakdown": dict(cats),
        })

    entity_ids = set(entities.keys())

    # Edges from cross-references / clusters (subjects of linked claims)
    claim_to_subject = {c["claim_id"]: c["subject"] for c in claims}
    edges = []
    edge_set = set()

    for link in links:
        subjects = set()
        for cid in link["claim_ids"]:
            s = claim_to_subject.get(cid)
            if s and s in entity_ids:
                subjects.add(s)
        sub_list = sorted(subjects)
        rel = link["relationship_type"]
        rationale = link.get("rationale")
        for i in range(len(sub_list)):
            for j in range(i + 1, len(sub_list)):
                key = (sub_list[i], sub_list[j])
                if key not in edge_set:
                    edge_set.add(key)
                    edge = {
                        "source": sub_list[i],
                        "target": sub_list[j],
                        "relationship_type": rel,
                    }
                    if rationale:
                        edge["rationale"] = rationale
                    edges.append(edge)

    # Edges from document co-occurrence (both entities in same doc, weighted)
    doc_entities = defaultdict(set)
    for c in claims:
        if c["subject"] in entity_ids:
            doc_entities[c["source_document"]].add(c["subject"])

    cooccurrence = Counter()
    for doc, subs in doc_entities.items():
        sub_list = sorted(subs)
        for i in range(len(sub_list)):
            for j in range(i + 1, len(sub_list)):
                cooccurrence[(sub_list[i], sub_list[j])] += 1

    # Add co-occurrence edges with weight >= 2 (appear together in 2+ docs)
    for (s1, s2), weight in cooccurrence.most_common():
        if weight < 2:
            break
        key = (s1, s2)
        if key not in edge_set:
            edge_set.add(key)
            edges.append({
                "source": s1,
                "target": s2,
                "relationship_type": f"co-occurs ({weight} docs)",
            })

    graph = {"nodes": nodes, "edges": edges}

    # Link contradictions to entity nodes via document_references → claims → subjects
    doc_to_entities = defaultdict(set)
    for c in claims:
        if c["subject"] in entity_ids:
            doc_to_entities[c["source_document"]].add(c["subject"])

    annotations = {}
    for node in nodes:
        annotations[node["id"]] = {
            "contradiction_ids": [], "distractor_ids": [],
            "contradiction_count": 0, "distractor_count": 0,
        }

    for i, c in enumerate(contradictions):
        cid = c.get("id", f"c_{i}")
        affected = set()
        for doc_ref in c.get("document_references", []):
            affected.update(doc_to_entities.get(doc_ref, set()))
        for eid in affected:
            if eid in annotations:
                annotations[eid]["contradiction_ids"].append(cid)
                annotations[eid]["contradiction_count"] += 1

    return graph, annotations


def build_claims_graph(claims, links, contradictions):
    """Build a claim-level graph from KG claims.

    Nodes = individual claims.
    Edges = claims linked via the same cross-reference group or claim cluster.
    `links` is the unified list produced by _merge_links().
    """
    nodes = []
    for c in claims:
        subj = c["subject"]
        obj = c["object"]
        label = f"{subj} \u2192 {obj}"
        if len(label) > 50:
            label = label[:47] + "\u2026"
        nodes.append({
            "id": c["claim_id"],
            "entity_type": c.get("category", "unknown"),
            "canonical_name": label,
            "aliases": [c.get("predicate", "")],
            "subcorpus_memberships": [c["source_document"]],
            "claim_count": 1,
            "category_breakdown": {c.get("category", "unknown"): 1},
            "confidence": c.get("confidence", 0.9),
            "predicate": c.get("predicate", ""),
            "object": obj,
            "subject": subj,
            "source_document": c["source_document"],
        })

    claim_ids_set = {c["claim_id"] for c in claims}

    edges = []
    edge_set = set()
    for link in links:
        # Filter to claims that exist in this dataset
        valid = sorted(cid for cid in link["claim_ids"] if cid in claim_ids_set)
        rel = link["relationship_type"]
        rationale = link.get("rationale")
        for i in range(len(valid)):
            for j in range(i + 1, len(valid)):
                key = (valid[i], valid[j])
                if key not in edge_set:
                    edge_set.add(key)
                    edge = {
                        "source": valid[i],
                        "target": valid[j],
                        "relationship_type": rel,
                    }
                    if rationale:
                        edge["rationale"] = rationale
                    edges.append(edge)

    graph = {"nodes": nodes, "edges": edges}

    # Build claim_id -> source_document mapping for contradiction linking
    claim_doc = {c["claim_id"]: c["source_document"] for c in claims}
    doc_to_claims = defaultdict(set)
    for cid, doc in claim_doc.items():
        doc_to_claims[doc].add(cid)

    annotations = {}
    for node in nodes:
        annotations[node["id"]] = {
            "contradiction_ids": [], "distractor_ids": [],
            "contradiction_count": 0, "distractor_count": 0,
        }

    for i, contra in enumerate(contradictions):
        cid = contra.get("id", f"c_{i}")
        affected = set()
        for doc_ref in contra.get("document_references", []):
            affected.update(doc_to_claims.get(doc_ref, set()))
        for claim_id in affected:
            if claim_id in annotations:
                annotations[claim_id]["contradiction_ids"].append(cid)
                annotations[claim_id]["contradiction_count"] += 1

    return graph, annotations


def build_payload(dataset_path: Path) -> dict:
    return load_dataset(dataset_path)


class ViewerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, payloads=None, dataset_names=None, viewer_dir=None, **kwargs):
        self._payloads = payloads
        self._dataset_names = dataset_names
        self._viewer_dir = viewer_dir
        super().__init__(*args, directory=str(viewer_dir), **kwargs)

    def do_GET(self):
        if self.path == "/api/datasets":
            data = json.dumps(self._dataset_names).encode()
            self._respond_json(data)
        elif self.path.startswith("/api/data/"):
            name = self.path[len("/api/data/"):]
            if name in self._payloads:
                data = json.dumps(self._payloads[name]).encode()
                self._respond_json(data)
            else:
                self.send_error(404, f"Dataset '{name}' not found")
        elif self.path == "/api/data":
            # Backward compat: serve the first dataset
            first = self._dataset_names[0] if self._dataset_names else None
            if first:
                data = json.dumps(self._payloads[first]).encode()
                self._respond_json(data)
            else:
                self.send_error(404, "No datasets loaded")
        else:
            super().do_GET()

    def _respond_json(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(data))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="CROSSFIRE KG Viewer server")
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("data/datasets"),
        help="Dataset directory or parent containing multiple datasets (default: data/datasets/)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    args = parser.parse_args()

    root = args.path.resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    datasets = discover_datasets(root)
    if not datasets:
        print(f"Error: no valid datasets found in {root}", file=sys.stderr)
        sys.exit(1)

    payloads = {}
    dataset_names = []
    for name, path in datasets.items():
        print(f"Loading {name}...", end=" ")
        payload = build_payload(path)
        payloads[name] = payload
        dataset_names.append(name)
        s = payload["stats"]
        info = f"nodes={s['total_nodes']}, edges={s['total_edges']}, contradictions={s['total_contradictions']}"
        if "total_claims" in s:
            info += f", claims={s['total_claims']}"
        print(f"({payload['layout']}) {info}")

    print(f"\n{len(payloads)} dataset(s) loaded. Serving at http://localhost:{args.port}")

    viewer_dir = Path(__file__).parent.resolve()
    handler = partial(ViewerHandler, payloads=payloads, dataset_names=dataset_names, viewer_dir=viewer_dir)
    server = HTTPServer(("", args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
