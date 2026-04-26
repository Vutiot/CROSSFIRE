# CROSSFIRE KG Viewer — v2

A WebGL rebuild of `tools/kg_viewer/` focused on **fluidity** (Sigma.js v3 +
graphology, ForceAtlas2 in a Web Worker, animated layout transitions, virtualized
sidebars) and **ergonomy** (command palette, keyboard nav, tri-state filters
preserved, deep-link URL hash, drop-in JSON loader).

Lives alongside the legacy viewer; nothing is removed yet.

## Quick start

Build once, then serve:

```bash
cd tools/kg_viewer_v2
npm install
npm run build
cd ../..
python tools/kg_viewer_v2/serve.py data/datasets/v1-test
# → http://localhost:8080
```

For live development with hot-reload:

```bash
# terminal 1: API server only
python tools/kg_viewer_v2/serve.py data/datasets/v1-test --api-only --port 8080

# terminal 2: Vite dev server (proxies /api → :8080)
cd tools/kg_viewer_v2
npm run dev
# → http://localhost:5173
```

## What's different from v1

| | v1 (`kg_viewer/`) | v2 (`kg_viewer_v2/`) |
|---|---|---|
| Renderer | Cytoscape.js (canvas, single thread) | **Sigma.js v3 (WebGL)** |
| Build system | None — single 78KB HTML | **Vite + TypeScript** (single bundle) |
| Layout work | Blocks main thread | **ForceAtlas2 in Web Worker** |
| Layout switch | Hard cut | **Animated 600ms transitions** |
| Sidebar lists | Render all DOM nodes | **Virtualized (windowed)** |
| Communities | Markov clustering, eager | **Louvain, lazy + cached** |
| Search | CSS class only | **Auto-pan + auto-fit to matches** |
| Focus subset | One-shot, no undo | **Stack with Backspace pop** |
| Keyboard | None | `/`, `⌘K`, `F`, `I`, `Z`, `L`, `C`, `V`, `?`, `Esc`, `Backspace` |
| Command palette | — | **`⌘K` — fuzzy across commands + nodes** |
| URL persistence | v1 plain hash | v2 base64-encoded JSON, version-prefixed |

## Keyboard

| Key | Action |
|---|---|
| `/` | Focus search |
| `⌘K` / `Ctrl+K` | Command palette |
| `F` | Toggle filter pane |
| `Shift+F` | Focus on currently visible nodes |
| `I` | Toggle details pane |
| `Z` | Fit visible nodes to viewport |
| `L` | Cycle layout |
| `C` | Toggle color mode (type ↔ community) |
| `V` | Cycle view (docs ↔ entities ↔ claims) |
| `Backspace` | Pop focus |
| `Shift+Backspace` | Clear focus |
| `?` | Show shortcuts |
| `Esc` | Close overlays / clear selection / clear search |

## Tri-state filter pills

Click an entity-type or relationship-type pill to cycle:

- **off** — neutral (no filter applied)
- **include** — show only this type
- **exclude** — hide this type

Multiple pills compose. Empty include set = no whitelist applied.

## Data shape

Same JSON contract as v1 — see `tools/kg_viewer/serve.py:build_payload()`.
The v2 server imports v1's data-loading code so both tools stay in sync.

## Drag-and-drop

If `/api/datasets` is unreachable (or you want to inspect an arbitrary
payload), drop a JSON file matching the `DatasetPayload` shape onto the
window.

## Architecture

```
src/
├── main.tsx              # entry, mounts <App>
├── types.ts              # mirror of serve.py payload
├── api.ts                # fetch + drag-drop loader
├── state/
│   ├── store.ts          # @preact/signals — global reactive state
│   └── url.ts            # base64+JSON hash persistence
├── graph/
│   ├── build.ts          # RawGraph → graphology Graph + style helpers
│   ├── filters.ts        # apply filters/search/focus to node/edge attrs
│   ├── layouts.ts        # FA2 (worker) + circle/grid/hierarchy + animation
│   ├── communities.ts    # lazy Louvain, cached per graph
│   └── renderer.ts       # Sigma instance + reducers + camera fit
└── ui/
    ├── App.tsx
    ├── Topbar.tsx
    ├── FilterPane.tsx
    ├── DetailsPane.tsx   # virtualized lists
    ├── StatusBar.tsx
    ├── GraphCanvas.tsx
    ├── CommandPalette.tsx
    ├── HelpDialog.tsx
    └── hooks/useGlobalKeys.ts
```
