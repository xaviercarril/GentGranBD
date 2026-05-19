from __future__ import annotations
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDateEdit, QTextEdit,
    QPushButton, QLabel, QFileDialog, QHBoxLayout, QMessageBox, QCheckBox
)
from PySide6.QtGui import QPixmap, QIntValidator
from PySide6.QtCore import Qt, QDate, Signal

from controladores.socios import (
    consultar_socio, modificar_socio
)


EMPTY_DATE = QDate(1900, 1, 1)


class SocioDetailWidget(QWidget):
    """Panell lateral de detall i edició del soci seleccionat."""
    saved = Signal(int)  # Sinal per notificar quin soci s'ha guardat

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._dirty = False
        self._id: int | None = None
        self._foto_path: str | None = None   # ruta temporal de la nova foto
        # ── widgets ──
        self.id_field = QLineEdit()
        self.id_field.setFixedWidth(300)
        self.id_field.setPlaceholderText("S'assigna automàticament si es deixa en blanc")
        self.id_field.setValidator(QIntValidator(0, 999999999, self))
        self.dni = QLineEdit()
        self.dni.setFixedWidth(300)
        self.nom = QLineEdit()
        self.nom.setFixedWidth(300)
        self.c1 = QLineEdit()
        self.c1.setFixedWidth(300)
        self.c2 = QLineEdit()
        self.c2.setFixedWidth(300)
        self.dir = QLineEdit()
        self.dir.setFixedWidth(300)
        self.tf = QLineEdit()
        self.tf.setFixedWidth(300)
        self.tm = QLineEdit()
        self.tm.setFixedWidth(300)
        self.email = QLineEdit()
        self.email.setFixedWidth(300)
        self.grup = QLineEdit()
        self.grup.setFixedWidth(300)
        self.fe_naixement = QDateEdit(); self.fe_naixement.setCalendarPopup(True)
        self.fe_naixement.setDisplayFormat("dd/MM/yyyy")
        self.fe_naixement.setMinimumDate(EMPTY_DATE)
        self.fe_naixement.setSpecialValueText("")
        self.fe_naixement.setDate(EMPTY_DATE)
        self.fe_alta = QDateEdit(); self.fe_alta.setCalendarPopup(True)
        self.fe_baixa = QDateEdit(); self.fe_baixa.setCalendarPopup(True)
        self.cb_baixa = QCheckBox("Baixa")
        self.cb_baixa.toggled.connect(self._toggle_baixa)
        if self.fe_baixa is None:
            self.cb_baixa.setChecked(False)
            self.fe_baixa.setEnabled(False)              # per defecte desactivat
        else:
            self.cb_baixa.setChecked(True)
            self.fe_baixa.setEnabled(True)               # si hi ha baixa, activat
        self.obs = QTextEdit()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")

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
        f.addRow("ID soci:", self.id_field)
        f.addRow("DNI/NIE*:", self.dni)
        f.addRow("Nom*:", self.nom)
        f.addRow("1r Cognom*:", self.c1); f.addRow("2n Cognom:", self.c2)
        f.addRow("Adreça:", self.dir)
        f.addRow("Tel. fix:", self.tf);   f.addRow("Tel. mòbil:", self.tm)
        f.addRow("Email:", self.email);   f.addRow("Grup:", self.grup)
        f.addRow("Data naixement:", self.fe_naixement)
        f.addRow("Data alta:", self.fe_alta)
        baixa_box = QHBoxLayout()
        baixa_box.addWidget(self.cb_baixa)
        baixa_box.addWidget(self.fe_baixa)
        baixa_box.addStretch()
        f.addRow("Data baixa:", baixa_box)
        f.addRow("Observacions:", self.obs)

        self.btn_guardar = QPushButton("Guardar")
        self.btn_descartar = QPushButton("Descartar")
        self.btn_guardar.setEnabled(False)
        self.btn_descartar.setEnabled(False)
        self.btn_guardar.clicked.connect(lambda: self._guardar())
        self.btn_descartar.clicked.connect(self.descartar_cambios)
        actions_box = QHBoxLayout()
        actions_box.addWidget(self.btn_guardar)
        actions_box.addWidget(self.btn_descartar)
        actions_box.addStretch()
        f.addRow("", actions_box)
        f.addRow("", self.status_label)

        # -- connexions per marcar canvis pendents --
        for w in (self.dni, self.nom, self.c1, self.c2, self.dir,
                  self.tf, self.tm, self.email, self.grup):
            w.textChanged.connect(self._mark_dirty)
        self.id_field.textChanged.connect(self._mark_dirty)
        self.fe_naixement.dateChanged.connect(self._mark_dirty)
        self.fe_alta.dateChanged.connect(self._mark_dirty)
        self.fe_baixa.dateChanged.connect(self._mark_dirty)
        self.cb_baixa.toggled.connect(self._mark_dirty)
        self.obs.textChanged.connect(self._mark_dirty)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def load(self, socioID: int | None):
        """Carrega dades del soci; si None, buida."""
        self._loading = True
        self._id = socioID
        self._foto_path = None
        if socioID is None:
            self._clear()
            self._loading = False
            self._set_dirty(False)
            return

        s = consultar_socio(socioID)
        if not s:
            self._clear(); self._loading = False; self._set_dirty(False); return
        # assigna
        self._id = s.get("id", socioID)
        if self._id is not None:
            self.id_field.setText(str(self._id))
        else:
            self.id_field.clear()
        self.dni.setText(s["dniNie"]);   self.nom.setText(s["nombre"])
        self.c1.setText(s.get("apellido1", "") or ""); self.c2.setText(s.get("apellido2", "") or "")
        self.dir.setText(s.get("direccion", "") or "")
        self.tf.setText(s.get("telefonoFijo", "") or ""); self.tm.setText(s.get("telefonoMovil", "") or "")
        self.email.setText(s.get("email", "") or ""); self.grup.setText(s.get("grupoDifusion", "") or "")
        if s.get("fechaNacimiento") is not None:
            self.fe_naixement.setDate(QDate(s["fechaNacimiento"].year, s["fechaNacimiento"].month, s["fechaNacimiento"].day))
        else:
            self.fe_naixement.setDate(EMPTY_DATE)
        if s.get("fechaAlta") is not None:
            self.fe_alta.setDate(QDate(s["fechaAlta"].year, s["fechaAlta"].month, s["fechaAlta"].day))
        else:
            self.fe_alta.setDate(QDate())
        if s.get("fechaBaja"):
            self.cb_baixa.setChecked(True)
            self.fe_baixa.setEnabled(True)
            self.fe_baixa.setDate(QDate(s["fechaBaja"].year, s["fechaBaja"].month, s["fechaBaja"].day))
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
        self._set_dirty(False)

    # ------------------------------------------------------------------
    def _clear(self):
        for w in (self.dni, self.nom, self.c1, self.c2, self.dir, self.tf,
                  self.tm, self.email, self.grup): w.clear()
        self.id_field.clear()
        self.fe_naixement.setDate(EMPTY_DATE); self.fe_alta.clear(); self.fe_baixa.clear(); self.obs.clear()
        self.cb_baixa.setChecked(False)
        self.fe_baixa.setEnabled(False)
        self.preview.setPixmap(QPixmap())
        self.status_label.clear()
        self.btn_guardar.setEnabled(False)
        self.btn_descartar.setEnabled(False)

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


    def _canviar_foto(self):
        if self._id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona foto", "", "Imatges (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        self._foto_path = path
        pix = QPixmap(path).scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pix)
        self._mark_dirty()

    def has_pending_changes(self) -> bool:
        return self._dirty

    def descartar_cambios(self):
        if self._id is None:
            self._set_dirty(False)
            return
        self.load(self._id)

    def confirm_pending_changes(self, emit_saved: bool = True) -> bool:
        if not self.has_pending_changes():
            return True

        box = QMessageBox(self)
        box.setWindowTitle("Canvis sense guardar")
        box.setText("Hi ha canvis sense guardar. Què vols fer?")
        guardar = box.addButton("Guardar", QMessageBox.AcceptRole)
        descartar = box.addButton("Descartar", QMessageBox.DestructiveRole)
        cancelar = box.addButton("Cancel·lar", QMessageBox.RejectRole)
        box.setDefaultButton(guardar)
        box.exec()

        clicked = box.clickedButton()
        if clicked == guardar:
            return self._guardar(emit_saved=emit_saved)
        if clicked == descartar:
            self._set_dirty(False)
            return True
        if clicked == cancelar:
            return False
        return False

    def _mark_dirty(self):
        if self._loading or self._id is None:
            return
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool):
        self._dirty = dirty
        self.btn_guardar.setEnabled(dirty and self._id is not None)
        self.btn_descartar.setEnabled(dirty and self._id is not None)
        if dirty:
            self.status_label.setText("Canvis pendents.")
        elif self._id is None:
            self.status_label.clear()
        else:
            self.status_label.clear()
     # ─────────────────────────────────────────────────────────
    # Guardar
    # ─────────────────────────────────────────────────────────
    def _validar(self) -> bool:
        if not self.dni.text().strip() or not self.nom.text().strip() or not self.c1.text().strip():
            QMessageBox.warning(self, "Error",
                                "Els camps marcats amb * són obligatoris.")
            return False
        return True

    def _build_data(self) -> dict:
        data = {
            "dniNie": self.dni.text().strip(),
            "nombre": self.nom.text().strip(),
            "apellido1": self.c1.text().strip(),
            "apellido2": self.c2.text().strip() or None,
            "direccion": self.dir.text().strip() or None,
            "telefonoFijo": self.tf.text().strip() or None,
            "telefonoMovil": self.tm.text().strip() or None,
            "email": self.email.text().strip() or None,
            "grupoDifusion": self.grup.text().strip() or None,
            "fechaNacimiento": (
                self.fe_naixement.date().toPython()
                if self.fe_naixement.date() != EMPTY_DATE
                else None
            ),
            "fechaAlta": self.fe_alta.date().toPython() or date.today(),
            "fechaBaja": (
                self.fe_baixa.date().toPython() or date.today()
                if self.cb_baixa.isChecked() and self.fe_baixa.date().isValid()
                else None
            ),
            "observaciones": self.obs.toPlainText() or None,
        }
        id_text = self.id_field.text().strip()
        if id_text:
            try:
                valor_id = int(id_text)
                if valor_id <= 0:
                    raise ValueError("L'ID ha de ser un enter positiu.")
                data["id"] = valor_id
            except ValueError as exc:
                raise ValueError("L'ID ha de ser un número enter.") from exc
        elif self._id is not None:
            data["id"] = self._id
        # Només afegim la foto si l'usuari n'ha seleccionat una de nova
        if self._foto_path:
            with open(self._foto_path, "rb") as fh:
                data["foto"] = fh.read()
        return data

    def _guardar(self, emit_saved: bool = True):
        # No fem res si estem carregant o no hi ha cap soci seleccionat
        if self._loading or self._id is None:
            return True

        if not self._validar():
            return False

        try:
            data = self._build_data()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            if self._id is not None:
                self.id_field.setText(str(self._id))
            return False

        nou_id = data.get("id", self._id)
        try:
            modificar_socio(self._id, data)
            self._foto_path = None          # reset because it's saved
            if nou_id is not None:
                self._id = nou_id
                self.id_field.setText(str(nou_id))
            self._set_dirty(False)
            self.status_label.setText("Canvis guardats.")
            if emit_saved:
                self.saved.emit(self._id)   # notifica MainWindow per refrescar taula
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            if self._id is not None:
                self.id_field.setText(str(self._id))
            return False

        # Widget no és QDialog; no cal accept()
        return True
