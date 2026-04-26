// Data contract returned by tools/kg_viewer/serve.py.
// Mirror of the Python build_payload() output. Keep this in sync.

export type ViewKind = "documents" | "entities" | "claims";

export interface RawNode {
  id: string;
  entity_type: string;
  canonical_name: string;
  aliases?: string[];
  subcorpus_memberships?: string[];
  claim_count?: number;
  category_breakdown?: Record<string, number>;
  // Claim-view specific
  confidence?: number;
  predicate?: string;
  object?: string;
  subject?: string;
  source_document?: string;
}

export interface RawEdge {
  source: string;
  target: string;
  relationship_type: string;
  weight?: number;
  rationale?: string;
}

export interface RawGraph {
  nodes: RawNode[];
  edges: RawEdge[];
}

export interface NodeAnnotation {
  contradiction_ids: string[];
  distractor_ids: string[];
  contradiction_count: number;
  distractor_count: number;
}

export interface Contradiction {
  id: string;
  document_references?: string[];
  scope?: string;
  mechanism?: string;
  detectability?: string;
  difficulty?: string;
  original_text?: string;
  modified_text?: string;
  rationale?: string;
  [k: string]: unknown;
}

export interface Distractor {
  id: string;
  document_references?: string[];
  rationale?: string;
  [k: string]: unknown;
}

export interface Claim {
  claim_id: string;
  subject: string;
  predicate: string;
  object: string;
  category?: string;
  source_document: string;
  confidence?: number;
}

export interface CrossReference {
  claim_ids?: string[];
  source_claim?: string;
  target_claim?: string;
  from_claim?: string;
  to_claim?: string;
  relationship_type?: string;
  relationship?: string;
  rationale?: string;
  description?: string;
}

export interface ClaimCluster {
  claim_ids: string[];
  relation?: string;
  theme?: string;
}

export interface DatasetStats {
  total_nodes: number;
  total_edges: number;
  total_claims?: number;
  total_cross_references?: number;
  total_claim_clusters?: number;
  total_contradictions: number;
  total_distractors: number;
}

export interface DatasetPayload {
  dataset_name: string;
  layout: string;
  graph: RawGraph;
  entity_graph: RawGraph;
  entity_annotations: Record<string, NodeAnnotation>;
  claims_graph: RawGraph;
  claims_annotations: Record<string, NodeAnnotation>;
  contradictions: Contradiction[];
  distractors: Distractor[];
  claims: Claim[];
  cross_references: CrossReference[];
  claim_clusters: ClaimCluster[];
  node_annotations: Record<string, NodeAnnotation>;
  stats: DatasetStats;
}

// ---- UI / runtime state types ----

export type TriState = "off" | "include" | "exclude";

export type LayoutKind = "forceatlas2" | "circle" | "grid" | "hierarchy";
export type ColorMode = "type" | "community";

export interface FilterState {
  entityTypes: Record<string, TriState>;
  relationTypes: Record<string, TriState>;
  showContradictions: boolean;
  showDistractors: boolean;
  scope: "all" | "intra_doc" | "inter_doc";
}

export interface FocusState {
  active: boolean;
  nodeIds: string[]; // visible subset
  history: string[][]; // stack for undo
}

export interface SelectionState {
  nodeId: string | null;
  edgeId: string | null; // graphology edge id (the same key build.ts assigns)
  highlight: Set<string>; // node ids to highlight
}
