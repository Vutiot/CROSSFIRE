import { focus, payload, search, selection, view } from "../state/store";
import { visibleCounts } from "./graphCounts";

export function StatusBar() {
  const p = payload.value;
  const sel = selection.value;
  const f = focus.value;
  const v = view.value;
  const counts = visibleCounts.value;

  return (
    <div class="statusbar">
      <span class="pill">{v}</span>
      {p && (
        <>
          <span>
            <strong style={{ color: "var(--text)" }}>{counts.nodes.toLocaleString()}</strong>
            {" / "}
            {p.stats.total_nodes.toLocaleString()} nodes
          </span>
          <span>
            <strong style={{ color: "var(--text)" }}>{counts.edges.toLocaleString()}</strong>
            {" / "}
            {p.stats.total_edges.toLocaleString()} edges
          </span>
          {search.value && (
            <span class="pill warn">{counts.matches} matches for "{search.value}"</span>
          )}
          {f.active && <span class="pill">focused: {f.nodeIds.length}</span>}
          {sel.nodeId && <span class="pill">{sel.nodeId}</span>}
        </>
      )}
      <span class="spacer" />
      <span><kbd>/</kbd> search</span>
      <span><kbd>⌘K</kbd> palette</span>
      <span><kbd>F</kbd> focus</span>
      <span><kbd>?</kbd> help</span>
    </div>
  );
}
