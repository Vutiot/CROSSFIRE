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
  degree: number; // computed in the post-edge pass; drives sizing + hub labels
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

// Tableau-20-derived palette per the design spec. Six categorical fills
// (officer/civilian/evidence/allegation/process/organization) are the
// primary anchors; the lightVariants extend the palette so the 12 generic
// entity-type buckets (person, equipment, mechanical, …) all map to a
// distinct, deliberately-chosen hue rather than something invented.
//
//   Spec category   | Fill      | LightVariant
//   officer         | #4e79a7   | #a0cbe8
//   civilian        | #f28e2b   | #ffbe7d
//   evidence        | #59a14f   | #8cd17d
//   allegation      | #e15759   | #ff9d9a
//   process         | #b07aa1   | #d4a6c8
//   organization    | #9c755f   | #d7b5a6
//
// The mapping below assigns each generic CROSSFIRE entity_type to the
// closest semantic match in that vocabulary so the same hue carries
// across datasets. COPA's actual subjects (Officer-1, Victim, etc.) ride
// on top of these buckets via their `entity_type` field at build time.
const TYPE_COLORS: Record<string, string> = {
  // people & roles → officer / civilian
  person: "#4e79a7",
  personnel: "#a0cbe8",
  officer: "#4e79a7",
  civilian: "#f28e2b",
  // organisations → organization brown
  organization: "#9c755f",
  location: "#d7b5a6",
  // physical evidence + equipment → evidence green
  equipment: "#59a14f",
  evidence: "#59a14f",
  mechanical: "#8cd17d",
  meteorological: "#8cd17d",
  // harms / causal / accusations → allegation red
  causal: "#e15759",
  allegation: "#e15759",
  numeric: "#ff9d9a",
  // procedural / regulatory → process purple
  procedural: "#b07aa1",
  regulation: "#d4a6c8",
  process: "#b07aa1",
  // temporal → secondary civilian orange
  temporal: "#ffbe7d",
  unknown: "#7a7466",
};

export function colorForType(t: string): string {
  return TYPE_COLORS[t] ?? "#8b949e";
}

export function colorForCommunity(c: number): string {
  // Tableau-20 alternating fill / lightVariant — picks read as a coherent
  // categorical scheme with sub-typing built in (each pair belongs to one
  // semantic family).
  const palette = [
    "#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#b07aa1", "#9c755f",
    "#a0cbe8", "#ffbe7d", "#8cd17d", "#ff9d9a", "#d4a6c8", "#d7b5a6",
    "#76b7b2", "#edc949", "#af7aa1", "#fabfd2",
  ];
  return palette[c % palette.length];
}

// Per design spec, edges in the graph itself use a single uniform stroke
// color so the node palette carries the categorical hierarchy on its own.
// The previous per-relation rainbow made the graph harder to scan because
// edge color competed with node color for attention. Relation type is
// still surfaced via the edge details card and the filter-pane swatches.
export const EDGE_STROKE = "#c8c5bb";

// Per-relation colors used ONLY for the FilterPane swatches so users can
// still visually distinguish relation kinds in the filter list. The actual
// rendered edges in the canvas always paint with EDGE_STROKE.
const REL_TYPE_COLORS: Record<string, string> = {
  shared_facts: "#59a14f",
  shared_entities: "#4e79a7",
  cross_reference: "#b07aa1",
  contradiction: "#e15759",
  distractor: "#b07aa1",
  temporal_proximity: "#f28e2b",
  causal_link: "#e15759",
  aircraft_context: "#59a14f",
  same_fact: "#4e79a7",
  causal: "#e15759",
};

export function colorForRelation(rel: string): string {
  return REL_TYPE_COLORS[rel] ?? "#9c9890";
}

// Per-spec node sizing: degree-based with sqrt scaling, 5–16px range.
// `sqrt` is the right scale for graph degree — it preserves visual
// distinction at low degrees (where the diff between 1 and 5 connections
// matters) without letting hubs balloon out of proportion. The actual
// degree → size pass runs after edges are added (see post-build loop in
// buildGraph).
const SIZE_MIN = 4;
const SIZE_MAX = 12;
const HUB_DEGREE = 10; // labels for nodes at or above this degree are forced visible

function sizeByDegree(deg: number, maxDeg: number): number {
  if (maxDeg <= 0) return SIZE_MIN;
  const t = Math.sqrt(Math.max(0, deg)) / Math.sqrt(maxDeg);
  return SIZE_MIN + t * (SIZE_MAX - SIZE_MIN);
}

function edgeSize(weight: number): number {
  return Math.max(0.5, Math.min(2.0, 0.5 + Math.log2((weight || 1) + 1) * 0.5));
}

export interface BuildOpts {
  raw: RawGraph;
  annotations: Record<string, NodeAnnotation>;
}

export function buildGraph({ raw, annotations }: BuildOpts): Graph<NodeAttrs, EdgeAttrs> {
  const g = new Graph<NodeAttrs, EdgeAttrs>({ multi: false, type: "undirected" });

  // Pass 1: add nodes with placeholder size (5px). Real sizes are assigned
  // after edges are added, in pass 3, since we size by degree per the
  // design spec.
  for (const n of raw.nodes) {
    const ann = annotations[n.id] ?? emptyAnnotation();
    const seed = strHash(n.id);
    const angle = (seed % 1000) / 1000 * Math.PI * 2;
    const r = 0.5 + ((seed >> 5) % 500) / 1000;
    g.addNode(n.id, {
      x: Math.cos(angle) * r,
      y: Math.sin(angle) * r,
      size: SIZE_MIN,
      color: colorForType(n.entity_type),
      label: n.canonical_name || n.id,
      raw: n,
      entityType: n.entity_type,
      contradictionCount: ann.contradiction_count,
      distractorCount: ann.distractor_count,
      degree: 0,
      hidden: false,
      highlighted: false,
      dimmed: false,
      matched: false,
    });
  }

  // Pass 2: add edges.
  for (const e of raw.edges) {
    if (!g.hasNode(e.source) || !g.hasNode(e.target)) continue;
    if (e.source === e.target) continue;
    const key = edgeKey(e.source, e.target);
    if (g.hasEdge(key)) continue;
    g.addEdgeWithKey(key, e.source, e.target, {
      raw: e,
      relationshipType: e.relationship_type,
      weight: e.weight ?? 1,
      color: EDGE_STROKE,
      size: edgeSize(e.weight ?? 1),
      hidden: false,
      dimmed: false,
      highlighted: false,
      type: "line",
    });
  }

  // Pass 3: degree-based sizing. We need to know the global maxDegree
  // before scaling, so this has to be a second sweep.
  let maxDeg = 0;
  g.forEachNode((id) => {
    const d = g.degree(id);
    if (d > maxDeg) maxDeg = d;
  });
  g.forEachNode((id, attrs) => {
    const d = g.degree(id);
    attrs.degree = d;
    attrs.size = sizeByDegree(d, maxDeg);
  });

  return g;
}

export const HUB_DEGREE_THRESHOLD = HUB_DEGREE;

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
