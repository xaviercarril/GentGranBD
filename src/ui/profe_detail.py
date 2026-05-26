from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QVBoxLayout, QLabel, QMessageBox, QTextEdit, QTableView
)
from PySide6.QtCore import Qt, Signal
from controladores.personal import modificar_personal, consultar_personal, listar_actividades_por_Personal
from controladores.curso_academico import consultar_cursoA
from ui.table_models import DictTableModel

class ProfeDetailWidget(QWidget):
    """Panell lateral de detall i edició auto-guardada."""
    saved = Signal()  # Sinal per notificar que s'ha guardat un professor

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._id: int | None = None

        self.nom = QLineEdit()
        self.nom.setFixedWidth(300)
        self.cognom1 = QLineEdit()
        self.cognom1.setFixedWidth(300)
        self.cognom2 = QLineEdit()
        self.cognom2.setFixedWidth(300)
        self.email = QLineEdit()
        self.email.setFixedWidth(300)
        self.tel_mob = QLineEdit()
        self.tel_mob.setFixedWidth(300)
        self.obs = QTextEdit()

        # ── Disseny ──────────────────────────────────────────
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        form.addRow("Nom*:", self.nom)
        form.addRow("1r Cognom*:", self.cognom1)
        form.addRow("2n Cognom:", self.cognom2)
        form.addRow("Email:", self.email)
        form.addRow("Tel. mòbil:", self.tel_mob)
        form.addRow("Observacions:", self.obs)

        self.label_imparteix = QLabel("Activitats que imparteix:")
        self.imparteix_table = QTableView()
        self.imparteix_table.verticalHeader().setVisible(False)
        self.imparteix_table.setSelectionBehavior(QTableView.SelectRows)
        self.imparteix_table.setSelectionMode(QTableView.NoSelection)
        self.imparteix_table.setAlternatingRowColors(True)

        layout.addLayout(form)
        layout.addWidget(self.label_imparteix)
        layout.addWidget(self.imparteix_table)
        layout.addStretch()

        for widget in [self.nom, self.cognom1, self.cognom2, self.email, self.tel_mob]:
            widget.editingFinished.connect(self._guardar)
        self.obs.textChanged.connect(self._guardar)

    def load(self, profeID: int):
        """Load professor data by ID."""
        self._loading = True
        self._id = profeID
        if profeID is None:
            self._clear(); self._loading = False; return
        
        profe = consultar_personal(profeID)
        if not profe:
            self._clear(); self._loading = False; return

        if hasattr(profe, "model_dump"):
            profe = profe.model_dump()

        self.nom.setText(profe.get("nombre", ""))
        self.cognom1.setText(profe.get("apellido1", ""))
        self.cognom2.setText(profe.get("apellido2", ""))
        self.email.setText(profe.get("email", ""))
        self.tel_mob.setText(profe.get("telfMovil", ""))
        self.obs.setText(profe.get("observaciones", ""))

        self._load_imparteix_table()
        self._loading = False

    def _clear(self):
        """Clear all fields."""
        self._loading = True
        self._id = None
        self.nom.clear()
        self.cognom1.clear()
        self.cognom2.clear()
        self.email.clear()
        self.tel_mob.clear()
        self.obs.clear()
        self.imparteix_table.setModel(DictTableModel([], []))
        self._loading = False

    # ------------------------------------------------------------------
    # Guardar
    # ------------------------------------------------------------------
    def _validar(self) -> bool:
        if not self.nom.text().strip() or not self.cognom1.text().strip():
            QMessageBox.warning(self, "Error",
                                "Els camps marcats amb * són obligatoris.")
            return False
        return True
    
    def _build_data(self) -> dict:
        data = {
            "nombre": self.nom.text().strip(),
            "apellido1": self.cognom1.text().strip(),
            "apellido2": self.cognom2.text().strip() or None,
            "email": self.email.text().strip() or None,
            "telfMovil": self.tel_mob.text().strip() or None,
            "observaciones": self.obs.toPlainText().strip() or None,
        }
        return data
    
    def _guardar(self):
        # No fem res si estem carregant o no hi ha cap soci seleccionat
        if self._loading or self._id is None:
            return
        
        if not self._validar():
            return

        data = self._build_data()
        try:
            modificar_personal(self._id, data)
            self.saved.emit()  # Emit saved signal if needed
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'han pogut guardar les dades: {e}")

    def _load_imparteix_table(self):
        """Load activities taught by this professor."""
        try:

            actividades = listar_actividades_por_Personal(self._id)
            headers = [
                ("Nom", "nombre"),
                ("Curs Acadèmic", "cursoAcademico")
            ]
            for actividad in actividades:
                cursoAcademicoID = actividad.get("cursoAcademico_id")
                cursoAcademico = consultar_cursoA(cursoAcademicoID)
                actividad["cursoAcademico"] = cursoAcademico.get("nombre", "Desconegut")
                actividad["nombre"] = actividad.get("nombre", "Desconegut")
            self.imparteix_table.setModel(DictTableModel(actividades, headers))
            self.imparteix_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut carregar les activitats: {e}")
