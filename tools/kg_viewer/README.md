# KG Viewer

Lightweight interactive viewer for CROSSFIRE knowledge graphs, contradictions, and distractors.

## Quick Start

```bash
# Serve all datasets (auto-discovers under data/datasets/)
python tools/kg_viewer/serve.py

# Or specify a custom directory
python tools/kg_viewer/serve.py data/datasets/

# Custom port
python tools/kg_viewer/serve.py --port 3000
```

Then open `http://localhost:8080`. If multiple datasets are found, use the dropdown in the toolbar to switch between them.

## Standalone (no server)

Open `index.html` directly in a browser and drag-and-drop JSON files onto the page:
- `entity_graph.json` — required (nodes + edges)
- `gold_incoherence_labels.json` — optional (contradiction overlay)
- `gold_distractor_labels.json` — optional (distractor overlay)

## Controls

- **Zoom**: scroll wheel
- **Pan**: drag background
- **Inspect**: click any node to highlight its neighbourhood and see details
- **Search**: type in the search box to find nodes by name or alias
- **Filter**: toggle entity types, relationship types, contradiction/distractor overlays, and scope
- **Layout**: switch between force-directed, circle, grid, and hierarchy
- **Colour by**: swap node fill between entity type (default) and community cluster (Markov clustering over edge weights)
- **Trace contradiction**: click `trace` on any contradiction card to isolate the subgraph of nodes/edges participating in that conflict; click `untrace` to return
- **N-hop isolate**: `1-hop` / `2-hop` buttons in a selected node's header hide everything outside that neighbourhood; `reset` restores the current filter view
- **Copy link**: the `link` button in the toolbar copies a URL that restores the current view (dataset, filters, layout, selection, zoom/pan) when reopened

## Dataset Layouts

The server auto-detects two layouts:

| Layout | Structure | Example |
|--------|-----------|---------|
| `entity_graph` | `gold/entity_graph.json` + labels | `data/datasets/default` |
| `claims` | `*/metadata/knowledge_graph.json` + `*/contradictions/*.jsonl` | `data/datasets/v1-test` |

No Python dependencies beyond the standard library.
