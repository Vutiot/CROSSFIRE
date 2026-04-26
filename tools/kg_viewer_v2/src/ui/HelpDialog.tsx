import { helpOpen } from "../state/store";

export function HelpDialog() {
  return (
    <div class="help-backdrop fade-in" onClick={() => (helpOpen.value = false)}>
      <div class="help-card" onClick={(e) => e.stopPropagation()}>
        <h2>Keyboard shortcuts</h2>
        <table>
          <tbody>
            <tr><td>Search nodes</td><td><kbd>/</kbd></td></tr>
            <tr><td>Command palette</td><td><kbd>⌘</kbd> <kbd>K</kbd> / <kbd>Ctrl</kbd> <kbd>K</kbd></td></tr>
            <tr><td>Toggle filter pane</td><td><kbd>F</kbd></td></tr>
            <tr><td>Toggle details pane</td><td><kbd>I</kbd></td></tr>
            <tr><td>Fit visible to viewport</td><td><kbd>Z</kbd></td></tr>
            <tr><td>Focus on visible subset</td><td><kbd>Shift</kbd> <kbd>F</kbd></td></tr>
            <tr><td>Pop focus</td><td><kbd>Backspace</kbd></td></tr>
            <tr><td>Clear focus</td><td><kbd>Shift</kbd> <kbd>Backspace</kbd></td></tr>
            <tr><td>Cycle layout</td><td><kbd>L</kbd></td></tr>
            <tr><td>Toggle color mode</td><td><kbd>C</kbd></td></tr>
            <tr><td>Cycle view</td><td><kbd>V</kbd></td></tr>
            <tr><td>Close panels / clear</td><td><kbd>Esc</kbd></td></tr>
            <tr><td>This dialog</td><td><kbd>?</kbd></td></tr>
          </tbody>
        </table>
        <p style={{ color: "var(--text-3)", fontSize: 11.5, marginTop: 16 }}>
          Click an entity-type or relationship-type pill to cycle off → include only → exclude.
        </p>
      </div>
    </div>
  );
}
