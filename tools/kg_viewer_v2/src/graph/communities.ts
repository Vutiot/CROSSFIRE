// Lazy Louvain community detection. Cached per-graph identity so repeated
// switches between color modes don't recompute.
import Graph from "graphology";
import louvain from "graphology-communities-louvain";
import type { NodeAttrs, EdgeAttrs } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;

const cache = new WeakMap<G, Map<string, number>>();

export function detectCommunities(graph: G): Map<string, number> {
  const cached = cache.get(graph);
  if (cached) return cached;
  // graphology-communities-louvain returns Record<nodeId, communityIdx>
  const detail = louvain(graph, { resolution: 1 }) as Record<string, number>;
  const m = new Map<string, number>();
  for (const [id, c] of Object.entries(detail)) m.set(id, c);
  cache.set(graph, m);
  return m;
}
