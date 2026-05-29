from __future__ import annotations

import base64
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path

from server_firma import SignatureServer


def _json_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict) -> int:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        response.read()
        return response.status


def _local_url(server: SignatureServer) -> str:
    url = server.connection_url()
    assert url is not None
    return url.replace("0.0.0.0", "127.0.0.1")


def test_servidor_tablet_espera_y_publica_socio(tmp_path: Path) -> None:
    pdf = tmp_path / "lopd.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    server = SignatureServer(preferred_port=0)

    try:
        server.start()
        base_url = _local_url(server)

        waiting = _json_get(f"{base_url}/status")
        assert waiting["active"] is False

        token = server.set_active_signature(
            pdf_path=pdf,
            socio_id=12,
            nombre="Maria Test",
            dni="12345678Z",
        )
        active = _json_get(f"{base_url}/status")
        assert active["active"] is True
        assert active["token"] == token
        assert active["socioID"] == 12
        assert active["nombre"] == "Maria Test"
        assert active["dni"] == "12345678Z"

        with urllib.request.urlopen(f"{base_url}/documento.pdf", timeout=2) as response:
            assert response.read() == b"%PDF-1.4 test"
    finally:
        server.stop()


def test_servidor_rechaza_token_antiguo_y_encola_firma(tmp_path: Path) -> None:
    pdf = tmp_path / "lopd.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    server = SignatureServer(preferred_port=0)

    try:
        server.start()
        base_url = _local_url(server)
        token = server.set_active_signature(pdf_path=pdf, socio_id=7)
        image_data = base64.b64encode(b"signature-bytes").decode("ascii")
        signature = f"data:image/png;base64,{image_data}"

        try:
            _post_json(f"{base_url}/submit", {"token": "old", "signature": signature})
        except urllib.error.HTTPError as exc:
            assert exc.code == 409
        else:
            raise AssertionError("El servidor ha acceptat un token antic")

        assert _post_json(f"{base_url}/submit", {"token": token, "signature": signature}) == 200
        queued = server.queue.get_nowait()
        assert queued["type"] == "signature"
        assert queued["socioID"] == 7
        assert queued["token"] == token
        assert queued["image"] == b"signature-bytes"
        status = _json_get(f"{base_url}/status")
        assert status["active"] is False
        assert status["previewAvailable"] is False

        server.set_completed_document(b"%PDF-1.4 signed", socio_id=7, nombre="Maria Test")
        status = _json_get(f"{base_url}/status")
        assert status["active"] is False
        assert status["previewAvailable"] is True
        assert status["previewUrl"] == "/firmado.pdf"
        assert status["previewID"]

        with urllib.request.urlopen(f"{base_url}/firmado.pdf", timeout=2) as response:
            assert response.read() == b"%PDF-1.4 signed"
    finally:
        server.stop()


def test_servidor_usa_puerto_alternativo_si_el_preferido_esta_ocupado() -> None:
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("0.0.0.0", 0))
    blocker.listen(1)
    busy_port = blocker.getsockname()[1]
    server = SignatureServer(preferred_port=busy_port)

    try:
        _host, chosen_port = server.start()
        assert chosen_port != busy_port
    finally:
        server.stop()
        blocker.close()
