# KG → Obsidian Exporter

Generate an Obsidian vault from any CROSSFIRE knowledge-graph dataset. Lets you
inspect, filter, and search the KG with Obsidian's native graph view, color
groups, properties pane, tag tree, and full-text search — instead of reaching
for a custom viewer every time we add a new filter dimension.

The HTML viewer at [tools/kg_viewer/](../kg_viewer/) is still around for
quick interactive exploration. Use this exporter when you want to slice the
data along arbitrary tags / properties.

## Usage

```bash
# Export every dataset under data/datasets/
python tools/kg_to_obsidian/export.py

# Export a specific dataset
python tools/kg_to_obsidian/export.py data/datasets/v1-test/

# Custom output directory (single-dataset mode only)
python tools/kg_to_obsidian/export.py data/datasets/v1-test/ --out /tmp/vault
```

Each dataset gets a sibling `obsidian-vault/` directory:

```
data/datasets/<name>/obsidian-vault/
  .obsidian/                      # Pre-baked workspace, color groups, bookmarks
  README.md
  documents/<doc_id>.md           # Source documents (full text in body)
  entities/<entity_id>.md         # Canonical entities (entity_graph layout)
  claims/<claim_id>.md            # Subject/predicate/object triples (claims layout)
  xrefs/<xref_id>.md              # Pairwise cross-reference hubs
  clusters/<cluster_id>.md        # Multi-claim cluster hubs
  contradictions/<id>.md
  distractors/<id>.md
```

Open `obsidian-vault/` as a vault in Obsidian. The graph view, color groups,
and bookmarks are all pre-configured.

The exporter is idempotent — re-running on the same dataset overwrites the
vault deterministically. Only stdlib is used.

## Filter mapping (HTML viewer → Obsidian)

| HTML viewer feature | Obsidian native equivalent | Status |
|---|---|---|
| Tri-state pill: entity types | Color groups + `tag:#entity/<type>` (include) / `-tag:#entity/<type>` (exclude) | Kept (two-state per group) |
| Tri-state pill: relationship types | Color groups on `tag:#predicate/*` and `tag:#rel/*` | Kept |
| Color by entity type | Pre-configured color groups in `.obsidian/graph.json` | Kept |
| Search by name/alias | Native Obsidian search | Kept (better) |
| Click-to-inspect | Backlinks pane + properties pane | Kept (better) |
| Document / Entity / Claim views | Path filters (`path:documents/`, `path:claims/`, …) saved as bookmarks | Kept |
| Contradictions overlay | Color group on `tag:#contradiction` | Kept |
| Distractors overlay | Color group on `tag:#distractor` | Kept |
| N-hop isolate (1-hop / 2-hop) | Local Graph view with depth slider | Kept (native) |
| Focus mode | Toggle filter groups; graph re-runs forces | Kept (automatic) |
| Force-directed layout | Native | Kept |
| Circle / grid / hierarchy layouts | — | Dropped (Obsidian only has force-directed) |
| Markov clustering coloring | — | Dropped (no native equivalent) |
| Edge labels on graph | — | Dropped (preserved instead in xref/cluster hub notes) |
| Trace contradiction (isolate subgraph) | Open contradiction note → Local Graph (1-hop) | Simplified |
| Copy-link / URL view persistence | Per-vault `.obsidian/workspace.json` + bookmarks | Simplified |
| Confidence threshold filter | Properties view filter on `confidence ≥ X` | New (free win) |

## What it surfaces

Because every claim, document, xref, cluster, and label becomes a markdown
note with frontmatter properties and tags, *anything missing from the source
JSON is immediately visible*. Examples found while building this:

- COPA claims have `category: unknown` (Phase 3 of `agent_plan.md` lists
  categories but the schema example omits the field) — every COPA claim ends
  up under `tag:#category/unknown`.
- COPA produces no clusters (only pairwise xrefs) — the `clusters/` folder
  is empty for COPA datasets.
- COPA produces no entities and no gold contradiction labels — those folders
  are empty too.
- v1-test cases reference `meteorology_report.txt` (with extension) in some
  claims and `meteorology_report` (without) in others; the exporter
  normalises the trailing `.txt` so the wikilinks resolve, but the upstream
  inconsistency is worth fixing.
- Multiple v1-test claims point at chunked source documents
  (`001_WEATHER_STUDY_chunk_003.txt`) for which no anonymized document file
  exists.

## Templates

`templates/dot_obsidian/` is copied verbatim into each generated vault as
`.obsidian/`. Edit those files to change the default color groups, saved
searches, or which sidebar panes open.

To customise per-dataset, tweak the vault's own `.obsidian/` after export
— the exporter overwrites it on re-run, so commit any changes to the
template if you want them to stick.
