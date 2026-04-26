// Global keyboard shortcuts. Bound on App mount; unbinds on unmount.
import { useEffect } from "preact/hooks";
import {
  clearFocus,
  colorMode,
  commandPaletteOpen,
  detailsOpen,
  filterPaneOpen,
  helpOpen,
  layoutKind,
  popFocus,
  resetSelection,
  search,
  setView,
  view,
} from "../../state/store";
import type { LayoutKind, ViewKind } from "../../types";

const LAYOUTS: LayoutKind[] = ["forceatlas2", "circle", "grid", "hierarchy"];
const VIEWS: ViewKind[] = ["documents", "entities", "claims"];

export function useGlobalKeys() {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      // If user is typing in an input/textarea, only intercept Esc + ⌘K.
      const target = e.target as HTMLElement;
      const inField = target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target.isContentEditable;

      const meta = e.metaKey || e.ctrlKey;

      // ⌘K / Ctrl+K — palette
      if (meta && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        commandPaletteOpen.value = !commandPaletteOpen.value;
        return;
      }

      // Esc closes overlays / clears selection / search
      if (e.key === "Escape") {
        if (commandPaletteOpen.value) {
          commandPaletteOpen.value = false;
          return;
        }
        if (helpOpen.value) {
          helpOpen.value = false;
          return;
        }
        if (search.value) {
          search.value = "";
          return;
        }
        resetSelection();
        return;
      }

      if (inField) return;

      // Letter shortcuts must NOT swallow OS-level chords like Ctrl+C (copy),
      // Ctrl+L (locate), Cmd+R (reload), Alt+Tab, etc. ⌘K and Esc above are
      // already handled. Anything else with Ctrl/Cmd/Alt held passes through
      // to the browser. Shift is allowed (Shift+F = focus visible).
      if (e.metaKey || e.ctrlKey || e.altKey) return;

      // "/" — focus search
      if (e.key === "/") {
        e.preventDefault();
        const w = window as unknown as { __searchInput?: HTMLInputElement };
        w.__searchInput?.focus();
        w.__searchInput?.select();
        return;
      }

      // "?" — help
      if (e.key === "?") {
        e.preventDefault();
        helpOpen.value = !helpOpen.value;
        return;
      }

      // Layout cycle
      if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        const i = LAYOUTS.indexOf(layoutKind.value);
        layoutKind.value = LAYOUTS[(i + 1) % LAYOUTS.length];
        return;
      }

      // Color mode toggle
      if (e.key === "c" || e.key === "C") {
        e.preventDefault();
        colorMode.value = colorMode.value === "type" ? "community" : "type";
        return;
      }

      // View cycle
      if (e.key === "v" || e.key === "V") {
        e.preventDefault();
        const i = VIEWS.indexOf(view.value);
        setView(VIEWS[(i + 1) % VIEWS.length]);
        return;
      }

      // F — toggle filter pane; Shift+F — focus visible
      if (e.key === "f") {
        e.preventDefault();
        filterPaneOpen.value = !filterPaneOpen.value;
        return;
      }
      if (e.key === "F") {
        e.preventDefault();
        const w = window as unknown as { __kgFocusVisible?: () => void };
        w.__kgFocusVisible?.();
        return;
      }

      // I — toggle details pane
      if (e.key === "i" || e.key === "I") {
        e.preventDefault();
        detailsOpen.value = !detailsOpen.value;
        return;
      }

      // Z — fit visible
      if (e.key === "z" || e.key === "Z") {
        e.preventDefault();
        const w = window as unknown as { __kgFitAll?: () => void };
        w.__kgFitAll?.();
        return;
      }

      // Backspace — pop focus; Shift+Backspace — clear focus
      if (e.key === "Backspace") {
        e.preventDefault();
        if (e.shiftKey) clearFocus();
        else popFocus();
        return;
      }
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);
}
