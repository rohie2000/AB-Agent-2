#!/usr/bin/env python3
"""Serve the local worksheet generator UI and API."""

from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from generate_worksheet_set import (
    GenerationError,
    generate_worksheet_set,
    load_demo_worksheet_set,
    normalize_payload,
    save_generated_json,
)
from render_worksheets import RenderConfig, render_html
from render_worksheets_pdf import render_pdf


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
OUT_DIR = ROOT / "out"
GENERATED_DIR = OUT_DIR / "generated"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "ABAgentHTTP/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self.serve_file(APP_DIR / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/app.js":
            return self.serve_file(APP_DIR / "app.js", "application/javascript; charset=utf-8")
        if parsed.path == "/style.css":
            return self.serve_file(APP_DIR / "style.css", "text/css; charset=utf-8")
        if parsed.path.startswith("/out/"):
            return self.serve_relative(parsed.path.lstrip("/"))
        if parsed.path == "/api/health":
            return self.send_json(
                {
                    "ok": True,
                    "openai_api_key_present": bool(os.environ.get("OPENAI_API_KEY")),
                }
            )
        self.send_error(HTTPStatus.NOT_FOUND, "Datei nicht gefunden.")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            return self.handle_generate(demo=False)
        if parsed.path == "/api/generate-demo":
            return self.handle_generate(demo=True)
        self.send_error(HTTPStatus.NOT_FOUND, "API-Endpunkt nicht gefunden.")

    def handle_generate(self, demo: bool) -> None:
        try:
            body = self.read_json_body()
            template_variant = str(body.get("template_variant", "instructions")).strip() or "instructions"

            if demo:
                worksheet_set = load_demo_worksheet_set()
                topic = worksheet_set["topic"]
            else:
                payload = normalize_payload(body)
                template_variant = payload["template_variant"]
                worksheet_set = generate_worksheet_set(payload)
                topic = payload["topic"]

            worksheet_set["_meta"]["template_variant"] = template_variant

            json_path = save_generated_json(worksheet_set, topic=topic)
            html_path = json_path.with_suffix(".html")
            pdf_path = json_path.with_suffix(".pdf")
            html = render_html(worksheet_set, config=RenderConfig(template_variant, html_path))
            html_path.write_text(html, encoding="utf-8")
            render_pdf(worksheet_set, pdf_path, template_variant=template_variant)

            self.send_json(
                {
                    "ok": True,
                    "topic": worksheet_set["topic"],
                    "level_count": len(worksheet_set["levels"]),
                    "json_path": str(json_path),
                    "html_path": str(html_path),
                    "pdf_path": str(pdf_path),
                    "preview_url": "/" + html_path.relative_to(ROOT).as_posix(),
                    "pdf_url": "/" + pdf_path.relative_to(ROOT).as_posix(),
                    "meta": worksheet_set.get("_meta", {}),
                }
            )
        except (GenerationError, ValueError) as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            self.send_json(
                {"ok": False, "error": f"Unerwarteter Fehler: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8")
        if not raw.strip():
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Der Request-Body muss ein JSON-Objekt sein.")
        return parsed

    def serve_relative(self, relative_path: str) -> None:
        path = ROOT / relative_path
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Datei nicht gefunden.")
            return
        mime_type, _ = mimetypes.guess_type(str(path))
        self.serve_file(path, mime_type or "application/octet-stream")

    def serve_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Datei nicht gefunden.")
            return

        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> int:
    host = "127.0.0.1"
    port = 8123
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"AB-Agent laeuft unter http://{host}:{port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
