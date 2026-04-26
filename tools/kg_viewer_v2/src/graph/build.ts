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

// 12-color palette mirroring the legacy viewer for visual continuity
const TYPE_COLORS: Record<string, string> = {
  person: "#58a6ff",
  organization: "#bc8cff",
  equipment: "#7ee787",
  regulation: "#ffa657",
  location: "#79c0ff",
  temporal: "#d4a855",
  mechanical: "#ff7b72",
  causal: "#f47067",
  procedural: "#56d4dd",
  meteorological: "#a5d6ff",
  numeric: "#e3b341",
  personnel: "#ffa198",
  unknown: "#8b949e",
};

export function colorForType(t: string): string {
  return TYPE_COLORS[t] ?? "#8b949e";
}

export function colorForCommunity(c: number): string {
  // Categorical palette derived from D3 Tableau10 + Set3 — readable on dark bg
  const palette = [
    "#58a6ff", "#7ee787", "#d4a855", "#bc8cff", "#ff7b72",
    "#56d4dd", "#ffa657", "#a5d6ff", "#e3b341", "#ffa198",
    "#79c0ff", "#f47067", "#3fb950", "#db61a2", "#a371f7",
  ];
  return palette[c % palette.length];
}

const REL_TYPE_DEFAULT = "#30363d";
const REL_TYPE_COLORS: Record<string, string> = {
  shared_facts: "#3fb950",
  shared_entities: "#58a6ff",
  cross_reference: "#bc8cff",
  contradiction: "#f47067",
  distractor: "#a371f7",
  temporal_proximity: "#d4a855",
  causal_link: "#ff7b72",
  aircraft_context: "#7ee787",
};

export function colorForRelation(rel: string): string {
  return REL_TYPE_COLORS[rel] ?? REL_TYPE_DEFAULT;
}

const SIZE_MIN = 4;
const SIZE_MAX = 22;

function nodeSize(claimCount: number, contradictionCount: number, maxClaims: number): number {
  // Log-scaled by claim count, plus small bump per contradiction.
  const base = Math.log2((claimCount || 1) + 1) / Math.log2(maxClaims + 1);
  const sized = SIZE_MIN + base * (SIZE_MAX - SIZE_MIN);
  return sized + Math.min(contradictionCount, 6) * 0.5;
}

function edgeSize(weight: number): number {
  return Math.max(0.5, Math.min(6, Math.log2((weight || 1) + 1)));
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
