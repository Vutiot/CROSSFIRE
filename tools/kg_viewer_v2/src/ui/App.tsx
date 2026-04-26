import { useEffect, useRef } from "preact/hooks";
import { effect, signal } from "@preact/signals";
import {
  commandPaletteOpen,
  currentDataset,
  datasetNames,
  filterPaneOpen,
  filters,
  focus,
  helpOpen,
  isLoading,
  loadError,
  payload,
  selection,
} from "../state/store";
import { applyUrl, readUrl, startUrlSync } from "../state/url";
import { fetchDataset, fetchDatasetNames, readDroppedPayload } from "../api";
import { Topbar } from "./Topbar";
import { FilterPane } from "./FilterPane";
import { SelectionCard } from "./SelectionCard";
import { StatusBar } from "./StatusBar";
import { GraphCanvas } from "./GraphCanvas";
import { CommandPalette } from "./CommandPalette";
import { HelpDialog } from "./HelpDialog";
import { useGlobalKeys } from "./hooks/useGlobalKeys";

const dragOver = signal<boolean>(false);
const toast = signal<string | null>(null);

export function showToast(msg: string, ms = 2000) {
  toast.value = msg;
  window.setTimeout(() => {
    if (toast.value === msg) toast.value = null;
  }, ms);
}

export function App() {
  const mainRef = useRef<HTMLDivElement>(null);

  // Bootstrap: read URL, fetch dataset list, then react to dataset changes.
  useEffect(() => {
    applyUrl(readUrl());
    startUrlSync();

    void (async () => {
      try {
        const names = await fetchDatasetNames();
        datasetNames.value = names;
        if (!names.length) {
          loadError.value = "No datasets available. Drop a dataset JSON to begin.";
          return;
        }
        const fromUrl = currentDataset.value;
        const target = fromUrl && names.includes(fromUrl) ? fromUrl : names[0];
        // Setting currentDataset triggers the loader effect below.
        currentDataset.value = target;
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        loadError.value = `Failed to load dataset list: ${msg}. Drop a dataset JSON to begin.`;
      }
    })();

    // Loader: fetch payload whenever currentDataset changes (and isn't loaded).
    // Tracks the in-flight target so a fast double-pick doesn't race two
    // fetches; also installs a watchdog so a hung request can't strand the
    // spinner forever.
    let inflight: string | null = null;
    const dispose = effect(() => {
      const ds = currentDataset.value;
      if (!ds) return;
      const p = payload.value;
      if (p && p.dataset_name === ds) return; // already loaded
      if (inflight === ds) return; // already fetching this one
      inflight = ds;

      const watchdog = window.setTimeout(() => {
        if (inflight === ds && isLoading.value) {
          loadError.value = `Loading ${ds} timed out after 25s — check the server log and browser console.`;
          isLoading.value = false;
          inflight = null;
        }
      }, 25_000);

      void (async () => {
        try {
          isLoading.value = true;
          loadError.value = null;
          const next = await fetchDataset(ds);
          // Reset focus/selection/filters BEFORE swapping the payload so the
          // build effect (which fires synchronously on payload.value = ...)
          // doesn't apply stale, view-incompatible filter state to the new
          // graph and hide every node.
          focus.value = { active: false, nodeIds: [], history: [] };
          selection.value = { nodeId: null, edgeId: null, highlight: new Set() };
          filters.value = {
            entityTypes: {},
            relationTypes: {},
            showContradictions: false,
            showDistractors: false,
            scope: "all",
          };
          payload.value = next;
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e);
          // eslint-disable-next-line no-console
          console.error(`[kg-viewer] failed to load ${ds}:`, e);
          loadError.value = `Failed to load ${ds}: ${msg}`;
        } finally {
          window.clearTimeout(watchdog);
          if (inflight === ds) inflight = null;
          isLoading.value = false;
        }
      })();
    });
    return dispose;
  }, []);

  useGlobalKeys();

  // Drop handlers
  function onDragOver(e: DragEvent) {
    if (e.dataTransfer?.types.includes("Files")) {
      e.preventDefault();
      dragOver.value = true;
    }
  }
  function onDragLeave(e: DragEvent) {
    if (e.target === e.currentTarget) dragOver.value = false;
  }
  async function onDrop(e: DragEvent) {
    e.preventDefault();
    dragOver.value = false;
    const file = e.dataTransfer?.files[0];
    if (!file) return;
    try {
      const p = await readDroppedPayload(file);
      payload.value = p;
      currentDataset.value = p.dataset_name;
      showToast(`Loaded ${p.dataset_name}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      showToast(`Failed: ${msg}`, 4000);
    }
  }

  return (
    <div
      class="app"
      style={{
        // Two-column shell: filter pane on the left, canvas takes the rest.
        // Selection details overlay the canvas as a node-anchored card so
        // opening them never resizes the canvas (which is what made
        // single-click feel like the camera was moving).
        gridTemplateColumns: `${filterPaneOpen.value ? "var(--left-w)" : "0"} 1fr`,
      }}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <Topbar />
      <FilterPane />
      <div class="main" ref={mainRef}>
        <GraphCanvas />
        <SelectionCard />
        {dragOver.value && (
          <div class="dropzone">Drop dataset JSON to load</div>
        )}
        {!payload.value && !isLoading.value && (
          <div class="empty-state">
            <h2>{loadError.value ? "Couldn't load data" : "No dataset loaded"}</h2>
            <p>
              {loadError.value ||
                "Run python tools/kg_viewer/serve.py to expose datasets, then refresh — or drop a dataset JSON onto this window."}
            </p>
          </div>
        )}
        {isLoading.value && (
          <div class="empty-state">
            <div class="spinner" />
            <p>Loading {currentDataset.value ?? "dataset"}…</p>
          </div>
        )}
      </div>
      <StatusBar />
      {commandPaletteOpen.value && <CommandPalette />}
      {helpOpen.value && <HelpDialog />}
      {toast.value && <div class="toast fade-in">{toast.value}</div>}
    </div>
  );
}
