from __future__ import annotations

import os
import queue
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
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


class LOPDFirmaDialog(QDialog):
    """Gestor complet del document LOPD d'un soci."""

    def __init__(self, socio_id: int, parent=None) -> None:
        super().__init__(parent)
        self._socio_id = socio_id
        self._server = SignatureServer()
        self._server_pdf: Optional[Path] = None
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
        self._server_url.setPlaceholderText("Enllaç de firma (s'activarà en iniciar)")

        self._btn_view = QPushButton("Obrir document signat")
        self._btn_delete = QPushButton("Eliminar document")
        self._btn_export = QPushButton("Desar PDF en…")
        self._btn_start = QPushButton("Iniciar firma digital")
        self._btn_cancel = QPushButton("Cancel·lar firma")
        self._btn_copy_link = QPushButton("Copiar enllaç")

        self._btn_view.clicked.connect(self._abrir_documento_guardado)
        self._btn_delete.clicked.connect(self._eliminar_documento)
        self._btn_export.clicked.connect(self._exportar_pdf)
        self._btn_start.clicked.connect(self._iniciar_firma)
        self._btn_cancel.clicked.connect(self._detener_server)
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
        ly.addWidget(QLabel("2. Inicia la firma digital per a dispositius mòbils."))

        link_row = QHBoxLayout()
        link_row.addWidget(self._server_url, stretch=1)
        link_row.addWidget(self._btn_copy_link)
        ly.addLayout(link_row)

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
        try:
            base_path = self._generar_pdf_temporal()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut preparar el PDF:\n{exc}")
            return

        try:
            self._server.start(base_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut iniciar el servidor de firma:\n{exc}")
            self._cleanup_temp_pdf()
            return

        self._server_pdf = Path(base_path)
        url = self._server.connection_url()
        if url:
            self._server_url.setText(url)
            self._btn_copy_link.setEnabled(True)
        else:
            self._server_url.setText("http://localhost")
            self._btn_copy_link.setEnabled(False)

        self._progress_label.setText("Servidor actiu. Obre l'enllaç al mòbil i signa al requadre.")
        self._btn_start.setEnabled(False)
        self._btn_cancel.show()
        self._btn_cancel.setEnabled(True)
        self._timer.start()

    def _detener_server(self) -> None:
        self._timer.stop()
        self._server.stop()
        self._cleanup_temp_pdf()
        self._server_url.clear()
        self._btn_copy_link.setEnabled(False)
        self._btn_start.setEnabled(True)
        self._btn_cancel.hide()
        self._progress_label.clear()

    def _copiar_enlace(self) -> None:
        if not self._server_url.text():
            return
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._server_url.text())
        self._progress_label.setText("Enllaç copiat al porta-retalls.")

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

        signature_bytes = payload.get("image")
        if not isinstance(signature_bytes, (bytes, bytearray)):
            return

        self._timer.stop()
        self._progress_label.setText("Signatura rebuda. Processant…")

        try:
            self._guardar_signatura(bytes(signature_bytes))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No s'ha pogut guardar la signatura:\n{exc}")
        finally:
            self._detener_server()
            self._load_signature_status()

    def _guardar_signatura(self, signature: bytes) -> None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.close()
        tmp_path = Path(tmp.name)

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
