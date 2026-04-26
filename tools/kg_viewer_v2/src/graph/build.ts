// Adapter: RawGraph (from serve.py) → graphology Graph with attributes
// suitable for Sigma + layout algorithms.
import Graph from "graphology";
import type {
  NodeAnnotation,
  RawEdge,
  RawGraph,
  RawNode,
} from "../types";

export interface NodeAttrs {
  // visual
  x: number;
  y: number;
  size: number;
  color: string;
  label: string;
  // semantic
  raw: RawNode;
  entityType: string;
  contradictionCount: number;
  distractorCount: number;
  community?: number;
  // runtime visibility (mutated by filters)
  hidden: boolean;
  highlighted: boolean;
  dimmed: boolean;
  matched: boolean; // search match
}

export interface EdgeAttrs {
  raw: RawEdge;
  relationshipType: string;
  weight: number;
  color: string;
  size: number;
  hidden: boolean;
  dimmed: boolean;
  highlighted: boolean;
  type: "line" | "arrow";
}

// Type palette tuned for the light theme — saturated enough to read against
// paper-white but desaturated enough to coexist when many types are visible
// at once. Same hue assignments as the dark legacy palette so users carry
// over their mental color-code.
const TYPE_COLORS: Record<string, string> = {
  person: "#1f6feb",
  organization: "#8250df",
  equipment: "#1a7f37",
  regulation: "#bc4c00",
  location: "#0969da",
  temporal: "#b88600",
  mechanical: "#cf222e",
  causal: "#d4351c",
  procedural: "#0e7a78",
  meteorological: "#3692e0",
  numeric: "#9e6a03",
  personnel: "#bf3989",
  unknown: "#7a7466",
};

export function colorForType(t: string): string {
  return TYPE_COLORS[t] ?? "#8b949e";
}

export function colorForCommunity(c: number): string {
  // Categorical palette tuned for paper-white background. Derived from a
  // muted Tableau-style scheme — saturated mid-tones that hold up at
  // small sizes without flaring.
  const palette = [
    "#1f6feb", "#1a7f37", "#b88600", "#8250df", "#cf222e",
    "#0e7a78", "#bc4c00", "#3692e0", "#9e6a03", "#bf3989",
    "#0969da", "#d4351c", "#137d4f", "#a04075", "#7048d6",
  ];
  return palette[c % palette.length];
}

const REL_TYPE_DEFAULT = "#c8c2ad";
const REL_TYPE_COLORS: Record<string, string> = {
  shared_facts: "#1a7f37",
  shared_entities: "#1f6feb",
  cross_reference: "#8250df",
  contradiction: "#cf222e",
  distractor: "#bf3989",
  temporal_proximity: "#b88600",
  causal_link: "#cf222e",
  aircraft_context: "#1a7f37",
};

export function colorForRelation(rel: string): string {
  return REL_TYPE_COLORS[rel] ?? REL_TYPE_DEFAULT;
}

// Refined size scale — the original 4–22 range was too dominant and made
// hub nodes overwhelm the canvas. 3–11 keeps a clear visual hierarchy
// without nodes blotting out their own neighborhoods.
const SIZE_MIN = 3;
const SIZE_MAX = 11;

function nodeSize(claimCount: number, contradictionCount: number, maxClaims: number): number {
  const base = Math.log2((claimCount || 1) + 1) / Math.log2(maxClaims + 1);
  const sized = SIZE_MIN + base * (SIZE_MAX - SIZE_MIN);
  return sized + Math.min(contradictionCount, 6) * 0.35;
}

// Edges go thicker than before so they're visible against the lighter
// theme AND big enough for Sigma's hit-test to register clicks reliably.
// The previous 0.5px floor was effectively unclickable.
function edgeSize(weight: number): number {
  return Math.max(1.6, Math.min(5, 1.6 + Math.log2((weight || 1) + 1) * 0.9));
}

export interface BuildOpts {
  raw: RawGraph;
  annotations: Record<string, NodeAnnotation>;
}

export function buildGraph({ raw, annotations }: BuildOpts): Graph<NodeAttrs, EdgeAttrs> {
  const g = new Graph<NodeAttrs, EdgeAttrs>({ multi: false, type: "undirected" });

  const maxClaims = Math.max(1, ...raw.nodes.map((n) => n.claim_count ?? 1));

  // Initial random positions in a unit disc — FA2 / circle / grid will overwrite.
  // Using a deterministic hash so layouts converge consistently across reloads.
  for (const n of raw.nodes) {
    const ann = annotations[n.id] ?? emptyAnnotation();
    const seed = strHash(n.id);
    const angle = (seed % 1000) / 1000 * Math.PI * 2;
    const r = 0.5 + ((seed >> 5) % 500) / 1000;
    g.addNode(n.id, {
      x: Math.cos(angle) * r,
      y: Math.sin(angle) * r,
      size: nodeSize(n.claim_count ?? 1, ann.contradiction_count, maxClaims),
      color: colorForType(n.entity_type),
      label: n.canonical_name || n.id,
      raw: n,
      entityType: n.entity_type,
      contradictionCount: ann.contradiction_count,
      distractorCount: ann.distractor_count,
      hidden: false,
      highlighted: false,
      dimmed: false,
      matched: false,
    });
  }

  for (const e of raw.edges) {
    if (!g.hasNode(e.source) || !g.hasNode(e.target)) continue;
    if (e.source === e.target) continue;
    const key = edgeKey(e.source, e.target);
    if (g.hasEdge(key)) continue;
    g.addEdgeWithKey(key, e.source, e.target, {
      raw: e,
      relationshipType: e.relationship_type,
      weight: e.weight ?? 1,
      color: colorForRelation(e.relationship_type),
      size: edgeSize(e.weight ?? 1),
      hidden: false,
      dimmed: false,
      highlighted: false,
      type: "line",
    });
  }

  return g;
}

export function edgeKey(a: string, b: string): string {
  return a < b ? `${a}||${b}` : `${b}||${a}`;
}

export function emptyAnnotation(): NodeAnnotation {
  return {
    contradiction_ids: [],
    distractor_ids: [],
    contradiction_count: 0,
    distractor_count: 0,
  };
}

function strHash(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

// ---- derived sets used by filter pane ---------------------------------

export function uniqueEntityTypes(raw: RawGraph): string[] {
  const set = new Set<string>();
  for (const n of raw.nodes) set.add(n.entity_type);
  return [...set].sort();
}

export function uniqueRelationTypes(raw: RawGraph): string[] {
  const set = new Set<string>();
  for (const e of raw.edges) set.add(e.relationship_type);
  return [...set].sort();
}
