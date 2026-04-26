// The Sigma-rendered graph canvas. Owns the graphology graph + Sigma
// instance, and reacts to store changes by either rebuilding (payload/view)
// or just re-applying filters/layouts.
import { useEffect, useRef } from "preact/hooks";
import { effect } from "@preact/signals";
import type Sigma from "sigma";
import type Graph from "graphology";
import {
  activeAnnotations,
  activeRawGraph,
  clearSelection,
  colorMode,
  communities,
  currentDataset,
  filters,
  focus,
  layoutKind,
  pushFocus,
  search,
  selectEdge,
  selectNode,
  selection,
  view,
} from "../state/store";
import { buildGraph, type EdgeAttrs, type NodeAttrs } from "../graph/build";
import { applyAll, neighborhood } from "../graph/filters";
import { applyLayout, stopActiveLayout } from "../graph/layouts";
import { detectCommunities } from "../graph/communities";
import { createRenderer, fitToNodes } from "../graph/renderer";
import { visibleCounts } from "./graphCounts";

export function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma<NodeAttrs, EdgeAttrs> | null>(null);
  const graphRef = useRef<Graph<NodeAttrs, EdgeAttrs> | null>(null);
  const lastBuildKey = useRef<string | null>(null);
  const lastLayoutKey = useRef<string | null>(null);

  // Build / rebuild graph when payload + view change
  useEffect(() => {
    const dispose = effect(() => {
      const raw = activeRawGraph.value;
      const ann = activeAnnotations.value;
      const ds = currentDataset.value;
      const v = view.value;
      const buildKey = `${ds}::${v}`;
      if (!raw || !containerRef.current) return;
      if (buildKey === lastBuildKey.current && graphRef.current) return;
      lastBuildKey.current = buildKey;

      // Clean previous instance — wrapped because a faulty kill mustn't
      // propagate into the caller (the loader would otherwise leave its
      // spinner up if its `payload.value = next` line throws synchronously).
      try {
        stopActiveLayout();
        sigmaRef.current?.kill();
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("[kg-viewer] sigma.kill threw — continuing rebuild", err);
      }
      sigmaRef.current = null;
      graphRef.current = null;

      let graph: ReturnType<typeof buildGraph>;
      try {
        graph = buildGraph({ raw, annotations: ann });
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("[kg-viewer] buildGraph failed for", buildKey, err);
        return;
      }
      graphRef.current = graph;

      let sigma: ReturnType<typeof createRenderer>;
      try {
        sigma = createRenderer({
        container: containerRef.current,
        graph,
        getColorMode: () => colorMode.value,
        getCommunities: () => communities.value,
        onNodeClick: (id) => {
          if (!id) {
            clearSelection();
            return;
          }
          // Highlight the 1-hop neighborhood — matches the legacy viewer's
          // single-tap behavior at tools/kg_viewer/index.html:1294.
          selectNode(id, neighborhood(graph, id, 1));
        },
        onEdgeClick: (id) => {
          if (!id) return;
          const ext = graph.extremities(id);
          selectEdge(id, new Set(ext));
        },
        onNodeDoubleClick: (id) => {
          // Same conceptual effect as the 1-hop button in the details pane:
          // hide everything outside the 1-hop neighborhood and fit the camera.
          // Click already ran (Sigma fires click before doubleClick), so the
          // selection state is current — we just push focus on top.
          pushFocus([...neighborhood(graph, id, 1)]);
        },
        onEdgeDoubleClick: (id) => {
          // Edge equivalent: union of both endpoints' 1-hop neighborhoods so
          // you see the edge in its local subgraph context.
          const [a, b] = graph.extremities(id);
          const set = new Set<string>([a, b]);
          for (const n of neighborhood(graph, a, 1)) set.add(n);
          for (const n of neighborhood(graph, b, 1)) set.add(n);
          pushFocus([...set]);
        },
        onHover: () => {
          /* could update tooltip here */
        },
        onDragStart: () => {
          // A running FA2 worker would fight the drag — stop it for the
          // duration of the gesture. User can re-trigger with L key.
          stopActiveLayout();
        },
        onDragEnd: () => {
          // Refresh once so the final position is committed cleanly.
          sigma.refresh();
        },
        });
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error("[kg-viewer] createRenderer failed for", buildKey, err);
        return;
      }
      sigmaRef.current = sigma;

      // Apply current filter state synchronously so the very first paint
      // reflects active filters/search/focus instead of a one-frame flash
      // of "everything visible" before the rAF lands.
      applyFiltersAndRefresh();

      // Run initial layout after the next frame (so the canvas has size).
      requestAnimationFrame(() => {
        if (sigmaRef.current !== sigma) return; // raced — superseded by rebuild
        void applyLayout({
          graph,
          kind: layoutKind.value,
          sigma,
          animate: false,
          onSettle: () => fitToNodes(sigma, graph.nodes()),
        });
      });

      lastLayoutKey.current = layoutKind.value;
    });

    return () => {
      dispose();
      stopActiveLayout();
      sigmaRef.current?.kill();
      sigmaRef.current = null;
      graphRef.current = null;
    };
  }, []);

  // React to layout changes
  useEffect(() => {
    return effect(() => {
      const k = layoutKind.value;
      const g = graphRef.current;
      const s = sigmaRef.current;
      if (!g || !s) return;
      if (k === lastLayoutKey.current) return;
      lastLayoutKey.current = k;
      void applyLayout({
        graph: g,
        kind: k,
        sigma: s,
        animate: true,
        onSettle: () => fitToNodes(s, focus.value.active ? focus.value.nodeIds : g.nodes()),
      });
    });
  }, []);

  // Color mode changes — recompute communities lazily
  useEffect(() => {
    return effect(() => {
      const m = colorMode.value;
      const g = graphRef.current;
      const s = sigmaRef.current;
      if (!g || !s) return;
      if (m === "community" && communities.value.size === 0) {
        const c = detectCommunities(g);
        communities.value = c;
      }
      s.refresh();
    });
  }, []);

  // Filters + search + focus + selection → reapply
  useEffect(() => {
    return effect(() => {
      // Touch reactive deps
      void filters.value;
      void search.value;
      void focus.value;
      void selection.value;
      applyFiltersAndRefresh();
    });
  }, []);

  // Auto-fit on focus changes
  useEffect(() => {
    return effect(() => {
      const f = focus.value;
      const s = sigmaRef.current;
      const g = graphRef.current;
      if (!s || !g) return;
      if (f.active && f.nodeIds.length) {
        fitToNodes(s, f.nodeIds);
      }
    });
  }, []);

  // Search auto-fit: when search produces matches, frame them
  useEffect(() => {
    return effect(() => {
      const q = search.value.trim();
      const s = sigmaRef.current;
      const g = graphRef.current;
      if (!s || !g || !q) return;
      const matches: string[] = [];
      const ql = q.toLowerCase();
      g.forEachNode((id, a) => {
        if (!a.hidden && (a.label.toLowerCase().includes(ql) || id.toLowerCase().includes(ql))) {
          matches.push(id);
        }
      });
      if (matches.length) fitToNodes(s, matches, 0.4);
    });
  }, []);

  function applyFiltersAndRefresh() {
    const g = graphRef.current;
    const s = sigmaRef.current;
    if (!g || !s) return;
    const r = applyAll({
      graph: g,
      filters: filters.value,
      search: search.value,
      focus: focus.value,
      selection: selection.value,
    });
    visibleCounts.value = { nodes: r.visibleNodes, edges: r.visibleEdges, matches: r.matches };
    s.refresh();
  }

  // Expose helpers globally for command palette / hooks
  useEffect(() => {
    const w = window as unknown as Record<string, unknown>;
    w.__kgFocusVisible = () => {
      const g = graphRef.current;
      if (!g) return;
      const visible: string[] = [];
      g.forEachNode((id, a) => {
        if (!a.hidden) visible.push(id);
      });
      if (visible.length) pushFocus(visible);
    };
    w.__kgFocusNeighborhood = (hops: number) => {
      const g = graphRef.current;
      const sel = selection.value.nodeId;
      if (!g || !sel) return;
      pushFocus([...neighborhood(g, sel, hops)]);
    };
    w.__kgFocusEdgeNeighborhood = (hops: number) => {
      const g = graphRef.current;
      const eid = selection.value.edgeId;
      if (!g || !eid || !g.hasEdge(eid)) return;
      const [a, b] = g.extremities(eid);
      const set = new Set<string>([a, b]);
      for (const n of neighborhood(g, a, hops)) set.add(n);
      for (const n of neighborhood(g, b, hops)) set.add(n);
      pushFocus([...set]);
    };
    w.__kgFitAll = () => {
      const s = sigmaRef.current;
      const g = graphRef.current;
      if (!s || !g) return;
      const visible: string[] = [];
      g.forEachNode((id, a) => {
        if (!a.hidden) visible.push(id);
      });
      fitToNodes(s, visible);
    };
    w.__kgTraceContradiction = (cId: string) => {
      const g = graphRef.current;
      const s = sigmaRef.current;
      if (!g || !s) return;
      const affected: string[] = [];
      g.forEachNode((id, a) => {
        if (a.raw && Array.isArray((a.raw as { contradiction_ids?: string[] }).contradiction_ids)) {
          // not present on RawNode; rely on annotation map (lookup elsewhere)
        }
        // We lookup via annotation through selection.highlight populated externally
        void id;
      });
      void affected;
      void cId;
    };
    return () => {
      delete w.__kgFocusVisible;
      delete w.__kgFocusNeighborhood;
      delete w.__kgFocusEdgeNeighborhood;
      delete w.__kgFitAll;
      delete w.__kgTraceContradiction;
    };
  }, []);

  return <div class="canvas" ref={containerRef} />;
}
