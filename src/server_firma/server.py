from __future__ import annotations

import base64
import json
import queue
import secrets
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
    """HTTP senzill que exposa la tablet fixa de firma LOPD."""

    def __init__(self, preferred_port: int = 8765) -> None:
        self._thread: threading.Thread | None = None
        self._server: ThreadingHTTPServer | None = None
        self._queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._address: tuple[str, int] | None = None
        self._preferred_port = preferred_port
        self._lock = threading.Lock()
        self._active_signature: dict[str, Any] | None = None
        self._completed_document: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def start(self, pdf_path: str | Path | None = None, port: int | None = None) -> tuple[str, int]:
        if self._server is not None:
            raise RuntimeError("El servidor de firma ja està en execució")

        if pdf_path is not None:
            self.set_active_signature(pdf_path=pdf_path)

        bind_port = self._preferred_port if port is None else port
        Handler = self._build_handler()
        self._server = self._bind_server(Handler, bind_port)
        self._address = (self._server.server_address[0], self._server.server_address[1])
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self._address

    def ensure_running(self) -> tuple[str, int]:
        if self._server is not None and self._address is not None:
            return self._address
        return self.start()

    def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
        self._address = None
        self.clear_active_signature()
        self.clear_completed_document()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def set_active_signature(
        self,
        *,
        pdf_path: str | Path,
        socio_id: int | None = None,
        nombre: str = "",
        dni: str = "",
    ) -> str:
        pdf = Path(pdf_path)
        if not pdf.exists():
            raise FileNotFoundError(pdf)

        token = secrets.token_urlsafe(16)
        with self._lock:
            self._completed_document = None
            self._active_signature = {
                "token": token,
                "socioID": socio_id,
                "nombre": nombre,
                "dni": dni,
                "pdf_path": pdf,
            }
        return token

    def clear_active_signature(self) -> None:
        with self._lock:
            self._active_signature = None

    def set_completed_document(self, documento: bytes, *, socio_id: int | None = None, nombre: str = "") -> None:
        with self._lock:
            self._completed_document = {
                "documento": documento,
                "socioID": socio_id,
                "nombre": nombre,
                "previewID": secrets.token_urlsafe(8),
            }

    def clear_completed_document(self) -> None:
        with self._lock:
            self._completed_document = None

    @property
    def queue(self) -> "queue.Queue[dict[str, Any]]":
        return self._queue

    @property
    def pdf_path(self) -> Path | None:
        with self._lock:
            if self._active_signature is None:
                return None
            return self._active_signature.get("pdf_path")

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
    def _bind_server(self, handler: type[BaseHTTPRequestHandler], port: int) -> ThreadingHTTPServer:
        if port == 0:
            return ThreadingHTTPServer(("0.0.0.0", 0), handler)

        last_error: OSError | None = None
        for candidate in range(port, port + 20):
            try:
                return ThreadingHTTPServer(("0.0.0.0", candidate), handler)
            except OSError as exc:
                last_error = exc

        try:
            return ThreadingHTTPServer(("0.0.0.0", 0), handler)
        except OSError:
            if last_error is not None:
                raise last_error
            raise

    def _status_payload(self) -> dict[str, Any]:
        with self._lock:
            active = self._active_signature.copy() if self._active_signature else None
            completed = self._completed_document.copy() if self._completed_document else None

        if active is None:
            return {
                "active": False,
                "hasSignature": not self._queue.empty(),
                "previewAvailable": completed is not None,
                "previewUrl": "/firmado.pdf" if completed is not None else None,
                "previewID": completed.get("previewID") if completed else None,
                "nombre": completed.get("nombre", "") if completed else "",
            }

        return {
            "active": True,
            "hasSignature": not self._queue.empty(),
            "token": active["token"],
            "socioID": active.get("socioID"),
            "nombre": active.get("nombre") or "",
            "dni": active.get("dni") or "",
            "pdfUrl": "/documento.pdf",
        }

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):  # type: ignore[misc]
            server_version = "GentGranSignature/1.0"

            def _set_headers(self, status: HTTPStatus, content_type: str = "text/html; charset=utf-8") -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                if self.path == "/" or self.path.startswith("/index"):
                    self._serve_index()
                elif self.path.startswith("/documento"):
                    self._serve_pdf()
                elif self.path.startswith("/firmado"):
                    self._serve_completed_pdf()
                elif self.path.startswith("/status"):
                    self._serve_status()
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)

            def _serve_index(self) -> None:
                self._set_headers(HTTPStatus.OK, "text/html; charset=utf-8")
                self.wfile.write(_SIGNATURE_HTML.encode("utf-8"))

            def _serve_pdf(self) -> None:
                pdf_path = server.pdf_path
                if pdf_path is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    with pdf_path.open("rb") as fh:
                        data = fh.read()
                except OSError:
                    self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
                    return

                self._set_headers(HTTPStatus.OK, "application/pdf")
                self.wfile.write(data)

            def _serve_completed_pdf(self) -> None:
                with server._lock:
                    completed = server._completed_document.copy() if server._completed_document else None
                if completed is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = completed.get("documento")
                if not isinstance(data, (bytes, bytearray)):
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                self._set_headers(HTTPStatus.OK, "application/pdf")
                self.wfile.write(bytes(data))

            def _serve_status(self) -> None:
                data = json.dumps(server._status_payload()).encode("utf-8")
                self._set_headers(HTTPStatus.OK, "application/json")
                self.wfile.write(data)

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

                token = payload.get("token")
                signature = payload.get("signature")
                if not isinstance(token, str) or not isinstance(signature, str):
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                with server._lock:
                    active = server._active_signature.copy() if server._active_signature else None
                if active is None or token != active["token"]:
                    self.send_error(HTTPStatus.CONFLICT)
                    return

                try:
                    header, b64data = signature.split(",", 1)
                    if "base64" not in header:
                        raise ValueError
                    img_bytes = base64.b64decode(b64data)
                except Exception:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return

                server._queue.put(
                    {
                        "type": "signature",
                        "image": img_bytes,
                        "token": token,
                        "socioID": active.get("socioID"),
                    }
                )
                server.clear_active_signature()

                self._set_headers(HTTPStatus.OK, "application/json")
                self.wfile.write(b"{\"status\": \"ok\"}")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        return Handler


_SIGNATURE_HTML = """<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Firma LOPD</title>
  <style>
    body { font-family: sans-serif; margin: 0; background: #f4f4f2; color: #1f2933; }
    main { max-width: 860px; margin: 0 auto; padding: 1.2rem; }
    h1 { font-size: 1.45rem; margin: 0 0 0.35rem; }
    .card { background: white; padding: 1rem; border: 1px solid #d7d7d2; border-radius: 8px; }
    .muted { color: #59636e; }
    .person { margin: 1rem 0; padding: 0.8rem; border-left: 4px solid #6f914d; background: #f7faf4; }
    .person strong { display: block; font-size: 1.2rem; }
    canvas { width: 100%; height: auto; border: 2px dashed #6f914d; border-radius: 8px; background: #fff; touch-action: none; }
    button { background: #6f914d; border: none; color: white; font-size: 1rem; padding: 0.65rem 1.1rem; border-radius: 6px; margin-right: 0.5rem; }
    button:disabled { background: #ccc; color: #666; }
    a { color: #2f6f9f; font-weight: 600; }
    .actions { margin-top: 1rem; }
    .preview { margin-top: 1rem; border-top: 1px solid #d7d7d2; padding-top: 1rem; }
    .preview iframe { width: 100%; height: 560px; border: 1px solid #d7d7d2; border-radius: 6px; background: white; }
    #status { margin-top: 0.8rem; font-weight: bold; min-height: 1.4rem; }
    #signing[hidden], #waiting[hidden], #preview[hidden] { display: none; }
  </style>
</head>
<body>
  <main>
    <div class="card">
      <h1>Consentiment LOPD</h1>
      <section id="waiting">
        <p class="muted">Tablet preparada. Esperant que s'enviï un soci des de l'ordinador.</p>
      </section>
      <section id="signing" hidden>
        <div class="person">
          <strong id="person-name"></strong>
          <span id="person-dni"></span>
        </div>
        <p><a id="pdf-link" href="/documento.pdf" target="_blank">Obrir document PDF</a></p>
        <p class="muted">Signa dins del requadre utilitzant el dit o un llapis tàctil.</p>
        <canvas id="pad" width="760" height="270"></canvas>
        <div class="actions">
          <button id="clear" type="button">Esborrar</button>
          <button id="submit" type="button" disabled>Enviar signatura</button>
        </div>
      </section>
      <section id="preview" class="preview" hidden>
        <p><a id="preview-link" href="/firmado.pdf" target="_blank">Obrir document signat</a></p>
        <iframe id="preview-frame" title="Document LOPD signat"></iframe>
      </section>
      <div id="status"></div>
    </div>
  </main>
  <script>
    const waiting = document.getElementById('waiting');
    const signing = document.getElementById('signing');
    const personName = document.getElementById('person-name');
    const personDni = document.getElementById('person-dni');
    const pdfLink = document.getElementById('pdf-link');
    const preview = document.getElementById('preview');
    const previewLink = document.getElementById('preview-link');
    const previewFrame = document.getElementById('preview-frame');
    const canvas = document.getElementById('pad');
    const ctx = canvas.getContext('2d');
    const submitBtn = document.getElementById('submit');
    const clearBtn = document.getElementById('clear');
    const statusLabel = document.getElementById('status');
    let activeToken = null;
    let currentPreviewID = null;

    ctx.lineWidth = 2;
    ctx.lineCap = 'round';

    const clearPad = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      submitBtn.disabled = true;
    };

    const setWaiting = (message = '') => {
      activeToken = null;
      clearPad();
      waiting.hidden = false;
      signing.hidden = true;
      statusLabel.textContent = message;
    };

    const hidePreview = () => {
      preview.hidden = true;
      previewFrame.removeAttribute('src');
      currentPreviewID = null;
    };

    const showPreview = (payload) => {
      if (currentPreviewID && payload.previewID === currentPreviewID && !preview.hidden) {
        return;
      }
      const url = payload.previewUrl || '/firmado.pdf';
      currentPreviewID = payload.previewID || String(Date.now());
      previewLink.href = url;
      previewFrame.src = `${url}?t=${encodeURIComponent(currentPreviewID)}`;
      preview.hidden = false;
    };

    const setActive = (payload) => {
      if (activeToken !== payload.token) {
        clearPad();
        statusLabel.textContent = '';
      }
      hidePreview();
      activeToken = payload.token;
      personName.textContent = payload.nombre || 'Soci sense nom';
      personDni.textContent = payload.dni ? `DNI/NIE ${payload.dni}` : '';
      pdfLink.href = payload.pdfUrl || '/documento.pdf';
      waiting.hidden = true;
      signing.hidden = false;
    };

    const refreshStatus = () => {
      fetch('/status', { cache: 'no-store' })
        .then(resp => resp.json())
        .then(payload => {
          if (payload.active) {
            setActive(payload);
          } else {
            setWaiting(statusLabel.textContent);
            if (payload.previewAvailable) {
              showPreview(payload);
            } else {
              hidePreview();
            }
          }
        })
        .catch(() => {
          statusLabel.textContent = 'No es pot contactar amb el servidor de firma.';
        });
    };

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
      clearPad();
      statusLabel.textContent = '';
    });

    submitBtn.addEventListener('click', () => {
      if (submitBtn.disabled || !activeToken) {
        return;
      }
      statusLabel.textContent = 'Enviant signatura...';
      fetch('/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: activeToken, signature: canvas.toDataURL('image/png') })
      }).then(resp => {
        if (!resp.ok) {
          throw new Error('Error en enviar la signatura');
        }
        setWaiting('Signatura enviada correctament. Generant previsualització...');
      }).catch(err => {
        statusLabel.textContent = err.message || 'No s\\'ha pogut enviar la signatura';
      });
    });

    setWaiting();
    refreshStatus();
    setInterval(refreshStatus, 1500);
  </script>
</body>
</html>
"""


__all__ = ["SignatureServer", "_read_local_ip"]
