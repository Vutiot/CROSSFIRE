// Sigma renderer wrapper. Owns the Sigma instance + reducers that read
// per-node/edge runtime attrs (hidden/highlighted/dimmed/matched) so filter
// state propagates without graph rebuilds.
import Sigma from "sigma";
import Graph from "graphology";
import type { NodeAttrs, EdgeAttrs } from "./build";
import { HUB_DEGREE_THRESHOLD, colorForCommunity, colorForType } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;

// Per spec — hover/selection fades non-adjacent down to 15% opacity. Lower
// than the previous 0.18 so the focused subset really pops.
const DIM_OPACITY = 0.15;
const HIGHLIGHT_INK = "#2c2c2a"; // outline + bold edge color when hovered/selected

export interface RendererOpts {
  container: HTMLElement;
  graph: G;
  getColorMode: () => "type" | "community";
  getCommunities: () => Map<string, number>;
  onNodeClick: (id: string | null) => void;
  onEdgeClick: (id: string | null) => void;
  // Sigma fires click* immediately, then doubleClick* if a second click
  // lands inside the threshold. The single-click handler runs unconditionally
  // first (so selection is always current), then doubleClick adds intent on
  // top — typically a focus / drill-down.
  onNodeDoubleClick?: (id: string) => void;
  onEdgeDoubleClick?: (id: string) => void;
  onHover: (id: string | null) => void;
  onDragStart?: (nodeId: string) => void;
  onDragEnd?: (nodeId: string) => void;
}

// True when both endpoints of `edgeId` are in the hover set.
function hoverSetContainsEdge(graph: G, set: Set<string>, edgeId: string): boolean {
  if (!graph.hasEdge(edgeId)) return false;
  const [a, b] = graph.extremities(edgeId);
  return set.has(a) && set.has(b);
}

export function createRenderer(opts: RendererOpts): Sigma<NodeAttrs, EdgeAttrs> {
  // Hover-neighborhood set — populated on enterNode (the hovered node + its
  // 1-hop neighbors), cleared on leaveNode. Reducers below close over this
  // variable so the dim treatment redraws on the next Sigma refresh.
  let hoverSet: Set<string> | null = null;

  const sigma = new Sigma<NodeAttrs, EdgeAttrs>(opts.graph, opts.container, {
    renderLabels: true,
    renderEdgeLabels: false,
    // Spec calls for Inter at 12px, weight 400. Hubs (degree ≥ 10) bump to
    // 13/500 — handled per-node via forceLabel + the labelWeight reducer
    // hook below.
    labelSize: 12,
    labelWeight: "400",
    labelFont: '"Inter", system-ui, sans-serif',
    labelColor: { color: "#2c2c2a" },
    edgeLabelSize: 10,
    edgeLabelColor: { color: "#5f5e5a" },
    defaultNodeColor: "#9b9789",
    // Spec edge stroke #c8c5bb at 0.7 opacity, encoded as 8-digit hex
    // (B3 = round(0.7 * 255)). This form is parsed deterministically by
    // Sigma's edge program; the rgba() form was rendering near-white due
    // to a premultiplied-alpha quirk in Sigma's blend pipeline.
    defaultEdgeColor: "#c8c5bbb3",
    minCameraRatio: 0.05,
    maxCameraRatio: 8,
    labelDensity: 0.5,
    labelGridCellSize: 100,
    labelRenderedSizeThreshold: 6,
    // Sigma defaults edge events to off for performance. Without this, no
    // clickEdge / doubleClickEdge / enterEdge ever fires, so the edge
    // properties panel can't open.
    enableEdgeEvents: true,
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
      // Hover-fade: when something is hovered (and nothing is click-selected
      // taking precedence), nodes outside the hover neighborhood dim.
      const hoverFaded = !!hoverSet && !hoverSet.has(id);

      const dimmed = (a.dimmed && !a.highlighted && !a.matched) || hoverFaded;
      const highlighted = a.highlighted || a.matched;
      const isHub = a.degree >= HUB_DEGREE_THRESHOLD;
      const finalColor = dimmed ? withAlpha(color, DIM_OPACITY) : color;
      const size = highlighted ? a.size * 1.25 : a.size;
      return {
        ...data,
        color: finalColor,
        size,
        zIndex: highlighted ? 2 : dimmed ? 0 : 1,
        // Hub labels stay visible even at low zoom; matched (search hit)
        // labels also forced. Selected node label too, so the user always
        // sees what they clicked.
        forceLabel: a.matched || highlighted || isHub,
      };
    },
    edgeReducer: (edgeId, data) => {
      const a = data as EdgeAttrs;
      if (a.hidden) return { ...data, hidden: true };

      // For edges, "in the hover neighborhood" means both endpoints are in
      // the hover set. Edge attrs don't carry source/target, so we look up
      // via the graph reference passed in via opts.
      const dimByHover = hoverSet
        ? !hoverSetContainsEdge(opts.graph, hoverSet, edgeId)
        : false;
      const dimmed = (a.dimmed && !a.highlighted) || dimByHover;
      const highlighted = a.highlighted;

      // Spec: highlighted edges go to ink #2c2c2a at full opacity. Default
      // edges keep their per-relation color but at the 0.7 spec opacity.
      const color = highlighted
        ? HIGHLIGHT_INK
        : dimmed
          ? withAlpha(a.color, 0.06)
          : withAlpha(a.color, 0.7);
      const size = highlighted ? Math.max(1.4, a.size * 1.6) : a.size;
      return {
        ...data,
        color,
        size,
        zIndex: highlighted ? 2 : 0,
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

  // Double-click handlers — gesture shortcut for "isolate to N-hop" (the
  // legacy viewer's 1-hop button). preventSigmaDefault stops Sigma's built-in
  // 2× zoom-on-click for nodes/edges. Stage double-click is intentionally
  // NOT overridden — the default zoom-at-cursor stays.
  sigma.on("doubleClickNode", (payload) => {
    payload.preventSigmaDefault();
    if (dragMoved) return;
    opts.onNodeDoubleClick?.(payload.node);
  });
  sigma.on("doubleClickEdge", (payload) => {
    payload.preventSigmaDefault();
    if (dragMoved) return;
    opts.onEdgeDoubleClick?.(payload.edge);
  });

  // Hover — cursor feedback PLUS hover-neighborhood fade. The reducers
  // above read the hoverSet closure directly; we just refresh after each
  // change so the new state paints.
  sigma.on("enterNode", ({ node }) => {
    opts.container.style.cursor = draggedNode ? "grabbing" : "grab";
    const set = new Set<string>([node]);
    opts.graph.forEachNeighbor(node, (nb) => set.add(nb));
    hoverSet = set;
    sigma.refresh();
    opts.onHover(node);
  });
  sigma.on("leaveNode", () => {
    opts.container.style.cursor = "default";
    hoverSet = null;
    sigma.refresh();
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
  // Output 8-digit hex (#RRGGBBAA) instead of rgba(). Sigma's color parser
  // handles the hex form deterministically across both edge and node WebGL
  // programs; the rgba() form interacted poorly with Sigma's premultiplied-
  // alpha blend pipeline and was rendering near-white on light backgrounds
  // — exactly the user-reported "white edges" symptom.
  const c = parseHex(hex);
  const a = Math.max(0, Math.min(255, Math.round(alpha * 255)));
  const h = (n: number) => n.toString(16).padStart(2, "0");
  return `#${h(c.r)}${h(c.g)}${h(c.b)}${h(a)}`;
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
