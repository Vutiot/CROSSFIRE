// Floating, node-anchored properties card. Replaces the right sidebar so
// opening details never resizes the canvas — that resize was what made
// single-click feel like the camera was moving. The card position tracks
// the selected node (or edge midpoint) on every Sigma render so it stays
// glued to its anchor through pan, zoom, drag, and layout animation.
import { useEffect, useMemo, useState } from "preact/hooks";
import {
  activeAnnotations,
  activeRawGraph,
  clearSelection,
  detailsOpen,
  payload,
  pushFocus,
  selectEdge,
  selectNode,
  selection,
} from "../state/store";
import type { Contradiction, Distractor, RawNode } from "../types";
import { showToast } from "./App";

const CARD_WIDTH = 320;
const CARD_OFFSET = 22; // px gap between node and card edge

interface ScreenPos {
  x: number;
  y: number;
  flipped: boolean; // true when card is positioned to the LEFT of the node
}

function clampPos(pos: { x: number; y: number }, viewportW: number, viewportH: number): ScreenPos {
  // Default: card to the right of the node.
  let cx = pos.x + CARD_OFFSET;
  let flipped = false;
  // Flip to the left if it would overflow the right edge.
  if (cx + CARD_WIDTH > viewportW - 8) {
    cx = pos.x - CARD_OFFSET - CARD_WIDTH;
    flipped = true;
  }
  // Vertical: keep within viewport with 12px margins.
  const cy = Math.max(12, Math.min(viewportH - 12, pos.y));
  return { x: cx, y: cy, flipped };
}

export function SelectionCard() {
  const sel = selection.value;
  const open = detailsOpen.value;
  const [pos, setPos] = useState<ScreenPos | null>(null);
  // Re-track on every Sigma render so pan/zoom/layout keeps the card glued
  // to the anchor. Sigma instance + helpers are exposed via the global
  // hooks installed in GraphCanvas.
  useEffect(() => {
    if (!open || (!sel.nodeId && !sel.edgeId)) {
      setPos(null);
      return;
    }
    type W = {
      __kgGetNodeViewport?: (id: string) => { x: number; y: number } | null;
      __kgGetEdgeViewport?: (id: string) => { x: number; y: number } | null;
      __kgOnRender?: (cb: () => void) => () => void;
      __kgViewportSize?: () => { w: number; h: number };
    };
    const w = window as unknown as W;
    const update = () => {
      let p: { x: number; y: number } | null = null;
      if (sel.nodeId) p = w.__kgGetNodeViewport?.(sel.nodeId) ?? null;
      else if (sel.edgeId) p = w.__kgGetEdgeViewport?.(sel.edgeId) ?? null;
      if (!p) {
        setPos(null);
        return;
      }
      const size = w.__kgViewportSize?.() ?? { w: window.innerWidth, h: window.innerHeight };
      setPos(clampPos(p, size.w, size.h));
    };
    update();
    const off = w.__kgOnRender?.(update);
    return () => off?.();
  }, [open, sel.nodeId, sel.edgeId]);

  if (!open) return null;
  if (!sel.nodeId && !sel.edgeId) return null;
  if (!pos) return null;

  return (
    <div
      class={`node-card ${pos.flipped ? "flip" : ""}`}
      style={{ left: `${pos.x}px`, top: `${pos.y}px`, transform: "translateY(-50%)" }}
      // Stop propagation so clicks inside the card don't hit clickStage and
      // clear the selection.
      onClick={(e) => e.stopPropagation()}
      onMouseDown={(e) => e.stopPropagation()}
    >
      <div class="leader" />
      {sel.nodeId ? <NodeCardBody nodeId={sel.nodeId} /> : <EdgeCardBody edgeId={sel.edgeId!} />}
    </div>
  );
}

// ---- Node body --------------------------------------------------------

function NodeCardBody({ nodeId }: { nodeId: string }) {
  const raw = activeRawGraph.value;
  const ann = activeAnnotations.value;
  const p = payload.value;

  const node = useMemo(
    () => (raw ? raw.nodes.find((n) => n.id === nodeId) ?? null : null),
    [raw, nodeId],
  );
  const a = ann[nodeId];

  const contradictions = useMemo(() => {
    if (!a || !p) return [];
    const ids = new Set(a.contradiction_ids);
    return p.contradictions.filter((c) => ids.has(c.id));
  }, [a, p?.contradictions]);

  const distractors = useMemo(() => {
    if (!a || !p) return [];
    const ids = new Set(a.distractor_ids);
    return p.distractors.filter((d) => ids.has(d.id));
  }, [a, p?.distractors]);

  if (!node) {
    return (
      <>
        <div class="card-head">
          <button class="close" onClick={clearSelection} title="Close">×</button>
          <div class="type-tag">missing</div>
          <h2>Node not found in current view</h2>
          <div class="id">{nodeId}</div>
        </div>
      </>
    );
  }

  return (
    <>
      <div class="card-head">
        <button class="close" onClick={clearSelection} title="Close (Esc)">×</button>
        <div class="type-tag">{node.entity_type}</div>
        <h2>{node.canonical_name}</h2>
        <div class="id">{node.id}</div>
        <div class="card-badges">
          {node.claim_count !== undefined && (
            <span class="badge claims">{node.claim_count} claims</span>
          )}
          {a?.contradiction_count > 0 && (
            <span class="badge contra">{a.contradiction_count} contradiction{a.contradiction_count > 1 ? "s" : ""}</span>
          )}
          {a?.distractor_count > 0 && (
            <span class="badge distractor">{a.distractor_count} distractor{a.distractor_count > 1 ? "s" : ""}</span>
          )}
        </div>
      </div>
      <div class="card-body">
        <NodeProps node={node} />
        <div class="group">
          <div class="group-title">Isolate neighborhood</div>
          <div class="iso-row">
            {[1, 2, 3].map((h) => (
              <button
                key={h}
                onClick={() => isolateNodeHops(nodeId, h)}
                title={`Focus to ${h}-hop`}
              >
                {h}-hop
              </button>
            ))}
          </div>
        </div>
        {contradictions.length > 0 && (
          <div class="group">
            <div class="group-title">Contradictions ({contradictions.length})</div>
            {contradictions.slice(0, 12).map((c) => <ContradictionCard key={c.id} c={c} />)}
            {contradictions.length > 12 && (
              <div style={{ fontSize: 11, color: "var(--text-faint)" }}>
                + {contradictions.length - 12} more
              </div>
            )}
          </div>
        )}
        {distractors.length > 0 && (
          <div class="group">
            <div class="group-title">Distractors ({distractors.length})</div>
            {distractors.slice(0, 8).map((d) => <DistractorCard key={d.id} d={d} />)}
          </div>
        )}
      </div>
    </>
  );
}

function NodeProps({ node }: { node: RawNode }) {
  const showAliases = node.aliases && node.aliases.length > 0;
  const showDocs = node.subcorpus_memberships && node.subcorpus_memberships.length > 0;
  return (
    <div class="group">
      <div class="group-title">Properties</div>
      <dl class="kv">
        <dt>Type</dt><dd>{node.entity_type}</dd>
        {node.subject && (<><dt>Subject</dt><dd>{node.subject}</dd></>)}
        {node.predicate && (<><dt>Predicate</dt><dd><code style={{ fontFamily: "var(--mono)", fontSize: 11 }}>{node.predicate}</code></dd></>)}
        {node.object && (<><dt>Object</dt><dd>{node.object}</dd></>)}
        {node.source_document && (<><dt>Source</dt><dd>{node.source_document}</dd></>)}
        {node.confidence !== undefined && (<><dt>Confidence</dt><dd>{node.confidence.toFixed(2)}</dd></>)}
        {showAliases && (<><dt>Aliases</dt><dd>{node.aliases!.slice(0, 5).join(", ")}{node.aliases!.length > 5 ? ", …" : ""}</dd></>)}
        {showDocs && (<><dt>Docs</dt><dd>{node.subcorpus_memberships!.slice(0, 4).join(", ")}{node.subcorpus_memberships!.length > 4 ? ", …" : ""}</dd></>)}
      </dl>
    </div>
  );
}

// ---- Edge body --------------------------------------------------------

function EdgeCardBody({ edgeId }: { edgeId: string }) {
  const raw = activeRawGraph.value;
  if (!raw) return null;
  const [sId, tId] = edgeId.split("||");
  const edge = useMemo(
    () =>
      raw.edges.find(
        (e) => (e.source === sId && e.target === tId) || (e.source === tId && e.target === sId),
      ) ?? null,
    [raw, sId, tId],
  );
  const sourceNode = raw.nodes.find((n) => n.id === sId);
  const targetNode = raw.nodes.find((n) => n.id === tId);

  if (!edge) {
    return (
      <>
        <div class="card-head">
          <button class="close" onClick={clearSelection} title="Close">×</button>
          <h2>Edge not found</h2>
          <div class="id">{edgeId}</div>
        </div>
      </>
    );
  }

  return (
    <>
      <div class="card-head">
        <button class="close" onClick={clearSelection} title="Close (Esc)">×</button>
        <div class="type-tag">{edge.relationship_type}</div>
        <h2>
          <span style={{ color: "var(--text-2)" }}>{sourceNode?.canonical_name ?? sId}</span>
          <span style={{ color: "var(--text-faint)", margin: "0 6px", fontFamily: "var(--font)", fontWeight: 400 }}>—</span>
          <span style={{ color: "var(--text-2)" }}>{targetNode?.canonical_name ?? tId}</span>
        </h2>
        {edge.weight !== undefined && (
          <div class="card-badges">
            <span class="badge claims">weight {edge.weight}</span>
          </div>
        )}
      </div>
      <div class="card-body">
        <div class="group">
          <div class="group-title">Endpoints</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <button
              style={{ textAlign: "left", justifyContent: "flex-start" }}
              onClick={() => sourceNode && selectNode(sourceNode.id, new Set([sourceNode.id]))}
              title="Jump to source node"
            >
              ← {sourceNode?.canonical_name ?? sId}
            </button>
            <button
              style={{ textAlign: "left", justifyContent: "flex-start" }}
              onClick={() => targetNode && selectNode(targetNode.id, new Set([targetNode.id]))}
              title="Jump to target node"
            >
              → {targetNode?.canonical_name ?? tId}
            </button>
          </div>
        </div>
        {edge.rationale && (
          <div class="group">
            <div class="group-title">Rationale</div>
            <p style={{ margin: 0, fontSize: 12, lineHeight: 1.5, color: "var(--text-2)", fontStyle: "italic" }}>
              {edge.rationale}
            </p>
          </div>
        )}
        <div class="group">
          <div class="group-title">Isolate</div>
          <div class="iso-row">
            {[1, 2, 3].map((h) => (
              <button
                key={h}
                onClick={() => isolateEdgeHops(edgeId, h)}
                title={`Focus to endpoints + ${h}-hop neighborhoods`}
              >
                {h}-hop
              </button>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

// ---- Inline cards used inside the body --------------------------------

function ContradictionCard({ c }: { c: Contradiction }) {
  return (
    <div class="detail-card contradiction">
      <h4>{c.mechanism ?? "contradiction"}</h4>
      <div class="meta">
        {c.scope && <span>{c.scope}</span>}
        {c.detectability && <span>{c.detectability}</span>}
        {c.difficulty && <span>{c.difficulty}</span>}
      </div>
      {c.original_text && (
        <div class="body">
          <strong style={{ color: "var(--ok)", fontWeight: 600 }}>was:</strong> {c.original_text}
        </div>
      )}
      {c.modified_text && (
        <div class="body">
          <strong style={{ color: "var(--danger)", fontWeight: 600 }}>now:</strong> {c.modified_text}
        </div>
      )}
      <div style={{ marginTop: 6 }}>
        <button class="ghost" onClick={() => traceContradiction(c)} style={{ fontSize: 11, padding: "2px 8px" }}>
          Trace affected nodes
        </button>
      </div>
    </div>
  );
}

function DistractorCard({ d }: { d: Distractor }) {
  return (
    <div class="detail-card distractor">
      <h4>{d.id}</h4>
      {d.rationale && <div class="body">{d.rationale}</div>}
    </div>
  );
}

// ---- Actions ----------------------------------------------------------

function isolateNodeHops(nodeId: string, hops: number) {
  const w = window as unknown as { __kgFocusNeighborhood?: (h: number) => void };
  if (selection.value.nodeId !== nodeId) {
    selectNode(nodeId, new Set([nodeId]));
  }
  w.__kgFocusNeighborhood?.(hops);
  showToast(`Isolated ${hops}-hop`);
}

function isolateEdgeHops(edgeId: string, hops: number) {
  const w = window as unknown as { __kgFocusEdgeNeighborhood?: (h: number) => void };
  if (selection.value.edgeId !== edgeId) {
    selectEdge(edgeId, new Set());
  }
  w.__kgFocusEdgeNeighborhood?.(hops);
  showToast(`Isolated edge + ${hops}-hop`);
}

function traceContradiction(c: Contradiction) {
  const ann = activeAnnotations.value;
  const ids = Object.entries(ann)
    .filter(([, v]) => v.contradiction_ids.includes(c.id))
    .map(([id]) => id);
  if (!ids.length) {
    showToast("No nodes in current view link to this contradiction");
    return;
  }
  pushFocus(ids);
  showToast(`Traced ${c.id} (${ids.length} nodes)`);
}
