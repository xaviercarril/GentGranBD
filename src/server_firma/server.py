from __future__ import annotations

import base64
import json
import queue
import socket
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def _read_local_ip() -> str:
    """Best-effort obtenció de la IP local per compartir amb el mòbil."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


class SignatureServer:
    """HTTP senzill que exposa el canvas de firma per a dispositius mòbils."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._server: ThreadingHTTPServer | None = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._pdf_path: Path | None = None
        self._address: tuple[str, int] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, pdf_path: str | Path, port: int = 0) -> tuple[str, int]:
        if self._server is not None:
            raise RuntimeError("El servidor de firma ja està en execució")

        self._pdf_path = Path(pdf_path)
        if not self._pdf_path.exists():
            raise FileNotFoundError(self._pdf_path)

        Handler = self._build_handler()
        self._server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
        self._address = (self._server.server_address[0], self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self._address

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
        self._pdf_path = None
        self._address = None
        # Netegem la cua per evitar processar restes de peticions
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @property
    def queue(self) -> "queue.Queue[dict[str, Any]]":
        return self._queue

    @property
    def pdf_path(self) -> Path | None:
        return self._pdf_path

    @property
    def running(self) -> bool:
        return self._server is not None

    def connection_url(self) -> str | None:
        if not self._server or not self._address:
            return None
        host_ip = _read_local_ip()
        port = self._address[1]
        return f"http://{host_ip}:{port}"

    # ------------------------------------------------------------------
    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):  # type: ignore[misc]
            server_version = "GentGranSignature/1.0"

            def _set_headers(self, status: HTTPStatus, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

            # --------------------------- GET ---------------------------
            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/" or self.path.startswith("/index"):
                    self._serve_index()
                elif self.path.startswith("/documento"):
                    self._serve_pdf()
                elif self.path.startswith("/status"):
                    self._serve_status()
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def _serve_index(self) -> None:
                pdf_url = "/documento.pdf"
                body = _SIGNATURE_HTML.replace("{pdf_url}", pdf_url)
                data = body.encode("utf-8")
                self._set_headers(HTTPStatus.OK, "text/html; charset=utf-8")
                self.wfile.write(data)

            def _serve_pdf(self) -> None:
                if server._pdf_path is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    with server._pdf_path.open("rb") as fh:
                        data = fh.read()
                except OSError:
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                self._set_headers(HTTPStatus.OK, "application/pdf")
                self.wfile.write(data)

            def _serve_status(self) -> None:
                payload = {
                    "hasSignature": not server._queue.empty(),
                }
                data = json.dumps(payload).encode("utf-8")
                self._set_headers(HTTPStatus.OK, "application/json")
                self.wfile.write(data)

            # --------------------------- POST --------------------------
            def do_POST(self) -> None:  # noqa: N802
                if self.path.startswith("/submit"):
                    self._handle_submit()
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def _handle_submit(self) -> None:
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                signature = payload.get("signature")
                if not isinstance(signature, str):
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                try:
                    header, b64data = signature.split(",", 1)
                    if "base64" not in header:
                        raise ValueError
                    img_bytes = base64.b64decode(b64data)
                except Exception:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                server._queue.put({"type": "signature", "image": img_bytes})

                self._set_headers(HTTPStatus.OK, "application/json")
                self.wfile.write(b"{\"status\": \"ok\"}")

            # --------------------------- misc -------------------------
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                # Evitem soroll al terminal
                return

        return Handler


_SIGNATURE_HTML = """<!DOCTYPE html>
<html lang=\"ca\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Firma LOPD</title>
  <style>
    body { font-family: sans-serif; margin: 1.5rem; background: #f6f6f6; }
    h1 { font-size: 1.4rem; margin-bottom: 0.5rem; }
    .card { background: white; padding: 1rem; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
    canvas { width: 100%; max-width: 700px; height: auto; border: 2px dashed #7da453; border-radius: 12px; background: #fff; touch-action: none; }
    button { background: #7da453; border: none; color: white; font-size: 1rem; padding: 0.6rem 1.2rem; border-radius: 6px; margin-right: 0.5rem; }
    button:disabled { background: #ccc; color: #666; }
    .link { margin-bottom: 1rem; display: inline-block; }
    .actions { margin-top: 1rem; }
    #status { margin-top: 0.8rem; font-weight: bold; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Consentiment LOPD</h1>
    <p class=\"link\"><a href=\"{pdf_url}\" target=\"_blank\">Obrir document PDF</a></p>
    <p>Signa dins del requadre utilitzant el dit o un llapis tàctil.</p>
    <canvas id=\"pad\" width=\"700\" height=\"250\"></canvas>
    <div class=\"actions\">
      <button id=\"clear\" type=\"button\">Esborrar</button>
      <button id=\"submit\" type=\"button\" disabled>Enviar signatura</button>
    </div>
    <div id=\"status\"></div>
  </div>
  <script>
    const canvas = document.getElementById('pad');
    const ctx = canvas.getContext('2d');
    const submitBtn = document.getElementById('submit');
    const clearBtn = document.getElementById('clear');
    const statusLabel = document.getElementById('status');

    ctx.lineWidth = 2;
    ctx.lineCap = 'round';

    const getScales = () => {
      const rect = canvas.getBoundingClientRect();
      return {
        rect,
        scaleX: canvas.width / rect.width,
        scaleY: canvas.height / rect.height,
      };
    };

    const toCanvasPoint = (clientX, clientY) => {
      const { rect, scaleX, scaleY } = getScales();
      return {
        x: (clientX - rect.left) * scaleX,
        y: (clientY - rect.top) * scaleY,
      };
    };

    let drawing = false;

    const beginStroke = (clientX, clientY) => {
      drawing = true;
      statusLabel.textContent = '';
      const { x, y } = toCanvasPoint(clientX, clientY);
      ctx.beginPath();
      ctx.moveTo(x, y);
    };

    const continueStroke = (clientX, clientY) => {
      if (!drawing) return;
      const { x, y } = toCanvasPoint(clientX, clientY);
      ctx.lineTo(x, y);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(x, y);
      submitBtn.disabled = false;
    };

    const finishStroke = () => {
      drawing = false;
    };

    if (window.PointerEvent) {
      canvas.addEventListener('pointerdown', (event) => {
        if (event.pointerType === 'mouse' && event.button !== 0) {
          return;
        }
        beginStroke(event.clientX, event.clientY);
        if (event.pointerId !== undefined) {
          canvas.setPointerCapture(event.pointerId);
        }
        event.preventDefault();
      }, { passive: false });

      canvas.addEventListener('pointermove', (event) => {
        if (!drawing) return;
        continueStroke(event.clientX, event.clientY);
        event.preventDefault();
      }, { passive: false });

      const endPointer = (event) => {
        if (!drawing) return;
        finishStroke();
        if (event.pointerId !== undefined) {
          canvas.releasePointerCapture(event.pointerId);
        }
        event.preventDefault();
      };

      canvas.addEventListener('pointerup', endPointer);
      canvas.addEventListener('pointercancel', endPointer);
      canvas.addEventListener('pointerleave', endPointer);
    } else {
      canvas.addEventListener('mousedown', (event) => {
        if (event.button !== 0) return;
        beginStroke(event.clientX, event.clientY);
        event.preventDefault();
      });

      canvas.addEventListener('mousemove', (event) => {
        if (!drawing) return;
        continueStroke(event.clientX, event.clientY);
        event.preventDefault();
      });

      document.addEventListener('mouseup', () => {
        if (!drawing) return;
        finishStroke();
      });

      canvas.addEventListener('touchstart', (event) => {
        if (!event.touches.length) return;
        const touch = event.touches[0];
        beginStroke(touch.clientX, touch.clientY);
        event.preventDefault();
      }, { passive: false });

      canvas.addEventListener('touchmove', (event) => {
        if (!event.touches.length) return;
        const touch = event.touches[0];
        continueStroke(touch.clientX, touch.clientY);
        event.preventDefault();
      }, { passive: false });

      const endTouch = (event) => {
        if (!drawing) return;
        finishStroke();
        event.preventDefault();
      };

      canvas.addEventListener('touchend', endTouch, { passive: false });
      canvas.addEventListener('touchcancel', endTouch, { passive: false });
    }

    clearBtn.addEventListener('click', () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      submitBtn.disabled = true;
      statusLabel.textContent = '';
    });

    submitBtn.addEventListener('click', () => {
      if (submitBtn.disabled) {
        return;
      }
      statusLabel.textContent = 'Enviant signatura...';
      fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ signature: canvas.toDataURL('image/png') })
      }).then(resp => {
        if (!resp.ok) {
          throw new Error('Error en enviar la signatura');
        }
        statusLabel.textContent = 'Signatura enviada correctament. Pots tancar aquesta pàgina.';
        submitBtn.disabled = true;
      }).catch(err => {
        statusLabel.textContent = err.message || 'No s\\'ha pogut enviar la signatura';
      });
    });
  </script>
</body>
</html>
"""


__all__ = ["SignatureServer", "_read_local_ip"]
