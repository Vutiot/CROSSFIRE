import type { DatasetPayload } from "./types";

const API_BASE = "/api";

export async function fetchDatasetNames(): Promise<string[]> {
  const r = await fetch(`${API_BASE}/datasets`);
  if (!r.ok) throw new Error(`/api/datasets returned ${r.status}`);
  return (await r.json()) as string[];
}

export async function fetchDataset(name: string): Promise<DatasetPayload> {
  const r = await fetch(`${API_BASE}/data/${encodeURIComponent(name)}`);
  if (!r.ok) throw new Error(`/api/data/${name} returned ${r.status}`);
  return (await r.json()) as DatasetPayload;
}

// Drag-drop fallback: parse a single payload JSON file (matching DatasetPayload
// shape, or a permissive subset).
export async function readDroppedPayload(file: File): Promise<DatasetPayload> {
  const text = await file.text();
  const obj = JSON.parse(text) as Partial<DatasetPayload>;
  // Be tolerant — fill in any missing fields with empty stand-ins.
  const p: DatasetPayload = {
    dataset_name: obj.dataset_name ?? file.name.replace(/\.json$/, ""),
    layout: obj.layout ?? "claims",
    graph: obj.graph ?? { nodes: [], edges: [] },
    entity_graph: obj.entity_graph ?? obj.graph ?? { nodes: [], edges: [] },
    entity_annotations: obj.entity_annotations ?? {},
    claims_graph: obj.claims_graph ?? { nodes: [], edges: [] },
    claims_annotations: obj.claims_annotations ?? {},
    contradictions: obj.contradictions ?? [],
    distractors: obj.distractors ?? [],
    claims: obj.claims ?? [],
    cross_references: obj.cross_references ?? [],
    claim_clusters: obj.claim_clusters ?? [],
    node_annotations: obj.node_annotations ?? {},
    stats: obj.stats ?? {
      total_nodes: 0,
      total_edges: 0,
      total_contradictions: 0,
      total_distractors: 0,
    },
  };
  return p;
}
