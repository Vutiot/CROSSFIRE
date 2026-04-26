// URL-hash persistence: serialize a stable subset of UI state into the
// fragment so deep-links survive reload and copy-share. Schema is versioned
// (v=2) so older v1 hashes from kg_viewer (legacy) are ignored cleanly.
import { effect } from "@preact/signals";
import {
  colorMode,
  currentDataset,
  filters,
  focus,
  layoutKind,
  search,
  selection,
  view,
} from "./store";
import type { FilterState, LayoutKind, ColorMode, ViewKind, TriState } from "../types";

const VERSION = "2";

interface SerializedState {
  v: string;
  ds?: string;
  view?: ViewKind;
  layout?: LayoutKind;
  color?: ColorMode;
  q?: string;
  et?: Record<string, TriState>;
  rt?: Record<string, TriState>;
  ovc?: 1 | 0;
  ovd?: 1 | 0;
  scope?: FilterState["scope"];
  focus?: string[];
  sel?: string;
}

function encode(obj: SerializedState): string {
  const json = JSON.stringify(obj);
  // base64url for URL safety
  const b64 = btoa(unescape(encodeURIComponent(json)));
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decode(hash: string): SerializedState | null {
  if (!hash) return null;
  try {
    const b64 = hash.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "===".slice((b64.length + 3) % 4);
    const json = decodeURIComponent(escape(atob(padded)));
    const obj = JSON.parse(json) as SerializedState;
    if (obj.v !== VERSION) return null;
    return obj;
  } catch {
    return null;
  }
}

let suppressWrite = false;

export function readUrl(): SerializedState | null {
  const hash = location.hash.replace(/^#/, "");
  return decode(hash);
}

export function applyUrl(state: SerializedState | null) {
  if (!state) return;
  suppressWrite = true;
  if (state.ds !== undefined) currentDataset.value = state.ds;
  if (state.view) view.value = state.view;
  if (state.layout) layoutKind.value = state.layout;
  if (state.color) colorMode.value = state.color;
  if (state.q !== undefined) search.value = state.q;
  filters.value = {
    entityTypes: state.et ?? {},
    relationTypes: state.rt ?? {},
    showContradictions: state.ovc === 1,
    showDistractors: state.ovd === 1,
    scope: state.scope ?? "all",
  };
  focus.value = state.focus?.length
    ? { active: true, nodeIds: state.focus, history: [] }
    : { active: false, nodeIds: [], history: [] };
  if (state.sel) {
    selection.value = { nodeId: state.sel, edgeKey: null, highlight: new Set() };
  }
  // Allow writes again on next tick
  queueMicrotask(() => {
    suppressWrite = false;
  });
}

export function startUrlSync() {
  effect(() => {
    // Touch all signals we want to persist.
    const ds = currentDataset.value;
    const v = view.value;
    const lay = layoutKind.value;
    const col = colorMode.value;
    const q = search.value;
    const f = filters.value;
    const fc = focus.value;
    const sel = selection.value;

    if (suppressWrite) return;

    const out: SerializedState = { v: VERSION };
    if (ds) out.ds = ds;
    out.view = v;
    out.layout = lay;
    out.color = col;
    if (q) out.q = q;
    const et = filterEntries(f.entityTypes);
    const rt = filterEntries(f.relationTypes);
    if (Object.keys(et).length) out.et = et;
    if (Object.keys(rt).length) out.rt = rt;
    if (f.showContradictions) out.ovc = 1;
    if (f.showDistractors) out.ovd = 1;
    if (f.scope !== "all") out.scope = f.scope;
    if (fc.active && fc.nodeIds.length) out.focus = fc.nodeIds;
    if (sel.nodeId) out.sel = sel.nodeId;

    const next = "#" + encode(out);
    if (next !== location.hash) {
      // replaceState avoids back-button spam on every signal change.
      history.replaceState(null, "", next);
    }
  });
}

function filterEntries(rec: Record<string, TriState>): Record<string, TriState> {
  const out: Record<string, TriState> = {};
  for (const [k, v] of Object.entries(rec)) {
    if (v !== "off") out[k] = v;
  }
  return out;
}
