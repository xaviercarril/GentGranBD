from __future__ import annotations

import io
import os
import queue
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from controladores.socios import (
    consultar_firma_LOPD,
    consultar_socio,
    eliminar_documento_firma_LOPD,
    generar_pdf_LOPD,
    guardar_documento_firma_LOPD,
    obtener_documento_firma_LOPD,
)
from server_firma import SignatureServer

try:
    import qrcode
except ImportError:  # pragma: no cover - fallback visual si falta la dependencia
    qrcode = None


def _build_qr_pixmap(text: str, size_px: int) -> QPixmap:
    if qrcode is not None:
        qr = qrcode.QRCode(version=None, box_size=8, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap

    matrix = _make_qr_matrix(text)
    module_count = len(matrix)
    quiet_zone = 4
    total_modules = module_count + quiet_zone * 2
    scale = max(1, size_px // total_modules)
    image_size = total_modules * scale
    image = QImage(image_size, image_size, QImage.Format_RGB32)
    image.fill(0xFFFFFF)

    for row, values in enumerate(matrix):
        for col, is_dark in enumerate(values):
            if not is_dark:
                continue
            x0 = (col + quiet_zone) * scale
            y0 = (row + quiet_zone) * scale
            for y in range(y0, y0 + scale):
                for x in range(x0, x0 + scale):
                    image.setPixel(x, y, 0x000000)

    return QPixmap.fromImage(image)


def _make_qr_matrix(text: str) -> list[list[bool]]:
    """Genera un QR byte-mode Version 3-L, suficient per a URLs locals."""

    data = text.encode("utf-8")
    data_codewords = 55
    if len(data) > 53:
        raise ValueError("La URL és massa llarga per al QR intern")

    bits: list[int] = []
    _append_bits(bits, 0b0100, 4)  # byte mode
    _append_bits(bits, len(data), 8)
    for byte in data:
        _append_bits(bits, byte, 8)
    _append_bits(bits, 0, min(4, data_codewords * 8 - len(bits)))
    while len(bits) % 8:
        bits.append(0)

    codewords = [_bits_to_int(bits[i : i + 8]) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(codewords) < data_codewords:
        codewords.append(pad)
        pad = 0x11 if pad == 0xEC else 0xEC

    all_codewords = codewords + _reed_solomon_remainder(codewords, 15)
    data_bits: list[int] = []
    for codeword in all_codewords:
        _append_bits(data_bits, codeword, 8)

    version = 3
    size = 17 + version * 4
    modules: list[list[bool | None]] = [[None for _ in range(size)] for _ in range(size)]
    function: list[list[bool]] = [[False for _ in range(size)] for _ in range(size)]

    def set_function(row: int, col: int, dark: bool) -> None:
        modules[row][col] = dark
        function[row][col] = True

    def draw_finder(row: int, col: int) -> None:
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                r = row + dy
                c = col + dx
                if not (0 <= r < size and 0 <= c < size):
                    continue
                is_finder = 0 <= dx <= 6 and 0 <= dy <= 6 and (
                    dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)
                )
                set_function(r, c, is_finder)

    def draw_alignment(center: int) -> None:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                is_dark = max(abs(dx), abs(dy)) != 1
                set_function(center + dy, center + dx, is_dark)

    draw_finder(0, 0)
    draw_finder(0, size - 7)
    draw_finder(size - 7, 0)
    draw_alignment(22)

    for i in range(size):
        if not function[6][i]:
            set_function(6, i, i % 2 == 0)
        if not function[i][6]:
            set_function(i, 6, i % 2 == 0)

    for i in range(9):
        if i != 6:
            set_function(8, i, False)
            set_function(i, 8, False)
    for i in range(8):
        set_function(size - 1 - i, 8, False)
        set_function(8, size - 1 - i, False)
    set_function(8, 8, False)
    set_function(4 * version + 9, 8, True)

    bit_index = 0
    upward = True
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for offset in range(2):
                c = col - offset
                if function[row][c]:
                    continue
                bit = data_bits[bit_index] if bit_index < len(data_bits) else 0
                dark = bool(bit)
                if (row + c) % 2 == 0:
                    dark = not dark
                modules[row][c] = dark
                bit_index += 1
        upward = not upward
        col -= 2

    format_bits = _format_bits(error_level_bits=0b01, mask=0)
    _draw_format_bits(modules, format_bits)

    return [[bool(cell) for cell in row] for row in modules]


def _append_bits(bits: list[int], value: int, width: int) -> None:
    for i in range(width - 1, -1, -1):
        bits.append((value >> i) & 1)


def _bits_to_int(bits: list[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def _reed_solomon_remainder(data: list[int], degree: int) -> list[int]:
    divisor = [1]
    for i in range(degree):
        divisor = _poly_multiply(divisor, [1, _gf_pow(2, i)])

    result = [0] * degree
    for byte in data:
        factor = byte ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor[1:]):
            result[i] ^= _gf_multiply(coef, factor)
    return result


def _poly_multiply(a: list[int], b: list[int]) -> list[int]:
    result = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] ^= _gf_multiply(x, y)
    return result


def _gf_multiply(x: int, y: int) -> int:
    z = 0
    for i in range(8):
        if (y >> i) & 1:
            z ^= x << i
    for i in range(14, 7, -1):
        if (z >> i) & 1:
            z ^= 0x11D << (i - 8)
    return z


def _gf_pow(x: int, power: int) -> int:
    result = 1
    for _ in range(power):
        result = _gf_multiply(result, x)
    return result


def _format_bits(error_level_bits: int, mask: int) -> int:
    data = (error_level_bits << 3) | mask
    value = data << 10
    generator = 0x537
    for i in range(14, 9, -1):
        if (value >> i) & 1:
            value ^= generator << (i - 10)
    return ((data << 10) | value) ^ 0x5412


def _draw_format_bits(modules: list[list[bool | None]], bits: int) -> None:
    size = len(modules)
    coords_1 = [
        (8, 0),
        (8, 1),
        (8, 2),
        (8, 3),
        (8, 4),
        (8, 5),
        (8, 7),
        (8, 8),
        (7, 8),
        (5, 8),
        (4, 8),
        (3, 8),
        (2, 8),
        (1, 8),
        (0, 8),
    ]
    coords_2 = (
        [(size - 1 - i, 8) for i in range(7)]
        + [(8, size - 8 + i) for i in range(8)]
    )
    for i, (row, col) in enumerate(coords_1):
        modules[row][col] = bool((bits >> i) & 1)
    for i, (row, col) in enumerate(coords_2):
        modules[row][col] = bool((bits >> i) & 1)


class LOPDFirmaDialog(QDialog):
    """Gestor complet del document LOPD d'un soci."""

    def __init__(self, socio_id: int, parent=None) -> None:
        super().__init__(parent)
        self._socio_id = socio_id
        self._server = SignatureServer()
        self._server_pdf: Optional[Path] = None
        self._active_token: str | None = None
        self._temp_view_files: list[Path] = []
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll_signature_queue)

        self.setWindowTitle("Gestió LOPD del soci")
        self.setMinimumWidth(480)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)

        self._progress_label = QLabel("")
        self._progress_label.setWordWrap(True)

        self._server_url = QLineEdit()
        self._server_url.setReadOnly(True)
        self._server_url.setPlaceholderText("URL fixa de la tablet")

        self._qr_label = QLabel("")
        self._qr_label.setAlignment(Qt.AlignCenter)
        self._qr_label.setFixedSize(180, 180)
        self._qr_label.hide()

        self._btn_view = QPushButton("Obrir document signat")
        self._btn_delete = QPushButton("Eliminar document")
        self._btn_export = QPushButton("Desar PDF en…")
        self._btn_generate_qr = QPushButton("Generar URL + QR")
        self._btn_start = QPushButton("Enviar a tablet")
        self._btn_cancel = QPushButton("Cancel·lar firma pendent")
        self._btn_copy_link = QPushButton("Copiar enllaç")

        self._btn_view.clicked.connect(self._abrir_documento_guardado)
        self._btn_delete.clicked.connect(self._eliminar_documento)
        self._btn_export.clicked.connect(self._exportar_pdf)
        self._btn_generate_qr.clicked.connect(self._generar_url_qr)
        self._btn_start.clicked.connect(self._iniciar_firma)
        self._btn_cancel.clicked.connect(self._cancelar_firma_pendiente)
        self._btn_copy_link.clicked.connect(self._copiar_enlace)

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_header_box())
        layout.addWidget(self._build_signed_box())
        layout.addWidget(self._build_signature_box())
        layout.addStretch(1)

        self._btn_cancel.hide()
        self._btn_copy_link.setEnabled(False)

        self._load_socio_info()
        self._load_signature_status()

    # ------------------------------------------------------------------
    def _build_header_box(self) -> QGroupBox:
        box = QGroupBox("Soci seleccionat")
        ly = QVBoxLayout(box)
        info = consultar_socio(self._socio_id)
        if info:
            nombre = f"{info['nombre']} {info.get('apellido1', '') or ''} {info.get('apellido2', '') or ''}".strip()
            dni = info.get("dniNie", "")
            ly.addWidget(QLabel(f"<b>{nombre}</b> — DNI {dni}"))
        else:
            ly.addWidget(QLabel("No s'han pogut obtenir les dades del soci."))
        return box

    def _build_signed_box(self) -> QGroupBox:
        box = QGroupBox("Document signat")
        ly = QVBoxLayout(box)
        ly.addWidget(self._status_label)
        btns = QHBoxLayout()
        btns.addWidget(self._btn_view)
        btns.addWidget(self._btn_delete)
        btns.addStretch(1)
        ly.addLayout(btns)
        return box

    def _build_signature_box(self) -> QGroupBox:
        box = QGroupBox("Generar i firmar")
        ly = QVBoxLayout(box)
        ly.addWidget(QLabel("1. Pots desar una còpia del document en blanc per revisar-lo."))
        ly.addWidget(self._btn_export, alignment=Qt.AlignLeft)

        ly.addSpacing(8)
        ly.addWidget(QLabel("2. Mantingues aquesta URL oberta a la tablet i envia-hi el soci."))
        ly.addWidget(self._btn_generate_qr, alignment=Qt.AlignLeft)

        link_row = QHBoxLayout()
        link_row.addWidget(self._server_url, stretch=1)
        link_row.addWidget(self._btn_copy_link)
        ly.addLayout(link_row)
        ly.addWidget(self._qr_label, alignment=Qt.AlignLeft)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn_start)
        btn_row.addWidget(self._btn_cancel)
        btn_row.addStretch(1)
        ly.addLayout(btn_row)

        ly.addWidget(self._progress_label)
        return box

    # ------------------------------------------------------------------
    def _load_socio_info(self) -> None:
        """Placeholder per si es vol ampliar futurament."""
        return

    def _load_signature_status(self) -> None:
        info = consultar_firma_LOPD(self._socio_id)
        if info and info.get("fechaFirma"):
            fecha = info["fechaFirma"]
            fecha_txt = fecha.strftime("%d/%m/%Y")
            self._status_label.setText(f"Document signat el {fecha_txt}.")
            self._btn_view.setEnabled(True)
            self._btn_delete.setEnabled(True)
        elif info and info.get("tieneDocumento"):
            self._status_label.setText("Document registrat sense data.")
            self._btn_view.setEnabled(True)
            self._btn_delete.setEnabled(True)
        else:
            self._status_label.setText("No hi ha cap document signat.")
            self._btn_view.setEnabled(False)
            self._btn_delete.setEnabled(False)

    # ------------------------------------------------------------------
    def _exportar_pdf(self) -> None:
        suggested = f"lopd_{self._socio_id:06d}.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Desar PDF LOPD", suggested, "PDF (*.pdf)")
        if not path:
            return
        try:
            generar_pdf_LOPD(self._socio_id, path, abrir=True)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{exc}")

    def _abrir_documento_guardado(self) -> None:
        try:
            data, _fecha = obtener_documento_firma_LOPD(self._socio_id)
        except Exception as exc:
            QMessageBox.warning(self, "Error", str(exc))
            self._load_signature_status()
            return

        if self._ensure_tablet_server():
            self._server.set_completed_document(
                data,
                socio_id=self._socio_id,
                nombre=self._nombre_socio_actual(),
            )
            self._progress_label.setText("Document signat obert també a la tablet.")

        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(data)
        tmp.close()
        tmp_path = Path(tmp.name)
        self._temp_view_files.append(tmp_path)
        self._open_file(tmp_path)

    def _eliminar_documento(self) -> None:
        reply = QMessageBox.question(
            self,
            "Eliminar document",
            "Segur que vols eliminar el document signat?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            eliminar_documento_firma_LOPD(self._socio_id)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha eliminat el document:\n{exc}")
            return

        self._load_signature_status()
        QMessageBox.information(self, "Document eliminat", "El document s'ha eliminat correctament.")

    # ------------------------------------------------------------------
    def _iniciar_firma(self) -> None:
        self._cleanup_temp_pdf()
        try:
            base_path = self._generar_pdf_temporal()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut preparar el PDF:\n{exc}")
            return

        self._server_pdf = Path(base_path)
        try:
            if not self._ensure_tablet_server():
                raise RuntimeError("El servidor de la tablet no està disponible")
            socio = consultar_socio(self._socio_id) or {}
            self._active_token = self._server.set_active_signature(
                pdf_path=base_path,
                socio_id=self._socio_id,
                nombre=self._nombre_socio_actual(socio),
                dni=socio.get("dniNie", "") or "",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut enviar el soci a la tablet:\n{exc}")
            self._cleanup_temp_pdf()
            return

        self._progress_label.setText("Soci enviat a la tablet. Esperant la signatura.")
        self._btn_start.setEnabled(False)
        self._btn_cancel.show()
        self._btn_cancel.setEnabled(True)
        self._timer.start()

    def _generar_url_qr(self) -> None:
        if not self._ensure_tablet_server():
            QMessageBox.critical(self, "Error", "No s'ha pogut generar la URL i el QR de la tablet.")
            return
        self._progress_label.setText("URL i QR generats. Escaneja el QR amb la tablet.")

    def _ensure_tablet_server(self) -> bool:
        try:
            self._server.ensure_running()
        except Exception as exc:
            self._server_url.clear()
            self._btn_copy_link.setEnabled(False)
            self._progress_label.setText(f"No s'ha pogut iniciar la tablet de firma: {exc}")
            return False

        url = self._server.connection_url()
        if url:
            self._server_url.setText(url)
            self._btn_copy_link.setEnabled(True)
            self._update_qr_url(url)
            self._timer.start()
        else:
            self._server_url.setText("http://localhost")
            self._btn_copy_link.setEnabled(False)
            self._clear_qr()
        return True

    def _detener_server(self) -> None:
        self._timer.stop()
        self._server.stop()
        self._cleanup_temp_pdf()
        self._active_token = None
        self._server_url.clear()
        self._btn_copy_link.setEnabled(False)
        self._clear_qr()
        self._btn_start.setEnabled(True)
        self._btn_cancel.hide()
        self._progress_label.clear()

    def _cancelar_firma_pendiente(self) -> None:
        self._server.clear_active_signature()
        self._server.clear_completed_document()
        self._cleanup_temp_pdf()
        self._active_token = None
        self._btn_start.setEnabled(True)
        self._btn_cancel.hide()
        self._progress_label.setText("Firma pendent cancel·lada. La tablet queda en espera.")

    def _copiar_enlace(self) -> None:
        if not self._server_url.text():
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._server_url.text())
        self._progress_label.setText("Enllaç copiat al porta-retalls.")

    def _update_qr_url(self, url: str) -> None:
        pixmap = _build_qr_pixmap(url, self._qr_label.width())
        self._qr_label.setPixmap(
            pixmap.scaled(
                self._qr_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self._qr_label.show()

    def _clear_qr(self) -> None:
        self._qr_label.clear()
        self._qr_label.hide()

    # ------------------------------------------------------------------
    def _generar_pdf_temporal(self) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        generar_pdf_LOPD(self._socio_id, tmp.name, abrir=False)
        return tmp.name

    def _poll_signature_queue(self) -> None:
        if not self._server.running:
            return
        q = self._server.queue
        try:
            payload = q.get_nowait()
        except queue.Empty:
            return

        if payload.get("type") != "signature":
            return
        if self._active_token and payload.get("token") != self._active_token:
            return

        signature_bytes = payload.get("image")
        if not isinstance(signature_bytes, (bytes, bytearray)):
            return

        self._timer.stop()
        self._progress_label.setText("Signatura rebuda. Processant…")

        try:
            signed_pdf = self._guardar_signatura(bytes(signature_bytes))
            self._server.set_completed_document(
                signed_pdf,
                socio_id=self._socio_id,
                nombre=self._nombre_socio_actual(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut guardar la signatura:\n{exc}")
        finally:
            self._cleanup_temp_pdf()
            self._active_token = None
            self._btn_start.setEnabled(True)
            self._btn_cancel.hide()
            self._progress_label.setText("Signatura rebuda i guardada. La tablet queda en espera.")
            if self._server.running:
                self._timer.start()
            self._load_signature_status()

    def _guardar_signatura(self, signature: bytes) -> bytes:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        tmp_path = Path(tmp.name)

        datos = b""
        try:
            generar_pdf_LOPD(
                self._socio_id,
                tmp.name,
                abrir=False,
                firma=signature,
                fechaFirma=date.today(),
            )
            with tmp_path.open("rb") as fh:
                datos = fh.read()
            guardar_documento_firma_LOPD(self._socio_id, datos, date.today())
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

        QMessageBox.information(self, "Signatura enregistrada", "S'ha registrat i guardat la signatura.")
        return datos

    def _nombre_socio_actual(self, socio: dict | None = None) -> str:
        if socio is None:
            socio = consultar_socio(self._socio_id) or {}
        return (
            f"{socio.get('nombre', '')} {socio.get('apellido1', '') or ''} "
            f"{socio.get('apellido2', '') or ''}"
        ).strip()

    def _cleanup_temp_pdf(self) -> None:
        if self._server_pdf and self._server_pdf.exists():
            try:
                self._server_pdf.unlink()
            except OSError:
                pass
        self._server_pdf = None

    def _open_file(self, path: Path) -> None:
        if not path.exists():
            return
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform.startswith("darwin"):
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')

    def closeEvent(self, event) -> None:  # noqa: N802
        self._detener_server()
        for path in list(self._temp_view_files):
            if path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
        self._temp_view_files.clear()
        super().closeEvent(event)
