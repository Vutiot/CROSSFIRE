import { useEffect, useRef } from "preact/hooks";
import {
  colorMode,
  commandPaletteOpen,
  currentDataset,
  datasetNames,
  detailsOpen,
  filterPaneOpen,
  focus,
  helpOpen,
  layoutKind,
  payload,
  search,
  selection,
  setView,
  view,
  popFocus,
} from "../state/store";
import type { ColorMode, LayoutKind, ViewKind } from "../types";

export function Topbar() {
  const searchRef = useRef<HTMLInputElement>(null);

  // Focus search when "/" is pressed (handled in useGlobalKeys but we need the ref)
  useEffect(() => {
    (window as unknown as { __searchInput?: HTMLInputElement }).__searchInput = searchRef.current ?? undefined;
    return () => {
      delete (window as unknown as { __searchInput?: HTMLInputElement }).__searchInput;
    };
  });

  const v = view.value;
  const lay = layoutKind.value;
  const col = colorMode.value;
  const ds = currentDataset.value;
  const names = datasetNames.value;
  const focused = focus.value.active;
  const hasSel = !!selection.value.nodeId;

  return (
    <div class="topbar">
      <span class="brand">CROSSFIRE</span>

      <button
        class="icon ghost"
        title="Toggle filter pane (F)"
        onClick={() => (filterPaneOpen.value = !filterPaneOpen.value)}
      >
        {iconSidebar()}
      </button>

      <select
        title="Dataset"
        value={ds ?? ""}
        onChange={(e) => {
          const t = e.currentTarget.value;
          currentDataset.value = t || null;
        }}
      >
        {!names.length && <option value="">— no datasets —</option>}
        {names.map((n) => (
          <option key={n} value={n}>{n}</option>
        ))}
      </select>

      <div class="seg" role="tablist" aria-label="View">
        {(["documents", "entities", "claims"] as ViewKind[]).map((k) => (
          <button
            key={k}
            class={v === k ? "active" : ""}
            onClick={() => setView(k)}
          >
            {labelView(k)}
          </button>
        ))}
      </div>

      <div class="seg" role="tablist" aria-label="Layout">
        {(["forceatlas2", "circle", "grid", "hierarchy"] as LayoutKind[]).map((k) => (
          <button
            key={k}
            class={lay === k ? "active" : ""}
            title={`Layout: ${labelLayout(k)}`}
            onClick={() => (layoutKind.value = k)}
          >
            {iconLayout(k)}
          </button>
        ))}
      </div>

      <div class="seg" role="tablist" aria-label="Color">
        {(["type", "community"] as ColorMode[]).map((k) => (
          <button
            key={k}
            class={col === k ? "active" : ""}
            title={`Color by ${k}`}
            onClick={() => (colorMode.value = k)}
          >
            {k === "type" ? "Type" : "Cluster"}
          </button>
        ))}
      </div>

      <div class="search-wrap">
        {iconSearch()}
        <input
          ref={searchRef}
          class="search"
          placeholder="Search nodes…  (press / to focus)"
          value={search.value}
          onInput={(e) => (search.value = e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              search.value = "";
              e.currentTarget.blur();
            }
          }}
        />
      </div>

      <button
        class="ghost"
        title="Open command palette (⌘K)"
        onClick={() => (commandPaletteOpen.value = true)}
      >
        ⌘K
      </button>

      <span class="spacer" />

      {focused && (
        <button class="ghost" title="Pop focus (Backspace)" onClick={popFocus}>
          {iconBack()} Unfocus
        </button>
      )}
      <button
        class={hasSel || detailsOpen.value ? "" : "ghost"}
        title="Toggle details pane"
        onClick={() => (detailsOpen.value = !detailsOpen.value)}
        disabled={!payload.value}
      >
        {iconPanel()}
      </button>
      <button class="icon ghost" title="Help (?)" onClick={() => (helpOpen.value = true)}>
        ?
      </button>
    </div>
  );
}

function labelView(k: ViewKind) {
  return k === "documents" ? "Docs" : k === "entities" ? "Entities" : "Claims";
}
function labelLayout(k: LayoutKind) {
  return k === "forceatlas2" ? "Force-directed" : k.charAt(0).toUpperCase() + k.slice(1);
}

// ---- inline icons (avoid extra deps) ----------------------------------

const I = (path: string) => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    {path.split("|").map((d, i) => <path key={i} d={d} />)}
  </svg>
);
const iconSearch = () => I("M21 21l-4.3-4.3|M11 19a8 8 0 1 1 0-16 8 8 0 0 1 0 16z");
const iconSidebar = () => I("M3 4h18v16H3z|M9 4v16");
const iconBack = () => I("M19 12H5|M12 19l-7-7 7-7");
const iconPanel = () => I("M3 4h18v16H3z|M15 4v16");

function iconLayout(k: LayoutKind) {
  switch (k) {
    case "forceatlas2":
      return I(
        "M12 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6z|" +
          "M5 19a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z|" +
          "M19 19a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z|" +
          "M12 9v5|M10 15l-4 1|M14 15l4 1",
      );
    case "circle":
      return I("M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z");
    case "grid":
      return I("M4 4h6v6H4z|M14 4h6v6h-6z|M4 14h6v6H4z|M14 14h6v6h-6z");
    case "hierarchy":
      return I("M12 3v4|M5 9v4|M19 9v4|M12 7l-7 2|M12 7l7 2|M5 13v4|M19 13v4");
  }
}
