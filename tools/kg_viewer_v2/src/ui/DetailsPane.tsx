import { useEffect, useMemo, useRef, useState } from "preact/hooks";
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
import type { Contradiction, Distractor, RawEdge, RawNode } from "../types";
import { showToast } from "./App";

const ROW_HEIGHT = 92; // px — used by virtual list

export function DetailsPane() {
  const sel = selection.value;
  const open = detailsOpen.value;
  if (!open || (!sel.nodeId && !sel.edgeId)) {
    return <aside class="right closed" />;
  }

  if (sel.edgeId) return <EdgeDetails edgeId={sel.edgeId} />;
  if (sel.nodeId) return <NodeDetails nodeId={sel.nodeId} />;
  return <aside class="right closed" />;
}

// ---- Node details -----------------------------------------------------

function NodeDetails({ nodeId }: { nodeId: string }) {
  const raw = activeRawGraph.value;
  const ann = activeAnnotations.value;
  const p = payload.value;
  if (!raw || !p) return <aside class="right" />;

  const node = useMemo(() => raw.nodes.find((n) => n.id === nodeId) ?? null, [raw, nodeId]);
  const a = ann[nodeId];

  const contradictions = useMemo(() => {
    if (!a) return [];
    const ids = new Set(a.contradiction_ids);
    return p.contradictions.filter((c) => ids.has(c.id));
  }, [a, p.contradictions]);

  const distractors = useMemo(() => {
    if (!a) return [];
    const ids = new Set(a.distractor_ids);
    return p.distractors.filter((d) => ids.has(d.id));
  }, [a, p.distractors]);

  if (!node) {
    return (
      <aside class="right">
        <div class="pane-inner">
          <p style={{ color: "var(--text-3)" }}>Node {nodeId} not found in current view.</p>
        </div>
      </aside>
    );
  }

  return (
    <aside class="right">
      <div class="pane-inner">
        <header class="pane-section">
          <h3 style={{ marginBottom: 6 }}>
            {node.entity_type}
            <span class="count">{node.claim_count ?? 0} claims</span>
          </h3>
          <h2 style={{ margin: "0 0 8px", fontSize: 17, lineHeight: 1.3 }}>
            {node.canonical_name}
          </h2>
          <code style={{ fontSize: 11, color: "var(--text-faint)" }}>{node.id}</code>
        </header>

        <NodeMeta node={node} />

        <div class="pane-section">
          <h3>Isolate</h3>
          <div style={{ display: "flex", gap: 4 }}>
            {[1, 2, 3].map((h) => (
              <button
                key={h}
                title={`Focus ${h}-hop neighborhood`}
                onClick={() => isolateHops(nodeId, h)}
                style={{ flex: 1 }}
              >
                {h}-hop
              </button>
            ))}
          </div>
        </div>

        {contradictions.length > 0 && (
          <ContradictionList contradictions={contradictions} />
        )}
        {distractors.length > 0 && <DistractorList distractors={distractors} />}
      </div>
    </aside>
  );
}

function NodeMeta({ node }: { node: RawNode }) {
  return (
    <div class="pane-section">
      <h3>Properties</h3>
      <dl class="kv">
        <dt>Type</dt><dd>{node.entity_type}</dd>
        {node.subject && (<><dt>Subject</dt><dd>{node.subject}</dd></>)}
        {node.predicate && (<><dt>Predicate</dt><dd>{node.predicate}</dd></>)}
        {node.object && (<><dt>Object</dt><dd>{node.object}</dd></>)}
        {node.source_document && (<><dt>Source</dt><dd>{node.source_document}</dd></>)}
        {node.confidence !== undefined && (<><dt>Confidence</dt><dd>{node.confidence.toFixed(2)}</dd></>)}
        {node.aliases && node.aliases.length > 0 && (
          <>
            <dt>Aliases</dt>
            <dd>{node.aliases.slice(0, 6).join(", ")}</dd>
          </>
        )}
        {node.subcorpus_memberships && node.subcorpus_memberships.length > 0 && (
          <>
            <dt>Documents</dt>
            <dd>{node.subcorpus_memberships.slice(0, 8).join(", ")}{node.subcorpus_memberships.length > 8 ? "…" : ""}</dd>
          </>
        )}
      </dl>
    </div>
  );
}

// ---- Edge details -----------------------------------------------------

function EdgeDetails({ edgeId }: { edgeId: string }) {
  const raw = activeRawGraph.value;
  if (!raw) return <aside class="right" />;
  const [a, b] = edgeId.split("||");
  const edge = useMemo(
    () =>
      raw.edges.find(
        (e) => (e.source === a && e.target === b) || (e.source === b && e.target === a),
      ) ?? null,
    [raw, a, b],
  );
  const sourceNode = raw.nodes.find((n) => n.id === a);
  const targetNode = raw.nodes.find((n) => n.id === b);

  if (!edge) {
    return (
      <aside class="right">
        <div class="pane-inner">
          <p style={{ color: "var(--text-3)" }}>Edge not found.</p>
        </div>
      </aside>
    );
  }

  return (
    <aside class="right">
      <div class="pane-inner">
        <div class="pane-section">
          <h3>Edge</h3>
          <h2 style={{ margin: 0, fontSize: 14 }}>
            {sourceNode?.canonical_name ?? a}
            <span style={{ color: "var(--text-3)", margin: "0 6px" }}>→</span>
            {targetNode?.canonical_name ?? b}
          </h2>
        </div>

        <EdgeMeta edge={edge} />

        <div class="pane-section">
          <h3>Isolate</h3>
          <div style={{ display: "flex", gap: 4 }}>
            {[1, 2, 3].map((h) => (
              <button
                key={h}
                title={`Focus to endpoints + their ${h}-hop neighborhoods`}
                onClick={() => isolateEdgeHops(edgeId, h)}
                style={{ flex: 1 }}
              >
                {h}-hop
              </button>
            ))}
          </div>
        </div>

        {edge.rationale && (
          <div class="pane-section">
            <h3>Rationale</h3>
            <p style={{ margin: 0, fontSize: 12.5, color: "var(--text-2)" }}>{edge.rationale}</p>
          </div>
        )}
      </div>
    </aside>
  );
}

function EdgeMeta({ edge }: { edge: RawEdge }) {
  return (
    <div class="pane-section">
      <dl class="kv">
        <dt>Type</dt><dd>{edge.relationship_type}</dd>
        {edge.weight !== undefined && (<><dt>Weight</dt><dd>{edge.weight}</dd></>)}
      </dl>
    </div>
  );
}

// ---- Lists with simple virtualization --------------------------------

function ContradictionList({ contradictions }: { contradictions: Contradiction[] }) {
  return (
    <div class="pane-section">
      <h3>
        Contradictions
        <span class="count">{contradictions.length}</span>
      </h3>
      <VirtualList
        items={contradictions}
        rowHeight={ROW_HEIGHT}
        render={(c) => (
          <div class="detail-card contradiction" key={c.id}>
            <h4>{c.mechanism ?? "contradiction"}</h4>
            <div class="meta">
              {c.scope && <span>{c.scope}</span>}
              {c.detectability && <span>{c.detectability}</span>}
              {c.difficulty && <span>{c.difficulty}</span>}
            </div>
            {c.original_text && (
              <div class="body">
                <strong style={{ color: "var(--ok)" }}>Original:</strong> {c.original_text}
              </div>
            )}
            {c.modified_text && (
              <div class="body">
                <strong style={{ color: "var(--danger)" }}>Modified:</strong> {c.modified_text}
              </div>
            )}
            <div style={{ marginTop: 8, display: "flex", gap: 4 }}>
              <button class="ghost" onClick={() => traceContradiction(c)}>
                Trace
              </button>
            </div>
          </div>
        )}
      />
    </div>
  );
}

function DistractorList({ distractors }: { distractors: Distractor[] }) {
  return (
    <div class="pane-section">
      <h3>
        Distractors
        <span class="count">{distractors.length}</span>
      </h3>
      <VirtualList
        items={distractors}
        rowHeight={ROW_HEIGHT}
        render={(d) => (
          <div class="detail-card distractor" key={d.id}>
            <h4>{d.id}</h4>
            {d.rationale && <div class="body">{d.rationale}</div>}
          </div>
        )}
      />
    </div>
  );
}

// ---- Virtual list ------------------------------------------------------
// Tiny windowed-list: renders only items inside the visible scroll window
// plus an overscan buffer. Negligible code, decent fluidity at 1k+ items.

function VirtualList<T>({
  items,
  rowHeight,
  render,
  overscan = 4,
}: {
  items: T[];
  rowHeight: number;
  render: (item: T, idx: number) => preact.JSX.Element;
  overscan?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [range, setRange] = useState<{ start: number; end: number }>({ start: 0, end: 12 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => {
      const top = el.scrollTop;
      const h = el.clientHeight;
      const start = Math.max(0, Math.floor(top / rowHeight) - overscan);
      const end = Math.min(items.length, Math.ceil((top + h) / rowHeight) + overscan);
      setRange((r) => (r.start === start && r.end === end ? r : { start, end }));
    };
    update();
    el.addEventListener("scroll", update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener("scroll", update);
      ro.disconnect();
    };
  }, [items.length, rowHeight, overscan]);

  // Only virtualize beyond a threshold; for small lists, render all (simpler markup).
  if (items.length <= 30) {
    return <div>{items.map((it, i) => render(it, i))}</div>;
  }

  const slice = items.slice(range.start, range.end);
  const totalH = items.length * rowHeight;
  const offset = range.start * rowHeight;

  return (
    <div ref={ref} class="virtual-list" style={{ maxHeight: 400 }}>
      <div class="virtual-list-spacer" style={{ height: totalH }}>
        <div class="virtual-list-window" style={{ transform: `translateY(${offset}px)` }}>
          {slice.map((it, i) => render(it, range.start + i))}
        </div>
      </div>
    </div>
  );
}

// ---- Actions ----------------------------------------------------------

function isolateHops(nodeId: string, hops: number) {
  // Defer to the graph-aware helper installed by GraphCanvas.
  const w = window as unknown as { __kgFocusNeighborhood?: (h: number) => void };
  if (selection.value.nodeId !== nodeId) {
    selectNode(nodeId, new Set([nodeId]));
  }
  w.__kgFocusNeighborhood?.(hops);
  showToast(`Isolated ${hops}-hop neighborhood`);
}

function isolateEdgeHops(edgeId: string, hops: number) {
  const w = window as unknown as { __kgFocusEdgeNeighborhood?: (h: number) => void };
  // Ensure selection points at this edge so the global helper picks it up.
  if (selection.value.edgeId !== edgeId) {
    selectEdge(edgeId, new Set());
  }
  w.__kgFocusEdgeNeighborhood?.(hops);
  showToast(`Isolated edge + ${hops}-hop endpoints`);
}

function traceContradiction(c: Contradiction) {
  // Find all nodes touched by this contradiction in the current view via annotations.
  const ann = activeAnnotations.value;
  const ids = Object.entries(ann)
    .filter(([, a]) => a.contradiction_ids.includes(c.id))
    .map(([id]) => id);
  if (!ids.length) {
    showToast("No nodes in current view link to this contradiction");
    return;
  }
  pushFocus(ids);
  // Trace replaces any prior selection with the affected node set.
  clearSelection();
  selection.value = { nodeId: null, edgeId: null, highlight: new Set(ids) };
  detailsOpen.value = true;
  showToast(`Traced contradiction ${c.id} (${ids.length} nodes)`);
}
