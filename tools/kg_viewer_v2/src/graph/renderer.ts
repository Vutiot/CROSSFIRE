// Sigma renderer wrapper. Owns the Sigma instance + reducers that read
// per-node/edge runtime attrs (hidden/highlighted/dimmed/matched) so filter
// state propagates without graph rebuilds.
import Sigma from "sigma";
import Graph from "graphology";
import type { NodeAttrs, EdgeAttrs } from "./build";
import { HUB_DEGREE_THRESHOLD, colorForCommunity, colorForType } from "./build";

type G = Graph<NodeAttrs, EdgeAttrs>;

// Per spec — hover/selection fades non-adjacent down to 15% opacity.
const DIM_OPACITY = 0.15;
const HIGHLIGHT_INK = "#2c2c2a"; // outline + bold edge / node color when hovered/selected
const CANVAS_BG = "#fafaf7";

// Solid pre-blended edge tones. Sigma's WebGL programs render alpha-encoded
// hex unreliably against light backgrounds — the result blows toward white
// instead of producing a faded warm grey. We compute the desired blended
// tone ourselves and ship a solid color so the alpha pipeline never runs
// for edges. Slightly darker than a literal "#c8c5bb @ 0.7" blend because
// 0.8 px strokes lose contrast to anti-aliasing softening.
const EDGE_COLOR_DEFAULT = "#a8a59a"; // visible warm grey at any zoom
const EDGE_COLOR_DIMMED  = "#dfdcd1"; // selection-far / hover-far state

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

export function createRenderer(opts: RendererOpts): Sigma<NodeAttrs, EdgeAttrs> {
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
    // Solid pre-blended grey instead of an alpha-encoded form. Sigma's
    // WebGL edge program renders alpha-channel hex against a light
    // background as near-white due to its blend pipeline; the only
    // reliable fix is to bake the desired final tone into a solid color.
    defaultEdgeColor: EDGE_COLOR_DEFAULT,
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
      // Fade only on click-selection — hover stays still. Hovering large
      // graphs with a fade behaviour caused too much visual churn (and was
      // the trigger for the alpha-blend white-out artefact users reported).
      const dimmed = a.dimmed && !a.highlighted && !a.matched;
      const highlighted = a.highlighted || a.matched;
      const isHub = a.degree >= HUB_DEGREE_THRESHOLD;
      // Same alpha-pipeline gotcha as edges: Sigma's WebGL node program
      // renders alpha-channel hex against the light canvas as near-white,
      // which is exactly the "random whitening on hover" bug. preBlend
      // returns a solid pre-composited hex so the alpha path never runs.
      const finalColor = dimmed ? preBlend(color, DIM_OPACITY, CANVAS_BG) : color;
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
    edgeReducer: (_edgeId, data) => {
      const a = data as EdgeAttrs;
      if (a.hidden) return { ...data, hidden: true };

      // Click-selection fade only; hover doesn't dim anything.
      const dimmed = a.dimmed && !a.highlighted;
      const highlighted = a.highlighted;

      // All three edge-states use solid hex (no alpha) so Sigma's WebGL
      // pipeline doesn't blow them out toward white. Highlighted edges use
      // the spec ink, dimmed edges fade into the canvas, and the default
      // is a pre-blended warm grey matching the spec's intended tone.
      const color = highlighted
        ? HIGHLIGHT_INK
        : dimmed
          ? EDGE_COLOR_DIMMED
          : EDGE_COLOR_DEFAULT;
      // Keep the user-validated highlight thickness, otherwise spec width.
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

  // Hover — cursor feedback only. The graph stays visually still so the
  // user can read labels and node positions without flicker. Click is the
  // committed gesture that fades and surfaces the selection card.
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

// Composite `fg` over `bg` at `alpha`, returning a solid 6-digit hex. We use
// this instead of the obvious 8-digit-hex / rgba() forms because Sigma's
// WebGL programs (both node and edge) render alpha-channel inputs against
// light backgrounds in a way that overflows toward white — pre-blending
// produces the visually-intended result without ever feeding alpha into
// the shader.
function preBlend(fg: string, alpha: number, bg: string): string {
  const c = parseHex(fg);
  const b = parseHex(bg);
  const mix = (a: number, b: number) => Math.round(a * alpha + b * (1 - alpha));
  const h = (n: number) => Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${h(mix(c.r, b.r))}${h(mix(c.g, b.g))}${h(mix(c.b, b.b))}`;
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
