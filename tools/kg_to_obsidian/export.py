#!/usr/bin/env python3
"""Export CROSSFIRE knowledge-graph datasets to Obsidian vaults.

Usage:
    python tools/kg_to_obsidian/export.py [path] [--out PATH]

Discovers datasets at the given path (default: data/datasets/) and emits
a `obsidian-vault/` sibling per dataset with markdown notes for documents,
entities/claims, xrefs, clusters, contradictions, and distractors. Pre-baked
.obsidian/ config (color groups, bookmarks, workspace) is copied into each
vault.

Idempotent: re-running overwrites the output deterministically.
Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

TEMPLATE_DOT_OBSIDIAN = Path(__file__).parent / "templates" / "dot_obsidian"


# ---------------------------------------------------------------------------
# Layout detection (mirrors tools/kg_viewer/serve.py)
# ---------------------------------------------------------------------------

def detect_layout(dataset_path: Path) -> str | None:
    if (dataset_path / "gold" / "entity_graph.json").exists():
        return "entity_graph"
    for child in dataset_path.iterdir():
        if child.is_dir() and (child / "metadata" / "knowledge_graph.json").exists():
            return "claims"
    return None


def discover_datasets(root: Path) -> dict[str, tuple[Path, str]]:
    """Return {dataset_name: (path, layout)} for the given root."""
    layout = detect_layout(root)
    if layout:
        return {root.name: (root, layout)}
    out: dict[str, tuple[Path, str]] = {}
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        l = detect_layout(child)
        if l:
            out[child.name] = (child, l)
    return out


# ---------------------------------------------------------------------------
# Link merging (copied from tools/kg_viewer/serve.py to keep the two tools
# in lockstep without forcing a Python import path).
# ---------------------------------------------------------------------------

def merge_links(cross_refs: list[dict], clusters: list[dict]) -> list[dict]:
    out: list[dict] = []
    for x in cross_refs:
        claim_ids = list(x.get("claim_ids") or [])
        if not claim_ids:
            src = x.get("source_claim") or x.get("from_claim") or ""
            tgt = x.get("target_claim") or x.get("to_claim") or ""
            if src and tgt:
                claim_ids = [src, tgt]
            elif src:
                claim_ids = [src]
        rel = x.get("relationship_type") or x.get("relationship") or "cross_reference"
        rationale = x.get("rationale") or x.get("description") or None
        xid = x.get("xref_id") or x.get("reference_id") or x.get("id")
        out.append({
            "kind": "xref",
            "id": xid,
            "claim_ids": claim_ids,
            "relationship_type": rel,
            "rationale": rationale,
            "confidence": x.get("confidence"),
        })
    for cl in clusters:
        cid = cl.get("cluster_id") or cl.get("id")
        out.append({
            "kind": "cluster",
            "id": cid,
            "claim_ids": list(cl.get("claim_ids") or []),
            "relationship_type": cl.get("relation") or "cross_reference",
            "rationale": cl.get("theme") or None,
            "confidence": cl.get("confidence"),
        })
    return out


# ---------------------------------------------------------------------------
# Markdown emission helpers
# ---------------------------------------------------------------------------

_SAFE_CHARS = re.compile(r"[^\w\-.]+")

def safe_filename(name: str) -> str:
    """Slugify into a filesystem- and Obsidian-safe note name."""
    s = _SAFE_CHARS.sub("_", str(name)).strip("_.")
    return s or "_"


def normalize_doc_id(doc_id: str) -> str:
    """Strip trailing `.txt` from source_document references so chunks /
    full docs / mixed-extension references all collapse to one note.
    """
    if doc_id.endswith(".txt"):
        return doc_id[:-4]
    return doc_id


def yaml_scalar(v) -> str:
    """Render a scalar as a YAML-safe value (best-effort, stdlib-only)."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if s == "":
        return '""'
    needs_quote = (
        any(c in s for c in ':#[]{},&*?|<>=!%@`\n\t')
        or s.startswith(('-', '?', ':', '"', "'", '!', '%', '@', '`', '&', '*'))
        or s.lower() in ('true', 'false', 'null', 'yes', 'no', '~', 'on', 'off')
        or s.strip() != s
    )
    if needs_quote:
        s = s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
        return f'"{s}"'
    return s


def emit_frontmatter(props: dict, tags: list[str]) -> str:
    lines = ["---"]
    for k, v in props.items():
        if v is None:
            continue
        if isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                for item in v:
                    lines.append(f"  - {yaml_scalar(item)}")
        else:
            lines.append(f"{k}: {yaml_scalar(v)}")
    seen = set()
    clean_tags = []
    for t in tags:
        t = str(t).strip().lstrip("#")
        if t and t not in seen:
            seen.add(t)
            clean_tags.append(t)
    if clean_tags:
        lines.append("tags:")
        for t in clean_tags:
            lines.append(f"  - {t}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def wikilink(name: str, alias: str | None = None) -> str:
    n = safe_filename(name)
    if alias and alias != name:
        return f"[[{n}|{alias}]]"
    return f"[[{n}]]"


def write_note(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = frontmatter + "\n" + body.rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Vault scaffolding
# ---------------------------------------------------------------------------

def copy_obsidian_config(vault: Path) -> None:
    """Copy templates/dot_obsidian/* into <vault>/.obsidian/ (idempotent)."""
    target = vault / ".obsidian"
    if target.exists():
        shutil.rmtree(target)
    if not TEMPLATE_DOT_OBSIDIAN.exists():
        return
    shutil.copytree(TEMPLATE_DOT_OBSIDIAN, target)


def reset_dir(d: Path) -> None:
    if d.exists():
        shutil.rmtree(d)


def write_vault_readme(vault: Path, dataset_name: str, layout: str, stats: dict) -> None:
    lines = [
        f"# {dataset_name} — Obsidian vault",
        "",
        f"Generated by `tools/kg_to_obsidian/export.py` from a CROSSFIRE `{layout}` dataset.",
        "",
        "## Folders",
        "",
    ]
    if layout == "claims":
        lines += [
            "- `documents/` — one note per source document (full text in body).",
            "- `claims/` — one note per claim (subject/predicate/object triple).",
            "- `xrefs/` — pairwise cross-reference hubs (link two or more claims).",
            "- `clusters/` — multi-claim cluster hubs (3+ claims sharing a theme).",
            "- `contradictions/` — gold contradiction labels.",
            "- `distractors/` — gold distractor labels.",
        ]
    else:
        lines += [
            "- `documents/` — one note per source document (full text in body).",
            "- `entities/` — one note per canonical entity (with aliases, subcorpus memberships).",
            "- `contradictions/` — gold incoherence labels.",
            "- `distractors/` — gold distractor labels.",
        ]
    lines += [
        "",
        "## Stats",
        "",
    ]
    for k, v in stats.items():
        lines.append(f"- **{k}**: {v}")
    lines += [
        "",
        "## Suggested workflow",
        "",
        "1. Open this folder as a vault in Obsidian.",
        "2. Open the **Graph view** — color groups are pre-configured for contradictions, clusters, xrefs, and common entity types.",
        "3. Use **Local Graph** (Ctrl/Cmd+G) on any note for n-hop neighborhood inspection.",
        "4. Use the **Properties** pane to filter claims by `confidence`, `category`, etc.",
        "5. See `bookmarks` (left sidebar) for saved searches like *Multi-hop contradictions* or *Low-confidence claims*.",
        "",
        "Re-run the exporter to regenerate the vault contents — `.obsidian/` is overwritten too.",
    ]
    (vault / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Claims-layout emission
# ---------------------------------------------------------------------------

def export_claims_dataset(dataset_path: Path, vault: Path) -> dict:
    """Walk per-case dirs and emit a vault for a `claims`-layout dataset."""
    cases: list[tuple[str, Path]] = []
    for child in sorted(dataset_path.iterdir()):
        if child.is_dir() and (child / "metadata" / "knowledge_graph.json").exists():
            cases.append((child.name, child))

    multi_case = len(cases) > 1
    totals = Counter()

    # Reset vault content folders we manage. Leave .obsidian alone here (it's
    # rewritten in copy_obsidian_config()).
    for sub in ("documents", "claims", "xrefs", "clusters", "contradictions", "distractors"):
        reset_dir(vault / sub)
    # Also clear per-case folders if multi-case
    for case_name, _ in cases:
        reset_dir(vault / safe_filename(case_name))

    for case_name, case_dir in cases:
        prefix = (vault / safe_filename(case_name)) if multi_case else vault
        case_id_for_link = case_name if multi_case else None

        kg_file = case_dir / "metadata" / "knowledge_graph.json"
        kg = json.loads(kg_file.read_text(encoding="utf-8"))
        claims = kg.get("claims", [])
        cross_refs = kg.get("cross_references", [])
        clusters = kg.get("claim_clusters", [])
        links = merge_links(cross_refs, clusters)

        # Load contradictions / distractors
        contradictions = _load_jsonl_dir(case_dir / "contradictions")
        distractors = _load_jsonl_dir(case_dir / "distractors")

        # Emit notes
        emit_claims_layout(
            prefix=prefix,
            case_name=case_name if multi_case else None,
            case_dir=case_dir,
            claims=claims,
            cross_refs=cross_refs,
            clusters=clusters,
            links=links,
            contradictions=contradictions,
            distractors=distractors,
        )

        totals["cases"] += 1
        totals["documents"] += _count_unique_docs(case_dir, claims)
        totals["claims"] += len(claims)
        totals["xrefs"] += len(cross_refs)
        totals["clusters"] += len(clusters)
        totals["contradictions"] += len(contradictions)
        totals["distractors"] += len(distractors)

    return dict(totals)


def _load_jsonl_dir(d: Path) -> list[dict]:
    if not d.exists():
        return []
    # Prefer canonical gold_labels.jsonl if present
    gold = d / "gold_labels.jsonl"
    if gold.exists():
        sources = [gold]
    else:
        sources = sorted(
            f for f in d.glob("*.jsonl")
            if f.name not in ("all_contradictions.jsonl",)
        )
    out: list[dict] = []
    for jl in sources:
        with jl.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "id" not in rec:
                    rec["id"] = f"{jl.stem}_{len(out):04d}"
                out.append(rec)
    return out


def _count_unique_docs(case_dir: Path, claims: list[dict]) -> int:
    """Documents we will emit: union of anonymized_docs/*.txt and claim sources."""
    docs = set()
    anon = case_dir / "anonymized_docs"
    if anon.exists():
        for p in anon.glob("*.txt"):
            docs.add(p.stem)
    for c in claims:
        docs.add(c.get("source_document", ""))
    docs.discard("")
    return len(docs)


def emit_claims_layout(
    prefix: Path,
    case_name: str | None,
    case_dir: Path,
    claims: list[dict],
    cross_refs: list[dict],
    clusters: list[dict],
    links: list[dict],
    contradictions: list[dict],
    distractors: list[dict],
) -> None:
    # Normalize source_document on every claim (stripping trailing .txt) so
    # chunks/full-docs/mixed-extension references all collapse to one note.
    for c in claims:
        c["source_document"] = normalize_doc_id(c.get("source_document", ""))

    # Index helpers
    claim_by_id = {c["claim_id"]: c for c in claims}
    doc_to_claims: dict[str, list[str]] = defaultdict(list)
    for c in claims:
        doc_to_claims[c["source_document"]].append(c["claim_id"])

    # Map claim -> participating xrefs and clusters
    claim_to_xrefs: dict[str, list[dict]] = defaultdict(list)
    claim_to_clusters: dict[str, list[dict]] = defaultdict(list)
    for x in cross_refs:
        ids = x.get("claim_ids") or []
        if not ids:
            src = x.get("source_claim") or x.get("from_claim")
            tgt = x.get("target_claim") or x.get("to_claim")
            ids = [i for i in (src, tgt) if i]
        for cid in ids:
            claim_to_xrefs[cid].append(x)
    for cl in clusters:
        for cid in cl.get("claim_ids") or []:
            claim_to_clusters[cid].append(cl)

    # Map doc -> contradiction/distractor IDs (normalized)
    doc_to_contras: dict[str, list[str]] = defaultdict(list)
    for k in contradictions:
        for doc_ref in k.get("document_references", []):
            doc_to_contras[normalize_doc_id(doc_ref)].append(k["id"])
    doc_to_distrs: dict[str, list[str]] = defaultdict(list)
    for k in distractors:
        for doc_ref in k.get("document_references", []):
            doc_to_distrs[normalize_doc_id(doc_ref)].append(k["id"])

    # ---------- Documents ----------
    anon_dir = case_dir / "anonymized_docs"
    all_doc_ids = set(doc_to_claims.keys())
    if anon_dir.exists():
        for p in anon_dir.glob("*.txt"):
            all_doc_ids.add(p.stem)

    for doc_id in sorted(all_doc_ids):
        body_text = ""
        anon_file = anon_dir / f"{doc_id}.txt"
        if anon_file.exists():
            body_text = anon_file.read_text(encoding="utf-8")

        tags = ["document"]
        if case_name:
            tags.append(f"case/{case_name}")
        if doc_to_contras.get(doc_id):
            tags.append("contradiction-host")
        if doc_to_distrs.get(doc_id):
            tags.append("distractor-host")

        props = {
            "type": "document",
            "document_id": doc_id,
        }
        if case_name:
            props["case_id"] = case_name
        props["claim_count"] = len(doc_to_claims.get(doc_id, []))
        props["contradiction_count"] = len(doc_to_contras.get(doc_id, []))
        props["distractor_count"] = len(doc_to_distrs.get(doc_id, []))

        body = [f"# {doc_id}", ""]
        if doc_to_claims.get(doc_id):
            body.append("## Claims sourced from this document")
            body.append("")
            for cid in sorted(doc_to_claims[doc_id]):
                body.append(f"- {wikilink(cid)}")
            body.append("")
        if doc_to_contras.get(doc_id):
            body.append("## Contradictions involving this document")
            body.append("")
            for kid in doc_to_contras[doc_id]:
                body.append(f"- {wikilink(kid)}")
            body.append("")
        if doc_to_distrs.get(doc_id):
            body.append("## Distractors involving this document")
            body.append("")
            for kid in doc_to_distrs[doc_id]:
                body.append(f"- {wikilink(kid)}")
            body.append("")
        if body_text:
            body.append("## Original content")
            body.append("")
            body.append(body_text.rstrip())
            body.append("")

        path = prefix / "documents" / f"{safe_filename(doc_id)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Claims ----------
    for c in claims:
        cid = c["claim_id"]
        subj = c.get("subject", "")
        pred = c.get("predicate", "")
        obj = c.get("object", "")
        cat = c.get("category", "unknown")
        src = c.get("source_document", "")
        conf = c.get("confidence")

        tags = [
            "claim",
            f"category/{safe_filename(cat)}",
            f"predicate/{safe_filename(pred)}",
            f"doc/{safe_filename(src)}",
        ]
        if case_name:
            tags.append(f"case/{case_name}")

        props = {
            "type": "claim",
            "claim_id": cid,
            "subject": subj,
            "predicate": pred,
            "object": obj,
            "category": cat,
            "source_document": src,
            "confidence": conf,
        }
        if case_name:
            props["case_id"] = case_name

        body = [
            f"# {cid} — {subj} `{pred}` {obj}",
            "",
            f"Source: {wikilink(src)}",
            "",
        ]
        xrefs_for = claim_to_xrefs.get(cid, [])
        if xrefs_for:
            body.append("## Cross-references")
            body.append("")
            for x in xrefs_for:
                xid = x.get("xref_id") or x.get("reference_id") or x.get("id") or ""
                rel = x.get("relationship_type") or x.get("relationship") or "cross_reference"
                if xid:
                    body.append(f"- {wikilink(xid)} ({rel})")
            body.append("")
        clusters_for = claim_to_clusters.get(cid, [])
        if clusters_for:
            body.append("## Clusters")
            body.append("")
            for cl in clusters_for:
                clid = cl.get("cluster_id") or cl.get("id") or ""
                theme = cl.get("theme") or cl.get("relation") or ""
                if clid:
                    body.append(f"- {wikilink(clid)} — {theme}")
            body.append("")

        path = prefix / "claims" / f"{safe_filename(cid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Xrefs ----------
    for x in cross_refs:
        xid = x.get("xref_id") or x.get("reference_id") or x.get("id")
        if not xid:
            continue
        rel = x.get("relationship_type") or x.get("relationship") or "cross_reference"
        rationale = x.get("rationale") or x.get("description") or ""
        member_ids = x.get("claim_ids") or []
        if not member_ids:
            src = x.get("source_claim") or x.get("from_claim")
            tgt = x.get("target_claim") or x.get("to_claim")
            member_ids = [i for i in (src, tgt) if i]

        tags = ["xref", f"rel/{safe_filename(rel)}"]
        if case_name:
            tags.append(f"case/{case_name}")

        props = {
            "type": "xref",
            "xref_id": xid,
            "relationship_type": rel,
            "confidence": x.get("confidence"),
            "member_count": len(member_ids),
        }
        if case_name:
            props["case_id"] = case_name

        body = [f"# {xid} — {rel}", ""]
        if rationale:
            body.append(f"> {rationale}")
            body.append("")
        body.append("## Members")
        body.append("")
        for mid in member_ids:
            if mid in claim_by_id:
                body.append(f"- {wikilink(mid)}")
            else:
                body.append(f"- `{mid}` (claim not found)")
        body.append("")

        path = prefix / "xrefs" / f"{safe_filename(xid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Clusters ----------
    for cl in clusters:
        clid = cl.get("cluster_id") or cl.get("id")
        if not clid:
            continue
        rel = cl.get("relation") or "cross_reference"
        theme = cl.get("theme") or ""
        member_ids = list(cl.get("claim_ids") or [])

        tags = ["cluster", f"rel/{safe_filename(rel)}"]
        if case_name:
            tags.append(f"case/{case_name}")

        props = {
            "type": "cluster",
            "cluster_id": clid,
            "relation": rel,
            "theme": theme,
            "member_count": len(member_ids),
        }
        if case_name:
            props["case_id"] = case_name

        body = [f"# {clid} — {theme or rel}", ""]
        if theme and rel:
            body.append(f"Relation: `{rel}`")
            body.append("")
        body.append("## Members")
        body.append("")
        for mid in member_ids:
            if mid in claim_by_id:
                body.append(f"- {wikilink(mid)}")
            else:
                body.append(f"- `{mid}` (claim not found)")
        body.append("")

        path = prefix / "clusters" / f"{safe_filename(clid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Contradictions ----------
    for k in contradictions:
        kid = k["id"]
        scope = k.get("scope", "")
        mech = k.get("mechanism", "")
        det = k.get("detectability", "")
        gt = k.get("ground_truth")

        tags = ["contradiction"]
        if scope:
            tags.append(f"scope/{safe_filename(scope)}")
        if mech:
            tags.append(f"mechanism/{safe_filename(mech)}")
        if det:
            tags.append(f"detectability/{safe_filename(det)}")
        if case_name:
            tags.append(f"case/{case_name}")

        props = {
            "type": "contradiction",
            "label_id": kid,
            "scope": scope or None,
            "mechanism": mech or None,
            "detectability": det or None,
            "system_affinity": k.get("system_affinity"),
            "difficulty": k.get("difficulty"),
            "ground_truth": gt,
        }
        if case_name:
            props["case_id"] = case_name

        body = [f"# {kid}", ""]
        if k.get("rationale"):
            body.append(f"> {k['rationale']}")
            body.append("")
        if "original_text" in k or "modified_text" in k:
            body.append("## Texts")
            body.append("")
            if k.get("original_text"):
                body.append(f"**Original:** {k['original_text']}")
                body.append("")
            if k.get("modified_text"):
                body.append(f"**Modified:** {k['modified_text']}")
                body.append("")
        elif k.get("original_fact") or k.get("modified_fact"):
            body.append("## Facts")
            body.append("")
            if k.get("original_fact"):
                body.append(f"**Original:** {k['original_fact']}")
                body.append("")
            if k.get("modified_fact"):
                body.append(f"**Modified:** {k['modified_fact']}")
                body.append("")

        refs = k.get("document_references", [])
        if refs:
            body.append("## Documents involved")
            body.append("")
            for r in refs:
                body.append(f"- {wikilink(normalize_doc_id(r))}")
            body.append("")

        path = prefix / "contradictions" / f"{safe_filename(kid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Distractors ----------
    for k in distractors:
        kid = k["id"]
        tags = ["distractor"]
        if case_name:
            tags.append(f"case/{case_name}")
        for fld in ("scope", "mechanism", "detectability"):
            v = k.get(fld)
            if v:
                tags.append(f"{fld}/{safe_filename(v)}")

        props = {
            "type": "distractor",
            "label_id": kid,
            "scope": k.get("scope"),
            "mechanism": k.get("mechanism"),
            "detectability": k.get("detectability"),
            "ground_truth": k.get("ground_truth"),
        }
        if case_name:
            props["case_id"] = case_name

        body = [f"# {kid}", ""]
        if k.get("rationale"):
            body.append(f"> {k['rationale']}")
            body.append("")
        for src_field in ("original_text", "modified_text", "original_fact", "modified_fact", "text"):
            if k.get(src_field):
                body.append(f"**{src_field}:** {k[src_field]}")
                body.append("")
        refs = k.get("document_references", [])
        if refs:
            body.append("## Documents involved")
            body.append("")
            for r in refs:
                body.append(f"- {wikilink(normalize_doc_id(r))}")
            body.append("")

        path = prefix / "distractors" / f"{safe_filename(kid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))


# ---------------------------------------------------------------------------
# entity_graph layout emission
# ---------------------------------------------------------------------------

def export_entity_graph_dataset(dataset_path: Path, vault: Path) -> dict:
    eg_file = dataset_path / "gold" / "entity_graph.json"
    incoh_file = dataset_path / "gold" / "gold_incoherence_labels.json"
    distr_file = dataset_path / "gold" / "gold_distractor_labels.json"
    corpus_dir = dataset_path / "corpus"

    eg = json.loads(eg_file.read_text(encoding="utf-8"))
    nodes = eg.get("nodes", [])
    edges = eg.get("edges", [])

    incoherences: list[dict] = []
    if incoh_file.exists():
        data = json.loads(incoh_file.read_text(encoding="utf-8"))
        incoherences = data if isinstance(data, list) else list(data.values())

    distractors: list[dict] = []
    if distr_file.exists():
        data = json.loads(distr_file.read_text(encoding="utf-8"))
        distractors = data if isinstance(data, list) else list(data.values())

    # Reset content folders
    for sub in ("documents", "entities", "contradictions", "distractors"):
        reset_dir(vault / sub)

    # Index documents from corpus JSONL files
    documents: dict[str, dict] = {}
    if corpus_dir.exists():
        for jl in sorted(corpus_dir.glob("*.jsonl")):
            with jl.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    d = json.loads(line)
                    if "id" in d:
                        documents[d["id"]] = d

    # Index: entity -> docs (subcorpus_memberships are corpus IDs, not doc IDs;
    # we link entities to *documents* via entity_type membership) — but the
    # entity_graph schema only gives subcorpus_memberships at corpus level. We
    # link entities to subcorpora as a coarse proxy and to docs that mention
    # them only when we can detect via canonical_name presence.
    doc_to_contras: dict[str, list[str]] = defaultdict(list)
    for k in incoherences:
        for doc_ref in k.get("document_references", []):
            doc_to_contras[doc_ref].append(k.get("id", ""))
    doc_to_distrs: dict[str, list[str]] = defaultdict(list)
    for k in distractors:
        for doc_ref in k.get("document_references", []):
            doc_to_distrs[doc_ref].append(k.get("id", ""))

    # Edge index: entity_id -> [(other_entity, rel)]
    entity_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e in edges:
        s, t, rel = e.get("source"), e.get("target"), e.get("relationship_type", "related")
        if s and t:
            entity_edges[s].append((t, rel))
            entity_edges[t].append((s, f"<- {rel}"))

    # ---------- Documents ----------
    for doc_id, d in documents.items():
        dtype = d.get("document_type", "unknown")
        sub = d.get("subcorpus_id", "")
        rel = d.get("reliability_signal")
        content = d.get("content", "")

        tags = ["document", f"doctype/{safe_filename(dtype)}"]
        if sub:
            tags.append(f"sc/{safe_filename(sub)}")
        if doc_to_contras.get(doc_id):
            tags.append("contradiction-host")
        if doc_to_distrs.get(doc_id):
            tags.append("distractor-host")

        props = {
            "type": "document",
            "document_id": doc_id,
            "document_type": dtype,
            "subcorpus_id": sub or None,
            "reliability_signal": rel,
            "contradiction_count": len(doc_to_contras.get(doc_id, [])),
            "distractor_count": len(doc_to_distrs.get(doc_id, [])),
        }

        body = [f"# {doc_id}", ""]
        if doc_to_contras.get(doc_id):
            body.append("## Contradictions involving this document")
            body.append("")
            for kid in doc_to_contras[doc_id]:
                if kid:
                    body.append(f"- {wikilink(kid)}")
            body.append("")
        if doc_to_distrs.get(doc_id):
            body.append("## Distractors involving this document")
            body.append("")
            for kid in doc_to_distrs[doc_id]:
                if kid:
                    body.append(f"- {wikilink(kid)}")
            body.append("")
        if content:
            body.append("## Original content")
            body.append("")
            body.append(content.rstrip())
            body.append("")

        path = vault / "documents" / f"{safe_filename(doc_id)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Entities ----------
    for n in nodes:
        nid = n["id"]
        etype = n.get("entity_type", "unknown")
        canon = n.get("canonical_name", nid)
        aliases = n.get("aliases", [])
        subcorps = n.get("subcorpus_memberships", [])

        tags = ["entity", f"entity/{safe_filename(etype)}"]
        for s in subcorps:
            tags.append(f"sc/{safe_filename(s)}")

        props = {
            "type": "entity",
            "entity_id": nid,
            "entity_type": etype,
            "canonical_name": canon,
            "aliases": aliases,
            "subcorpus_memberships": subcorps,
        }

        body = [f"# {nid} — {canon}", ""]
        if aliases:
            body.append("**Aliases:** " + ", ".join(aliases))
            body.append("")
        rel_edges = entity_edges.get(nid, [])
        if rel_edges:
            body.append("## Relationships")
            body.append("")
            for other, rel in rel_edges:
                body.append(f"- `{rel}` → {wikilink(other)}")
            body.append("")
        if subcorps:
            body.append("## Subcorpus memberships")
            body.append("")
            for s in subcorps:
                body.append(f"- `{s}`")
            body.append("")

        path = vault / "entities" / f"{safe_filename(nid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Contradictions (incoherences) ----------
    for k in incoherences:
        kid = k.get("id") or f"incoherence_{len(incoherences):04d}"
        scope = k.get("scope", "")
        mech = k.get("mechanism", "")
        det = k.get("detectability", "")

        tags = ["contradiction"]
        for fld, v in (("scope", scope), ("mechanism", mech), ("detectability", det)):
            if v:
                tags.append(f"{fld}/{safe_filename(v)}")

        props = {
            "type": "contradiction",
            "label_id": kid,
            "scope": scope or None,
            "mechanism": mech or None,
            "detectability": det or None,
            "system_affinity": k.get("system_affinity"),
        }

        body = [f"# {kid}", ""]
        if k.get("original_fact") or k.get("modified_fact"):
            body.append("## Facts")
            body.append("")
            if k.get("original_fact"):
                body.append(f"**Original:** {k['original_fact']}")
                body.append("")
            if k.get("modified_fact"):
                body.append(f"**Modified:** {k['modified_fact']}")
                body.append("")
        refs = k.get("document_references", [])
        if refs:
            body.append("## Documents involved")
            body.append("")
            for r in refs:
                body.append(f"- {wikilink(normalize_doc_id(r))}")
            body.append("")

        path = vault / "contradictions" / f"{safe_filename(kid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    # ---------- Distractors ----------
    for k in distractors:
        kid = k.get("id") or f"distractor_{len(distractors):04d}"
        tags = ["distractor"]
        for fld in ("scope", "mechanism", "detectability"):
            v = k.get(fld)
            if v:
                tags.append(f"{fld}/{safe_filename(v)}")

        props = {
            "type": "distractor",
            "label_id": kid,
            "scope": k.get("scope"),
            "mechanism": k.get("mechanism"),
            "detectability": k.get("detectability"),
        }

        body = [f"# {kid}", ""]
        for src_field in ("original_fact", "modified_fact", "original_text", "modified_text", "text"):
            if k.get(src_field):
                body.append(f"**{src_field}:** {k[src_field]}")
                body.append("")
        refs = k.get("document_references", [])
        if refs:
            body.append("## Documents involved")
            body.append("")
            for r in refs:
                body.append(f"- {wikilink(normalize_doc_id(r))}")
            body.append("")

        path = vault / "distractors" / f"{safe_filename(kid)}.md"
        write_note(path, emit_frontmatter(props, tags), "\n".join(body))

    return {
        "documents": len(documents),
        "entities": len(nodes),
        "edges": len(edges),
        "contradictions": len(incoherences),
        "distractors": len(distractors),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def export_dataset(name: str, path: Path, layout: str, out_root: Path | None) -> dict:
    if out_root is not None:
        vault = out_root / "obsidian-vault" if out_root.name != "obsidian-vault" else out_root
    else:
        vault = path / "obsidian-vault"
    vault.mkdir(parents=True, exist_ok=True)

    if layout == "claims":
        stats = export_claims_dataset(path, vault)
    else:
        stats = export_entity_graph_dataset(path, vault)

    copy_obsidian_config(vault)
    write_vault_readme(vault, name, layout, stats)
    return {"vault": str(vault), **stats}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export CROSSFIRE KG datasets to Obsidian vaults",
    )
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("data/datasets"),
        help="Dataset directory or parent (default: data/datasets/)",
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help="Override the vault output path (single-dataset mode only)",
    )
    args = parser.parse_args()

    root = args.path.resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        return 1

    datasets = discover_datasets(root)
    if not datasets:
        print(f"Error: no valid datasets found in {root}", file=sys.stderr)
        return 1

    if args.out is not None and len(datasets) > 1:
        print("Error: --out is only supported when exporting a single dataset", file=sys.stderr)
        return 1

    for name, (path, layout) in datasets.items():
        print(f"Exporting {name} ({layout})...", end=" ", flush=True)
        info = export_dataset(name, path, layout, args.out)
        bits = [f"vault={info['vault']}"]
        for k in ("documents", "entities", "claims", "xrefs", "clusters", "contradictions", "distractors", "cases"):
            if k in info:
                bits.append(f"{k}={info[k]}")
        print(" ".join(bits))

    return 0


if __name__ == "__main__":
    sys.exit(main())
