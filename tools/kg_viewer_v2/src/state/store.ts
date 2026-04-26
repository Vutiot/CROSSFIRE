import { signal, computed, effect } from "@preact/signals";
import type {
  ColorMode,
  DatasetPayload,
  FilterState,
  FocusState,
  LayoutKind,
  SelectionState,
  ViewKind,
} from "../types";

// ---- top-level signals -------------------------------------------------

export const datasetNames = signal<string[]>([]);
export const currentDataset = signal<string | null>(null);
export const payload = signal<DatasetPayload | null>(null);
export const loadError = signal<string | null>(null);
export const isLoading = signal<boolean>(false);

export const view = signal<ViewKind>("entities");
export const layoutKind = signal<LayoutKind>("forceatlas2");
export const colorMode = signal<ColorMode>("type");
export const search = signal<string>("");

export const filters = signal<FilterState>({
  entityTypes: {},
  relationTypes: {},
  showContradictions: false,
  showDistractors: false,
  scope: "all",
});

export const focus = signal<FocusState>({ active: false, nodeIds: [], history: [] });

export const selection = signal<SelectionState>({
  nodeId: null,
  edgeId: null,
  highlight: new Set(),
});

export const detailsOpen = signal<boolean>(false);
export const filterPaneOpen = signal<boolean>(true);
export const commandPaletteOpen = signal<boolean>(false);
export const helpOpen = signal<boolean>(false);

// Communities are computed on demand. Cached per-payload+view.
export const communities = signal<Map<string, number>>(new Map());

// Stats badge derived from current payload
export const stats = computed(() => payload.value?.stats ?? null);

// Currently active raw graph chosen by view
export const activeRawGraph = computed(() => {
  const p = payload.value;
  if (!p) return null;
  if (view.value === "documents") return p.graph;
  if (view.value === "claims") return p.claims_graph;
  return p.entity_graph;
});

export const activeAnnotations = computed(() => {
  const p = payload.value;
  if (!p) return {};
  if (view.value === "documents") return p.node_annotations;
  if (view.value === "claims") return p.claims_annotations;
  return p.entity_annotations;
});

// ---- selection helpers ------------------------------------------------
// All call sites (graph clicks, double-clicks, details-pane buttons, command
// palette, keyboard shortcuts) go through these so the state shape never
// gets reconstructed inline. Selecting a node clears any edge selection and
// vice versa — they're mutually exclusive.

export function selectNode(id: string, highlight: Set<string>) {
  selection.value = { nodeId: id, edgeId: null, highlight };
  detailsOpen.value = true;
}

export function selectEdge(id: string, highlight: Set<string>) {
  selection.value = { nodeId: null, edgeId: id, highlight };
  detailsOpen.value = true;
}

export function clearSelection() {
  selection.value = { nodeId: null, edgeId: null, highlight: new Set() };
  detailsOpen.value = false;
}

export function pushFocus(nodeIds: string[]) {
  const f = focus.value;
  focus.value = {
    active: true,
    nodeIds,
    history: [...f.history, f.nodeIds],
  };
}

export function popFocus() {
  const f = focus.value;
  if (!f.history.length) {
    focus.value = { active: false, nodeIds: [], history: [] };
    return;
  }
  const prev = f.history[f.history.length - 1];
  focus.value = {
    active: prev.length > 0,
    nodeIds: prev,
    history: f.history.slice(0, -1),
  };
}

export function clearFocus() {
  focus.value = { active: false, nodeIds: [], history: [] };
}

// View change clears view-specific filter pills (entity / relation types) and
// any focus subset — the vocabulary differs per view, so a leftover whitelist
// silently hides every node in the new view. Overlay flags + scope are kept
// since they are view-agnostic semantics.
export function setView(k: ViewKind) {
  if (view.value === k) return;
  view.value = k;
  filters.value = {
    ...filters.value,
    entityTypes: {},
    relationTypes: {},
  };
  clearFocus();
  clearSelection();
}

// Re-export for ergonomics
export { effect };
