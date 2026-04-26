import { useMemo } from "preact/hooks";
import {
  activeRawGraph,
  filterPaneOpen,
  filters,
  payload,
  view,
} from "../state/store";
import type { TriState } from "../types";
import { uniqueEntityTypes, uniqueRelationTypes, colorForType, colorForRelation } from "../graph/build";

export function FilterPane() {
  if (!filterPaneOpen.value) return <aside class="left collapsed" />;
  const raw = activeRawGraph.value;
  const p = payload.value;
  const f = filters.value;

  const entityTypes = useMemo(() => raw ? uniqueEntityTypes(raw) : [], [raw]);
  const relationTypes = useMemo(() => raw ? uniqueRelationTypes(raw) : [], [raw]);

  function toggleEntityType(t: string) {
    const next = nextTri(f.entityTypes[t] ?? "off");
    filters.value = {
      ...f,
      entityTypes: { ...f.entityTypes, [t]: next },
    };
  }
  function toggleRelationType(t: string) {
    const next = nextTri(f.relationTypes[t] ?? "off");
    filters.value = {
      ...f,
      relationTypes: { ...f.relationTypes, [t]: next },
    };
  }
  function clearAll() {
    filters.value = {
      entityTypes: {},
      relationTypes: {},
      showContradictions: false,
      showDistractors: false,
      scope: "all",
    };
  }

  return (
    <aside class="left">
      <div class="pane-inner">
        <div class="pane-section">
          <h3>
            View
            <span class="count">{view.value}</span>
          </h3>
          <p style={{ color: "var(--text-3)", fontSize: 11.5, margin: 0 }}>
            {viewBlurb(view.value)}
          </p>
        </div>

        <div class="pane-section">
          <h3>
            Entity types
            <span class="count">{entityTypes.length}</span>
          </h3>
          <div class="pills">
            {entityTypes.map((t) => {
              const state = (f.entityTypes[t] ?? "off") as TriState;
              return (
                <span
                  key={t}
                  class={`pill-tri ${state}`}
                  style={{ "--c": colorForType(t) } as Record<string, string>}
                  onClick={() => toggleEntityType(t)}
                  title={triHint(state)}
                >
                  <span class="swatch" />
                  {t}
                </span>
              );
            })}
          </div>
        </div>

        <div class="pane-section">
          <h3>
            Relationship types
            <span class="count">{relationTypes.length}</span>
          </h3>
          <div class="pills">
            {relationTypes.map((t) => {
              const state = (f.relationTypes[t] ?? "off") as TriState;
              return (
                <span
                  key={t}
                  class={`pill-tri ${state}`}
                  style={{ "--c": colorForRelation(t) } as Record<string, string>}
                  onClick={() => toggleRelationType(t)}
                  title={triHint(state)}
                >
                  <span class="swatch" />
                  {t}
                </span>
              );
            })}
          </div>
        </div>

        <div class="pane-section">
          <h3>Overlays</h3>
          <div class="toggle-row">
            <span>Only contradictions</span>
            <button
              class="switch"
              data-on={f.showContradictions}
              onClick={() => (filters.value = { ...f, showContradictions: !f.showContradictions })}
              aria-pressed={f.showContradictions}
            />
          </div>
          <div class="toggle-row">
            <span>Only distractors</span>
            <button
              class="switch"
              data-on={f.showDistractors}
              onClick={() => (filters.value = { ...f, showDistractors: !f.showDistractors })}
              aria-pressed={f.showDistractors}
            />
          </div>
          <div class="toggle-row">
            <span>Scope</span>
            <select
              value={f.scope}
              onChange={(e) =>
                (filters.value = { ...f, scope: e.currentTarget.value as typeof f.scope })
              }
            >
              <option value="all">all</option>
              <option value="intra_doc">intra-doc</option>
              <option value="inter_doc">inter-doc</option>
            </select>
          </div>
        </div>

        <div class="pane-section">
          <button onClick={clearAll} style={{ width: "100%" }}>
            Clear all filters
          </button>
        </div>

        {p && (
          <div class="pane-section">
            <h3>Dataset</h3>
            <dl class="kv">
              <dt>Name</dt><dd>{p.dataset_name}</dd>
              <dt>Nodes</dt><dd>{p.stats.total_nodes.toLocaleString()}</dd>
              <dt>Edges</dt><dd>{p.stats.total_edges.toLocaleString()}</dd>
              {p.stats.total_claims !== undefined && (
                <>
                  <dt>Claims</dt><dd>{p.stats.total_claims.toLocaleString()}</dd>
                </>
              )}
              <dt>Contradictions</dt><dd>{p.stats.total_contradictions.toLocaleString()}</dd>
              <dt>Distractors</dt><dd>{p.stats.total_distractors.toLocaleString()}</dd>
            </dl>
          </div>
        )}
      </div>
    </aside>
  );
}

function nextTri(s: TriState): TriState {
  return s === "off" ? "include" : s === "include" ? "exclude" : "off";
}
function triHint(s: TriState) {
  return s === "off"
    ? "Click to include only this type"
    : s === "include"
    ? "Click to exclude this type"
    : "Click to remove filter";
}
function viewBlurb(v: string) {
  if (v === "documents") return "Documents linked by shared entities and shared facts.";
  if (v === "claims") return "Individual claims linked by cross-references and clusters.";
  return "Subjects with ≥3 claims, linked by cross-refs, clusters, and co-occurrence.";
}
