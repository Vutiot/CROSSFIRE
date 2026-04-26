#!/usr/bin/env python3
"""Static server for the v2 KG viewer.

Serves the Vite-built `dist/` bundle plus the same /api/datasets and
/api/data/{name} endpoints as the legacy `tools/kg_viewer/serve.py`. The
data-loading logic is reused via direct import.

Usage:
    # build first, then serve
    cd tools/kg_viewer_v2 && npm install && npm run build
    python tools/kg_viewer_v2/serve.py [datasets_dir] [--port PORT]

    # or, for live development:
    python tools/kg_viewer_v2/serve.py [datasets_dir] --port 8080  # API server
    cd tools/kg_viewer_v2 && npm run dev  # Vite dev server proxies /api -> 8080
"""

import argparse
import json
import sys
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Reuse the data-loading code from the legacy viewer so both tools speak the
# exact same payload shape. No import-time side-effects in that module.
THIS_DIR = Path(__file__).resolve().parent
LEGACY_DIR = THIS_DIR.parent / "kg_viewer"
sys.path.insert(0, str(LEGACY_DIR))
from serve import build_payload, discover_datasets  # noqa: E402  type: ignore


class V2Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, payloads=None, dataset_names=None, root_dir=None, **kwargs):
        self._payloads = payloads
        self._dataset_names = dataset_names
        super().__init__(*args, directory=str(root_dir), **kwargs)

    def do_GET(self):
        if self.path == "/api/datasets":
            self._respond_json(json.dumps(self._dataset_names).encode())
        elif self.path.startswith("/api/data/"):
            name = self.path[len("/api/data/"):]
            if name in self._payloads:
                self._respond_json(json.dumps(self._payloads[name]).encode())
            else:
                self.send_error(404, f"Dataset '{name}' not found")
        elif self.path == "/api/data":
            first = self._dataset_names[0] if self._dataset_names else None
            if first:
                self._respond_json(json.dumps(self._payloads[first]).encode())
            else:
                self.send_error(404, "No datasets loaded")
        else:
            super().do_GET()

    def _respond_json(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="CROSSFIRE KG Viewer v2 server")
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("data/datasets"),
        help="Dataset directory (default: data/datasets/)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument(
        "--api-only", action="store_true",
        help="Only serve /api endpoints (use with `npm run dev` Vite proxy)",
    )
    args = parser.parse_args()

    root = args.path.resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    datasets = discover_datasets(root)
    if not datasets:
        print(f"Error: no valid datasets found in {root}", file=sys.stderr)
        sys.exit(1)

    payloads, names = {}, []
    for name, path in datasets.items():
        print(f"Loading {name}...", end=" ", flush=True)
        payload = build_payload(path)
        payloads[name] = payload
        names.append(name)
        s = payload["stats"]
        info = f"nodes={s['total_nodes']}, edges={s['total_edges']}, contradictions={s['total_contradictions']}"
        if "total_claims" in s:
            info += f", claims={s['total_claims']}"
        print(f"({payload['layout']}) {info}")

    dist = THIS_DIR / "dist"
    if not args.api_only and not dist.is_dir():
        print(
            f"\nError: {dist} not found. Run `npm install && npm run build` "
            f"in tools/kg_viewer_v2/, or pass --api-only.",
            file=sys.stderr,
        )
        sys.exit(1)

    serve_dir = dist if not args.api_only else THIS_DIR
    handler = partial(V2Handler, payloads=payloads, dataset_names=names, root_dir=serve_dir)
    server = HTTPServer(("", args.port), handler)
    print(f"\n{len(payloads)} dataset(s) loaded. Serving at http://localhost:{args.port}")
    if args.api_only:
        print("API-only mode — start `npm run dev` for the UI.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
