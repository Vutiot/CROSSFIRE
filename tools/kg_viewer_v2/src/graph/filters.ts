// Apply current filter / search / focus / selection state to a graphology
// graph by mutating per-node and per-edge `hidden`, `dimmed`, `highlighted`,
// `matched` attributes. Sigma's reducers read these directly.
import Graph from "graphology";
import type { FilterState, SelectionState, FocusState } from "../types";
import type { NodeAttrs, EdgeAttrs } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;

export interface ApplyOpts {
  graph: G;
  filters: FilterState;
  search: string;
  focus: FocusState;
  selection: SelectionState;
}

export function applyAll(opts: ApplyOpts): {
  visibleNodes: number;
  visibleEdges: number;
  matches: number;
} {
  const { graph, filters: f, search, focus, selection } = opts;

  const focusSet = focus.active ? new Set(focus.nodeIds) : null;
  const sel = selection.nodeId;
  const highlight = selection.highlight;
  const q = search.trim().toLowerCase();

  let visibleNodes = 0;
  let visibleEdges = 0;
  let matches = 0;

  // First pass: nodes
  graph.forEachNode((id, attrs) => {
    let hidden = false;

    // Focus subset
    if (focusSet && !focusSet.has(id)) hidden = true;

    // Entity-type tri-state: include = whitelist, exclude = blacklist
    if (!hidden) {
      const includes = Object.entries(f.entityTypes).filter(([, v]) => v === "include");
      const excludes = Object.entries(f.entityTypes).filter(([, v]) => v === "exclude");
      if (includes.length && !includes.some(([t]) => t === attrs.entityType)) hidden = true;
      else if (excludes.some(([t]) => t === attrs.entityType)) hidden = true;
    }

    // Overlay filters: when ON, only show nodes touched by that overlay
    if (!hidden && f.showContradictions && attrs.contradictionCount === 0) hidden = true;
    if (!hidden && f.showDistractors && attrs.distractorCount === 0) hidden = true;

    attrs.hidden = hidden;

    // Search match
    const m = q && (attrs.label.toLowerCase().includes(q) || id.toLowerCase().includes(q));
    attrs.matched = !!m;
    if (m && !hidden) matches++;

    // Selection highlight set
    const isSel = id === sel;
    const isHl = highlight.has(id);
    attrs.highlighted = isSel || isHl;

    // Dim everything not highlighted when something is selected
    attrs.dimmed = !!sel && !attrs.highlighted && !attrs.matched;

    if (!hidden) visibleNodes++;
  });

  // Second pass: edges
  graph.forEachEdge((edgeId, eAttrs, source, target, sAttrs, tAttrs) => {
    let hidden = false;
    if (sAttrs.hidden || tAttrs.hidden) hidden = true;

    if (!hidden) {
      const includes = Object.entries(f.relationTypes).filter(([, v]) => v === "include");
      const excludes = Object.entries(f.relationTypes).filter(([, v]) => v === "exclude");
      if (includes.length && !includes.some(([t]) => t === eAttrs.relationshipType)) hidden = true;
      else if (excludes.some(([t]) => t === eAttrs.relationshipType)) hidden = true;
    }

    eAttrs.hidden = hidden;

    const touchesSel = !!sel && (source === sel || target === sel);
    const touchesHl = highlight.has(source) && highlight.has(target);
    eAttrs.highlighted = touchesSel || touchesHl;
    eAttrs.dimmed = !!sel && !eAttrs.highlighted;

    if (!hidden) visibleEdges++;

    // Silence unused param warnings — they're part of the iterator API
    void edgeId;
  });

  return { visibleNodes, visibleEdges, matches };
}

// One-hop neighborhood of a node (excluding hidden) — for click highlight.
export function neighborhood(graph: G, nodeId: string, hops: number = 1): Set<string> {
  const out = new Set<string>([nodeId]);
  let frontier: string[] = [nodeId];
  for (let h = 0; h < hops; h++) {
    const next: string[] = [];
    for (const id of frontier) {
      graph.forEachNeighbor(id, (nb) => {
        if (!out.has(nb)) {
          out.add(nb);
          next.push(nb);
        }
      });
    }
    frontier = next;
  }
  return out;
}
