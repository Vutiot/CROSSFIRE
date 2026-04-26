// Reactive view of currently-visible counts, populated by GraphCanvas after
// each filter pass. Lives outside store.ts to avoid a circular import with
// the canvas.
import { signal } from "@preact/signals";

export const visibleCounts = signal<{ nodes: number; edges: number; matches: number }>({
  nodes: 0,
  edges: 0,
  matches: 0,
});
