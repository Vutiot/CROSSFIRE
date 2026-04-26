// Sigma renderer wrapper. Owns the Sigma instance + reducers that read
// per-node/edge runtime attrs (hidden/highlighted/dimmed/matched) so filter
// state propagates without graph rebuilds.
import Sigma from "sigma";
import Graph from "graphology";
import type { NodeAttrs, EdgeAttrs } from "./build";
import { colorForCommunity, colorForType } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;

const DIM_OPACITY = 0.18;

export interface RendererOpts {
  container: HTMLElement;
  graph: G;
  getColorMode: () => "type" | "community";
  getCommunities: () => Map<string, number>;
  onNodeClick: (id: string | null) => void;
  onEdgeClick: (id: string | null) => void;
  onHover: (id: string | null) => void;
  onDragStart?: (nodeId: string) => void;
  onDragEnd?: (nodeId: string) => void;
}

export function createRenderer(opts: RendererOpts): Sigma<NodeAttrs, EdgeAttrs> {
  const sigma = new Sigma<NodeAttrs, EdgeAttrs>(opts.graph, opts.container, {
    renderLabels: true,
    renderEdgeLabels: false,
    labelSize: 12,
    labelWeight: "500",
    labelFont: "Inter, system-ui, sans-serif",
    labelColor: { color: "#c9d1d9" },
    edgeLabelSize: 10,
    edgeLabelColor: { color: "#8b949e" },
    defaultNodeColor: "#8b949e",
    defaultEdgeColor: "#30363d",
    minCameraRatio: 0.05,
    maxCameraRatio: 8,
    labelDensity: 0.5,
    labelGridCellSize: 100,
    labelRenderedSizeThreshold: 6,
    nodeReducer: (id, data) => {
      const a = data as NodeAttrs;
      if (a.hidden) return { ...data, hidden: true };
      const colorMode = opts.getColorMode();
      let color = a.color;
      if (colorMode === "community") {
        const c = opts.getCommunities().get(id);
        color = c === undefined ? "#8b949e" : colorForCommunity(c);
      } else {
        color = colorForType(a.entityType);
      }
      const dimmed = a.dimmed && !a.highlighted && !a.matched;
      const highlighted = a.highlighted || a.matched;
      const finalColor = dimmed ? withAlpha(color, DIM_OPACITY) : color;
      // Subtle border for matched/highlighted via slight size bump
      const size = highlighted ? a.size * 1.35 : a.size;
      return {
        ...data,
        color: finalColor,
        size,
        zIndex: highlighted ? 2 : dimmed ? 0 : 1,
        forceLabel: a.matched, // always show search-match labels
      };
    },
    edgeReducer: (_id, data) => {
      const a = data as EdgeAttrs;
      if (a.hidden) return { ...data, hidden: true };
      const dimmed = a.dimmed && !a.highlighted;
      const color = dimmed ? withAlpha(a.color, 0.08) : a.highlighted ? brighten(a.color) : a.color;
      const size = a.highlighted ? a.size * 1.6 : a.size;
      return {
        ...data,
        color,
        size,
        zIndex: a.highlighted ? 2 : 0,
      };
    },
    allowInvalidContainer: true,
  });

  // Click handlers (suppressed when a drag actually moved the cursor)
  sigma.on("clickNode", ({ node }) => {
    if (dragMoved) return;
    opts.onNodeClick(node);
  });
  sigma.on("clickEdge", ({ edge }) => {
    if (dragMoved) return;
    opts.onEdgeClick(edge);
  });
  sigma.on("clickStage", () => {
    if (dragMoved) return;
    opts.onNodeClick(null);
    opts.onEdgeClick(null);
  });

  // Hover (cursor feedback)
  sigma.on("enterNode", ({ node }) => {
    opts.container.style.cursor = draggedNode ? "grabbing" : "grab";
    opts.onHover(node);
  });
  sigma.on("leaveNode", () => {
    opts.container.style.cursor = "default";
    opts.onHover(null);
  });

  // ---- node dragging --------------------------------------------------
  // Press on a node → that node becomes draggable; mouse-move while held
  // updates its x/y in graph-space; release ends the drag. preventSigmaDefault
  // suppresses the camera pan that would otherwise eat the gesture.
  let draggedNode: string | null = null;
  let dragMoved = false;

  sigma.on("downNode", ({ node }) => {
    draggedNode = node;
    dragMoved = false;
    // Freeze normalization so dragging in graph-space doesn't cause the
    // bbox to drift each frame.
    if (!sigma.getCustomBBox()) sigma.setCustomBBox(sigma.getBBox());
    opts.onDragStart?.(node);
  });

  const mouse = sigma.getMouseCaptor();
  mouse.on("mousemovebody", (e) => {
    if (!draggedNode) return;
    const pos = sigma.viewportToGraph(e);
    opts.graph.setNodeAttribute(draggedNode, "x", pos.x);
    opts.graph.setNodeAttribute(draggedNode, "y", pos.y);
    dragMoved = true;
    e.preventSigmaDefault();
    e.original.preventDefault();
    e.original.stopPropagation();
  });
  mouse.on("mouseup", () => {
    if (draggedNode) opts.onDragEnd?.(draggedNode);
    draggedNode = null;
    // Reset dragMoved on next tick so the synthesized clickNode (which fires
    // after mouseup) can be filtered out, but a fresh click still works.
    setTimeout(() => {
      dragMoved = false;
    }, 0);
  });
  mouse.on("mousedown", () => {
    // If the user starts a stage-pan, ensure no stale drag state remains.
    if (!draggedNode && !sigma.getCustomBBox()) {
      sigma.setCustomBBox(sigma.getBBox());
    }
  });

  return sigma;
}

function withAlpha(hex: string, alpha: number): string {
  const c = parseHex(hex);
  return `rgba(${c.r},${c.g},${c.b},${alpha})`;
}

function brighten(hex: string): string {
  const c = parseHex(hex);
  const f = (x: number) => Math.min(255, Math.round(x + (255 - x) * 0.35));
  return `rgb(${f(c.r)},${f(c.g)},${f(c.b)})`;
}

function parseHex(hex: string): { r: number; g: number; b: number } {
  if (hex.startsWith("rgb")) {
    const m = hex.match(/\d+/g);
    if (m && m.length >= 3) return { r: +m[0], g: +m[1], b: +m[2] };
    return { r: 139, g: 148, b: 158 };
  }
  let h = hex.replace("#", "");
  if (h.length === 3) h = h.split("").map((c) => c + c).join("");
  const n = parseInt(h, 16);
  return { r: (n >> 16) & 0xff, g: (n >> 8) & 0xff, b: n & 0xff };
}

// Smoothly fit the camera to a set of nodes. Uses sigma.getNodeDisplayData()
// which returns each node's position in the [0, 1] normalized camera space —
// camera.animate() expects coords in that same space.
export function fitToNodes(sigma: Sigma<NodeAttrs, EdgeAttrs>, nodeIds: string[], padding: number = 0.15) {
  if (!nodeIds.length) {
    sigma.getCamera().animatedReset({ duration: 400 });
    return;
  }
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  let count = 0;
  for (const id of nodeIds) {
    const p = sigma.getNodeDisplayData(id);
    if (!p) continue;
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
    count++;
  }
  if (!count || !isFinite(minX)) {
    sigma.getCamera().animatedReset({ duration: 400 });
    return;
  }
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  // Camera ratio ~ "fraction of normalized [0..1] extent the viewport shows"
  // — at ratio 1 we see the whole graph; smaller ratio = zoomed in.
  const span = Math.max(spanX, spanY, 0.05);
  const ratio = span * (1 + padding);
  sigma.getCamera().animate(
    { x: cx, y: cy, ratio: Math.max(0.05, Math.min(2, ratio)) },
    { duration: 500, easing: "quadraticInOut" },
  );
}
