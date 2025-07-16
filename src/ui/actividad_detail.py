from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QDateEdit, QSpinBox, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, QDate
from controladores.actividades import consultar_actividad, modificar_actividad

class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self._actividadID = None
        self._tipo = tipo.lower()
        self._loading = False

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.fechaInicio = QDateEdit(); self.fechaInicio.setCalendarPopup(True)
        self.fechaFin = QDateEdit(); self.fechaFin.setCalendarPopup(True)
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(0)
        self.numMaxAlumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Data inici:", self.fechaInicio)
        form.addRow("Data fi:", self.fechaFin)
        form.addRow("Màxim alumnes:", self.numMaxAlumnos)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch()

        self.nombre.editingFinished.connect(self._save)
        self.descripcion.editingFinished.connect(self._save)
        self.fechaInicio.dateChanged.connect(self._save)
        self.fechaFin.dateChanged.connect(self._save)
        self.numMaxAlumnos.valueChanged.connect(self._save)

    def load(self, actividadID):
        self._loading = True
        self._actividadID = actividadID

        if actividadID is None:
            self._clear()
            self._loading = False
            return

        act = consultar_actividad(actividadID)
        if not act:
            QMessageBox.warning(self, "Error", "Activitat no trobada.")
            self._clear()
            self._loading = False
            return

        self.nombre.setText(act.get("nombre", ""))
        self.descripcion.setText(
            act.get("descripcion") or act.get("descripcion_actividad") or ""
        )
        if act.get("fechaInicio"):
            self.fechaInicio.setDate(QDate.fromString(str(act["fechaInicio"]), "yyyy-MM-dd"))
        else:
            self.fechaInicio.setDate(QDate())
        if act.get("fechaFin"):
            self.fechaFin.setDate(QDate.fromString(str(act["fechaFin"]), "yyyy-MM-dd"))
        else:
            self.fechaFin.setDate(QDate())

        max_alumnos = act.get("numMaxAlumnos")
        if max_alumnos is None:
            max_alumnos = act.get("max_alumnos")
        if max_alumnos is not None:
            self.numMaxAlumnos.setValue(max_alumnos)
        else:
            self.numMaxAlumnos.setValue(1)
        self._loading = False

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.fechaInicio.setDate(QDate())
        self.fechaFin.setDate(QDate())
        self.numMaxAlumnos.setValue(0)

    def _validar(self) -> bool:
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El camp 'Nom' és obligatori.")
            return False
        return True

    def _build_data(self) -> dict:
        return {
            "nombre": self.nombre.text().strip(),
            "tipo": self._tipo,
            "descripcion": self.descripcion.text().strip() or None,
            "fechaInicio": self.fechaInicio.date().toPython() if self.fechaInicio.date().isValid() else None,
            "fechaFin": self.fechaFin.date().toPython() if self.fechaFin.date().isValid() else None,
            "max_alumnos": self.numMaxAlumnos.value(),
        }

    def _save(self):
        if self._loading or self._actividadID is None:
            return

        if not self._validar():
            QMessageBox.warning(self, "Error", "Dades incompletes o incorrectes.")
            return  
            

        data = self._build_data()
        try:
            modificar_actividad(self._actividadID, data)
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))