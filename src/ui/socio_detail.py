from __future__ import annotations
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDateEdit, QTextEdit,
    QPushButton, QLabel, QFileDialog, QHBoxLayout, QMessageBox, QCheckBox
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QDate, Signal

from controladores.socios import (
    consultar_socio, modificar_socio, adjuntar_foto_socio, registrar_socio
)


class SocioDetailWidget(QWidget):
    """Panell lateral de detall i edició auto-guardada."""
    saved = Signal()  # Sinal per notificar que s'ha guardat un soci

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._id: int | None = None
        self._foto_path: str | None = None   # ruta temporal de la nova foto
        # ── widgets ──
        self.dni = QLineEdit(); self.nom = QLineEdit()
        self.c1 = QLineEdit();  self.c2 = QLineEdit()
        self.dir = QLineEdit()
        self.tf = QLineEdit();  self.tm = QLineEdit()
        self.email = QLineEdit(); self.grup = QLineEdit()
        self.fe_alta = QDateEdit(); self.fe_alta.setCalendarPopup(True)
        self.fe_baixa = QDateEdit(); self.fe_baixa.setCalendarPopup(True)
        self.cb_baixa = QCheckBox("Baixa")
        self.cb_baixa.toggled.connect(self._toggle_baixa)
        self.fe_baixa.setEnabled(False)              # per defecte desactivat
        self.obs = QTextEdit()

        self.preview = QLabel(); self.preview.setFixedSize(100, 120)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("border:1px solid #888;")
        btn_foto = QPushButton("Canviar\nFoto")
        btn_foto.clicked.connect(self._canviar_foto)
        foto_box = QHBoxLayout()
        foto_box.addWidget(self.preview)
        foto_box.addSpacing(12)                 # espai entre la foto i el botó
        foto_box.addWidget(btn_foto)
        foto_box.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        

        # ── layout ──
        f = QFormLayout(self)
        f.addRow("Foto:", foto_box)
        f.addRow("DNI/NIE*:", self.dni)
        f.addRow("Nom*:", self.nom)
        f.addRow("1r Cognom*:", self.c1); f.addRow("2n Cognom:", self.c2)
        f.addRow("Adreça:", self.dir)
        f.addRow("Tel. fix:", self.tf);   f.addRow("Tel. mòbil:", self.tm)
        f.addRow("Email:", self.email);   f.addRow("Grup:", self.grup)
        f.addRow("Data alta:", self.fe_alta)
        baixa_box = QHBoxLayout()
        baixa_box.addWidget(self.cb_baixa)
        baixa_box.addWidget(self.fe_baixa)
        baixa_box.addStretch()
        f.addRow("Data baixa:", baixa_box)
        f.addRow("Observacions:", self.obs)

        # -- connexions per autoguardar --
        for w in (self.dni, self.nom, self.c1, self.c2, self.dir,
                  self.tf, self.tm, self.email, self.grup):
            w.editingFinished.connect(self._guardar)
        self.fe_alta.dateChanged.connect(self._guardar)
        self.fe_baixa.dateChanged.connect(self._guardar)
        self.obs.textChanged.connect(self._guardar)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def load(self, socio_id: int | None):
        """Carrega dades del soci; si None, buida."""
        self._loading = True
        self._id = socio_id
        if socio_id is None:
            self._clear()
            self._loading = False
            return

        s = consultar_socio(socio_id)
        if not s:
            self._clear(); self._loading = False; return
        # assigna
        self.dni.setText(s["dni_nie"]);   self.nom.setText(s["nombre"])
        self.c1.setText(s.get("apellido1", "") or ""); self.c2.setText(s.get("apellido2", "") or "")
        self.dir.setText(s.get("direccion", "") or "")
        self.tf.setText(s.get("telefonoFijo", "") or ""); self.tm.setText(s.get("telefonoMovil", "") or "")
        self.email.setText(s.get("email", "") or ""); self.grup.setText(s.get("grupoDifusion", "") or "")
        if s.get("fechaAlta"):
            self.fe_alta.setDate(QDate.fromString(str(s["fechaAlta"]), "yyyy-MM-dd"))
        else:
            self.fe_alta.setDate(QDate())
        if s.get("fechaBaja"):
            self.cb_baixa.setChecked(True)
            self.fe_baixa.setEnabled(True)
            self.fe_baixa.setDate(QDate.fromString(str(s["fechaBaja"]), "yyyy-MM-dd"))
        else:
            self.cb_baixa.setChecked(False)
            self.fe_baixa.setEnabled(False)
            self.fe_baixa.setDate(QDate())
        self.obs.setPlainText(s.get("observaciones", "") or "")

        if s.get("foto"):
            pix = QPixmap(); pix.loadFromData(s["foto"])
            self.preview.setPixmap(pix.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview.setPixmap(QPixmap())
        self._loading = False

    # ------------------------------------------------------------------
    def _clear(self):
        for w in (self.dni, self.nom, self.c1, self.c2, self.dir, self.tf,
                  self.tm, self.email, self.grup): w.clear()
        self.fe_alta.clear(); self.fe_baixa.clear(); self.obs.clear()
        self.cb_baixa.setChecked(False)
        self.fe_baixa.setEnabled(False)
        self.preview.setPixmap(QPixmap())

    def _toggle_baixa(self, checked: bool):
        """Activa o desactiva el camp Data baixa.

        • Si es marca, omple per defecte amb la data d'avui.
        • Si es desmarca, es buida i es deshabilita.
        """
        self.fe_baixa.setEnabled(checked)
        if checked:
            self.fe_baixa.setDate(QDate.currentDate())
        else:
            self.fe_baixa.clear()
        self._guardar()      # autoguarda canvi de baixa


    def _canviar_foto(self):
        if self._id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona foto", "", "Imatges (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        self._foto_path = path
        adjuntar_foto_socio(self._id, path)
        pix = QPixmap(path).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pix)
        self.saved.emit()
     # ─────────────────────────────────────────────────────────
    # Guardar
    # ─────────────────────────────────────────────────────────
    def _validar(self) -> bool:
        if not self.dni.text().strip() or not self.nom.text().strip():
            QMessageBox.warning(self, "Error",
                                "Els camps marcats amb * són obligatoris.")
            return False
        return True

    def _build_data(self) -> dict:
        data = {
            "dni_nie": self.dni.text().strip(),
            "nombre": self.nom.text().strip(),
            "apellido1": self.c1.text().strip(),
            "apellido2": self.c2.text().strip() or None,
            "direccion": self.dir.text().strip() or None,
            "telefonoFijo": self.tf.text().strip() or None,
            "telefonoMovil": self.tm.text().strip() or None,
            "email": self.email.text().strip() or None,
            "grupoDifusion": self.grup.text().strip() or None,
            "fechaAlta": self.fe_alta.date().toPython() or date.today(),
            "fechaBaja": (
                self.fe_baixa.date().toPython() or date.today()
                if self.cb_baixa.isChecked() and self.fe_baixa.date().isValid()
                else None
            ),
            "observaciones": self.obs.toPlainText() or None,
        }
        # Només afegim la foto si l'usuari n'ha seleccionat una de nova
        if self._foto_path:
            with open(self._foto_path, "rb") as fh:
                data["foto"] = fh.read()
        return data

    def _guardar(self):
        # No fem res si estem carregant o no hi ha cap soci seleccionat
        if self._loading or self._id is None:
            return

        if not self._validar():
            return

        data = self._build_data()
        try:
            modificar_socio(self._id, data)
            self._foto_path = None          # reset because it's saved
            self.saved.emit()               # notifica MainWindow per refrescar taula
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        # Widget no és QDialog; no cal accept()
