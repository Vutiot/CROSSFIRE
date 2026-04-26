import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import {
  colorMode,
  commandPaletteOpen,
  currentDataset,
  detailsOpen,
  filterPaneOpen,
  filters,
  helpOpen,
  layoutKind,
  payload,
  search,
  selectNode,
  selection,
  setView,
  view,
  clearFocus,
  popFocus,
} from "../state/store";
import { showToast } from "./App";
import type { LayoutKind } from "../types";

interface Cmd {
  id: string;
  label: string;
  hint?: string;
  group: string;
  run: () => void;
  keywords?: string;
}

export function CommandPalette() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const commands = useCommands();
  const filtered = useMemo(() => filterCmds(commands, q), [commands, q]);

  useEffect(() => {
    setIdx(0);
  }, [q, filtered.length]);

  function close() {
    commandPaletteOpen.value = false;
  }
  function activate(cmd: Cmd | undefined) {
    if (!cmd) return;
    cmd.run();
    close();
  }

  return (
    <div class="palette-backdrop fade-in" onClick={close}>
      <div class="palette" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          placeholder="Type a command, jump to a node, or search…"
          value={q}
          onInput={(e) => setQ(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              e.preventDefault();
              close();
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              setIdx((i) => Math.min(filtered.length - 1, i + 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setIdx((i) => Math.max(0, i - 1));
            } else if (e.key === "Enter") {
              e.preventDefault();
              activate(filtered[idx]);
            }
          }}
        />
        <ul>
          {filtered.length === 0 && (
            <li style={{ color: "var(--text-faint)" }}>No matches</li>
          )}
          {filtered.map((cmd, i) => (
            <li
              key={cmd.id}
              class={i === idx ? "active" : ""}
              onMouseEnter={() => setIdx(i)}
              onClick={() => activate(cmd)}
            >
              <span style={{ color: "var(--text-3)" }}>{cmd.group}</span>
              <span>{cmd.label}</span>
              {cmd.hint && <span class="hint">{cmd.hint}</span>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function useCommands(): Cmd[] {
  const p = payload.value;
  const cmds: Cmd[] = [];

  // Layout commands
  for (const k of ["forceatlas2", "circle", "grid", "hierarchy"] as LayoutKind[]) {
    cmds.push({
      id: `layout:${k}`,
      group: "Layout",
      label: `Set layout: ${k}`,
      run: () => (layoutKind.value = k),
    });
  }

  // View commands
  for (const v of ["documents", "entities", "claims"] as const) {
    cmds.push({
      id: `view:${v}`,
      group: "View",
      label: `Switch to ${v} view`,
      run: () => setView(v),
    });
  }

  // Color
  cmds.push(
    {
      id: "color:type",
      group: "Color",
      label: "Color by entity type",
      run: () => (colorMode.value = "type"),
    },
    {
      id: "color:community",
      group: "Color",
      label: "Color by Louvain community",
      run: () => (colorMode.value = "community"),
    },
  );

  // UI
  cmds.push(
    {
      id: "ui:toggle-filters",
      group: "UI",
      label: "Toggle filter pane",
      hint: "F",
      run: () => (filterPaneOpen.value = !filterPaneOpen.value),
    },
    {
      id: "ui:toggle-details",
      group: "UI",
      label: "Toggle details pane",
      run: () => (detailsOpen.value = !detailsOpen.value),
    },
    {
      id: "ui:help",
      group: "UI",
      label: "Show keyboard shortcuts",
      hint: "?",
      run: () => (helpOpen.value = true),
    },
  );

  // Camera / focus
  cmds.push(
    {
      id: "cam:fit",
      group: "Camera",
      label: "Fit visible nodes",
      hint: "Z",
      run: () => {
        const w = window as unknown as { __kgFitAll?: () => void };
        w.__kgFitAll?.();
      },
    },
    {
      id: "focus:visible",
      group: "Focus",
      label: "Focus on currently visible nodes",
      run: () => {
        const w = window as unknown as { __kgFocusVisible?: () => void };
        w.__kgFocusVisible?.();
      },
    },
    {
      id: "focus:pop",
      group: "Focus",
      label: "Pop last focus",
      hint: "⌫",
      run: () => popFocus(),
    },
    {
      id: "focus:clear",
      group: "Focus",
      label: "Clear focus",
      run: () => clearFocus(),
    },
  );

  // Isolate selection (node OR edge) to N-hop. Only meaningful when something
  // is selected — surfaced unconditionally so users can see the affordance,
  // and the run() short-circuits with a hint when no selection exists.
  for (const hops of [1, 2, 3]) {
    cmds.push({
      id: `isolate:${hops}`,
      group: "Isolate",
      label: `Isolate selection to ${hops}-hop`,
      run: () => {
        const w = window as unknown as {
          __kgFocusNeighborhood?: (h: number) => void;
          __kgFocusEdgeNeighborhood?: (h: number) => void;
        };
        if (selection.value.nodeId) {
          w.__kgFocusNeighborhood?.(hops);
          showToast(`Isolated ${hops}-hop neighborhood`);
        } else if (selection.value.edgeId) {
          w.__kgFocusEdgeNeighborhood?.(hops);
          showToast(`Isolated edge + ${hops}-hop endpoints`);
        } else {
          showToast("Select a node or edge first");
        }
      },
    });
  }

  // Filters quick toggles
  cmds.push(
    {
      id: "filter:contradictions",
      group: "Filter",
      label: filters.value.showContradictions
        ? "Hide non-contradiction nodes (off)"
        : "Show only contradictions",
      run: () => (filters.value = { ...filters.value, showContradictions: !filters.value.showContradictions }),
    },
    {
      id: "filter:distractors",
      group: "Filter",
      label: filters.value.showDistractors ? "Hide distractor-only filter" : "Show only distractors",
      run: () => (filters.value = { ...filters.value, showDistractors: !filters.value.showDistractors }),
    },
    {
      id: "filter:clear",
      group: "Filter",
      label: "Clear all filters",
      run: () => {
        filters.value = {
          entityTypes: {},
          relationTypes: {},
          showContradictions: false,
          showDistractors: false,
          scope: "all",
        };
        showToast("Filters cleared");
      },
    },
  );

  // Datasets
  if (p) {
    cmds.push({
      id: "ds:current",
      group: "Dataset",
      label: `Current: ${currentDataset.value}`,
      hint: "—",
      run: () => {},
    });
  }

  // Jump-to-node — search by canonical name in current view
  if (p) {
    const raw = view.value === "documents" ? p.graph : view.value === "claims" ? p.claims_graph : p.entity_graph;
    for (const n of raw.nodes.slice(0, 500)) {
      cmds.push({
        id: `node:${n.id}`,
        group: "Node",
        label: n.canonical_name,
        hint: n.entity_type,
        keywords: `${n.canonical_name} ${n.id} ${n.aliases?.join(" ") ?? ""}`,
        run: () => {
          selectNode(n.id, new Set([n.id]));
          search.value = "";
        },
      });
    }
  }

  return cmds;
}

function filterCmds(cmds: Cmd[], q: string): Cmd[] {
  const ql = q.trim().toLowerCase();
  if (!ql) return cmds.slice(0, 60);
  return cmds
    .filter((c) =>
      (c.keywords ?? `${c.group} ${c.label}`).toLowerCase().includes(ql),
    )
    .slice(0, 60);
}
