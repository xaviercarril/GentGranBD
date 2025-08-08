from __future__ import annotations

import os
import tempfile
from datetime import date

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QWidget,
)

from controladores.firma_LOPD import (
    consultar_firma_lopd,
    eliminar_firma_lopd,
    guardar_firma_lopd,
)
from controladores.socios import generar_pdf_LOPD, consultar_socio


class SignaturePad(QWidget):
    """Widget senzill per capturar una signatura amb el dit o ratolí."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(400, 200)
        self.image = QImage(self.size(), QImage.Format_RGB32)
        self.image.fill(Qt.white)
        self.last_point = QPoint()

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.last_point = event.position().toPoint()

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if event.buttons() & Qt.LeftButton:
            painter = QPainter(self.image)
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.position().toPoint())
            self.last_point = event.position().toPoint()
            self.update()

    def paintEvent(self, event):  # type: ignore[override]
        painter = QPainter(self)
        painter.drawImage(self.rect(), self.image, self.image.rect())

    def clear(self) -> None:
        self.image.fill(Qt.white)
        self.update()


class FirmaLOPDDialog(QDialog):
    """Dialog per gestionar la firma del document LOPD."""

    def __init__(self, socio_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.socio_id = socio_id
        self.setWindowTitle("Firma LOPD")

        self.signature = SignaturePad()

        btn_leer = QPushButton("Llegir document")
        btn_firmar = QPushButton("Guardar signatura")
        btn_veure = QPushButton("Veure signat")
        btn_eliminar = QPushButton("Eliminar signat")
        btn_tancar = QPushButton("Tancar")

        btn_leer.clicked.connect(self._leer)
        btn_firmar.clicked.connect(self._guardar)
        btn_veure.clicked.connect(self._veure)
        btn_eliminar.clicked.connect(self._eliminar)
        btn_tancar.clicked.connect(self.accept)

        hlayout = QHBoxLayout()
        hlayout.addWidget(btn_leer)
        hlayout.addWidget(btn_firmar)
        hlayout.addWidget(btn_veure)
        hlayout.addWidget(btn_eliminar)
        hlayout.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(hlayout)
        layout.addWidget(self.signature)
        layout.addWidget(btn_tancar, alignment=Qt.AlignRight)

        self._refresh_buttons()

    # ------------------------------------------------------------------
    # Helpers
    def _ruta_temp_pdf(self) -> str:
        fd, path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        return path

    def _ruta_temp_img(self) -> str:
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        return path

    def _leer(self) -> None:
        socio = consultar_socio(self.socio_id)
        if not socio:
            QMessageBox.warning(self, "Error", "Soci inexistent")
            return
        ruta = self._ruta_temp_pdf()
        generar_pdf_LOPD(self.socio_id, ruta)

    def _guardar(self) -> None:
        # Guardar signatura en imatge temporal
        img_path = self._ruta_temp_img()
        self.signature.image.save(img_path)

        socio = consultar_socio(self.socio_id)
        if not socio:
            QMessageBox.warning(self, "Error", "Soci inexistent")
            return

        pdf_path = self._ruta_temp_pdf()
        from exportador.pdf_LOPD import generar_pdf_lopd

        nombre = f"{socio['nombre']} {socio.get('apellido1', '')} {socio.get('apellido2', '')}".strip()
        generar_pdf_lopd(nombre, socio["dniNie"], pdf_path, firma_path=img_path)

        with open(pdf_path, "rb") as fh:
            pdf_bytes = fh.read()

        guardar_firma_lopd(self.socio_id, pdf_bytes, date.today())
        QMessageBox.information(self, "Èxit", "Document firmat correctament")
        self.signature.clear()
        self._refresh_buttons()

    def _veure(self) -> None:
        firma = consultar_firma_lopd(self.socio_id)
        if not firma:
            QMessageBox.information(self, "Informació", "No hi ha document signat")
            return
        ruta = self._ruta_temp_pdf()
        with open(ruta, "wb") as fh:
            fh.write(firma["documento"])
        os.system(f'xdg-open "{ruta}"')

    def _eliminar(self) -> None:
        if QMessageBox.question(
            self,
            "Confirmació",
            "Vols eliminar el document signat?",
        ) != QMessageBox.Yes:
            return

        eliminar_firma_lopd(self.socio_id)
        QMessageBox.information(self, "Eliminat", "Document eliminat")
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        # habilitar/deshabilitar veure/eliminar segons hi haja firma
        firma = consultar_firma_lopd(self.socio_id)
        has_doc = bool(firma)
        for btn in self.findChildren(QPushButton):
            if btn.text().startswith("Veure") or btn.text().startswith("Eliminar"):
                btn.setEnabled(has_doc)

