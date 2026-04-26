// Layout strategies: ForceAtlas2 (in worker, animated), circle, grid, hierarchy.
// Animated transitions interpolate from previous → target positions over a
// fixed window so layout switches feel fluid instead of teleporting.
import Graph from "graphology";
import circular from "graphology-layout/circular";
import { random } from "graphology-layout";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import type Sigma from "sigma";
import type { LayoutKind } from "../types";
import type { NodeAttrs, EdgeAttrs } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;
type S = Sigma<NodeAttrs, EdgeAttrs>;

// Active worker (cancelled when layout changes / unmount)
let activeWorker: { kill: () => void; stop: () => void } | null = null;

export function stopActiveLayout() {
  if (activeWorker) {
    try {
      activeWorker.kill();
    } catch {
      // ignore
    }
    activeWorker = null;
  }
}

export interface ApplyLayoutOpts {
  graph: G;
  kind: LayoutKind;
  sigma: S;
  animate?: boolean;
  onSettle?: () => void;
}

export async function applyLayout(opts: ApplyLayoutOpts): Promise<void> {
  stopActiveLayout();
  const { graph, kind, sigma, animate = true, onSettle } = opts;
  if (!graph.order) return;

  // Snapshot starting positions for animation
  const start = new Map<string, [number, number]>();
  graph.forEachNode((id, a) => start.set(id, [a.x, a.y]));

  switch (kind) {
    case "forceatlas2":
      return runForceAtlas2(graph, sigma, animate, start, onSettle);
    case "circle":
      circular.assign(graph, { scale: 1 });
      animateTo(graph, sigma, start, animate, onSettle);
      return;
    case "grid":
      gridLayout(graph);
      animateTo(graph, sigma, start, animate, onSettle);
      return;
    case "hierarchy":
      hierarchyLayout(graph);
      animateTo(graph, sigma, start, animate, onSettle);
      return;
  }
}

// ---- ForceAtlas2 in worker --------------------------------------------

function runForceAtlas2(
  graph: G,
  sigma: S,
  animate: boolean,
  start: Map<string, [number, number]>,
  onSettle?: () => void,
) {
  // If positions are too uniform (e.g., we just left grid layout), inject a
  // small jitter to break symmetry — FA2 is unstable on perfectly aligned
  // start states. We test by sampling first 10 nodes for x-variance.
  const sample = graph.nodes().slice(0, 10);
  if (sample.length > 1) {
    const xs = sample.map((id) => graph.getNodeAttribute(id, "x"));
    const variance = xs.reduce((s, x) => s + x * x, 0) / xs.length;
    if (variance < 0.001) {
      random.assign(graph, { scale: 1 });
    }
  }
  void start;

  const layout = new FA2Layout(graph, {
    settings: {
      gravity: 1,
      scalingRatio: 10,
      slowDown: 4,
      edgeWeightInfluence: 1,
      adjustSizes: true,
      barnesHutOptimize: graph.order > 500,
      barnesHutTheta: 0.5,
      linLogMode: false,
      outboundAttractionDistribution: false,
      strongGravityMode: true,
    },
  });
  activeWorker = layout;
  layout.start();
  // Auto-stop after a window proportional to graph size
  const ms = Math.min(8000, 1500 + graph.order * 4);
  setTimeout(() => {
    if (activeWorker === layout) {
      try {
        layout.stop();
      } catch {
        /* ignore */
      }
      activeWorker = null;
      sigma.refresh();
      onSettle?.();
    }
  }, ms);
  // Sigma will repaint as worker mutates the graph in-place.
  // Touch refresh once so the camera fit happens after first frame.
  requestAnimationFrame(() => sigma.refresh());
  void animate;
  return;
}

// ---- Static layouts ---------------------------------------------------

function gridLayout(graph: G) {
  const ids = graph.nodes();
  const n = ids.length;
  if (!n) return;
  const cols = Math.ceil(Math.sqrt(n));
  const step = 1 / Math.max(1, cols - 1);
  ids.sort();
  ids.forEach((id, i) => {
    const r = Math.floor(i / cols);
    const c = i % cols;
    graph.setNodeAttribute(id, "x", c * step - 0.5);
    graph.setNodeAttribute(id, "y", -(r * step - 0.5));
  });
}

function hierarchyLayout(graph: G) {
  // BFS from highest-degree node; place rank-by-rank in concentric rings.
  if (!graph.order) return;
  let root = graph.nodes()[0];
  let bestDeg = -1;
  graph.forEachNode((id) => {
    const d = graph.degree(id);
    if (d > bestDeg) {
      bestDeg = d;
      root = id;
    }
  });

  const depth = new Map<string, number>();
  depth.set(root, 0);
  const queue: string[] = [root];
  while (queue.length) {
    const id = queue.shift()!;
    const d = depth.get(id)!;
    graph.forEachNeighbor(id, (nb) => {
      if (!depth.has(nb)) {
        depth.set(nb, d + 1);
        queue.push(nb);
      }
    });
  }
  // Disconnected nodes — drop into outer ring
  let maxD = 0;
  depth.forEach((v) => (maxD = Math.max(maxD, v)));
  graph.forEachNode((id) => {
    if (!depth.has(id)) depth.set(id, maxD + 1);
  });
  maxD = Math.max(maxD, 1);

  const byDepth = new Map<number, string[]>();
  for (const [id, d] of depth) {
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d)!.push(id);
  }

  for (const [d, ids] of byDepth) {
    ids.sort();
    const r = d / (maxD + 0.5);
    const step = (Math.PI * 2) / Math.max(1, ids.length);
    ids.forEach((id, i) => {
      const a = i * step;
      graph.setNodeAttribute(id, "x", Math.cos(a) * r);
      graph.setNodeAttribute(id, "y", Math.sin(a) * r);
    });
  }
}

// ---- Animation --------------------------------------------------------

function animateTo(
  graph: G,
  sigma: S,
  start: Map<string, [number, number]>,
  animate: boolean,
  onSettle?: () => void,
) {
  if (!animate) {
    sigma.refresh();
    onSettle?.();
    return;
  }
  // Capture target after we've already set them, then animate from start.
  const end = new Map<string, [number, number]>();
  graph.forEachNode((id, a) => end.set(id, [a.x, a.y]));
  const DURATION = 600;
  const t0 = performance.now();

  function frame(now: number) {
    const t = Math.min(1, (now - t0) / DURATION);
    const e = easeOutCubic(t);
    graph.forEachNode((id) => {
      const s = start.get(id);
      const tgt = end.get(id);
      if (!s || !tgt) return;
      graph.setNodeAttribute(id, "x", s[0] + (tgt[0] - s[0]) * e);
      graph.setNodeAttribute(id, "y", s[1] + (tgt[1] - s[1]) * e);
    });
    sigma.refresh();
    if (t < 1) {
      requestAnimationFrame(frame);
    } else {
      onSettle?.();
    }
  }
  requestAnimationFrame(frame);
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}
