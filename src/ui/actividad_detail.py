from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QDateEdit, QSpinBox, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, QDate
from controladores.actividades import consultar_actividad, modificar_actividad

class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, tipo, parent=None):
        super().__init__(parent)
        self._actividad_id = None
        self._tipo = tipo.lower()
        self._loading = False

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.fecha_inicio = QDateEdit(); self.fecha_inicio.setCalendarPopup(True)
        self.fecha_fin = QDateEdit(); self.fecha_fin.setCalendarPopup(True)
        self.numero_maximo_alumnos = QSpinBox()
        self.numero_maximo_alumnos.setMinimum(0)
        self.numero_maximo_alumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Data inici:", self.fecha_inicio)
        form.addRow("Data fi:", self.fecha_fin)
        form.addRow("Màxim alumnes:", self.numero_maximo_alumnos)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch()

        self.nombre.editingFinished.connect(self._save)
        self.descripcion.editingFinished.connect(self._save)
        self.fecha_inicio.dateChanged.connect(self._save)
        self.fecha_fin.dateChanged.connect(self._save)
        self.numero_maximo_alumnos.valueChanged.connect(self._save)

    def load(self, actividad_id):
        self._loading = True
        self._actividad_id = actividad_id

        if actividad_id is None:
            self._clear()
            self._loading = False
            return

        act = consultar_actividad(actividad_id)
        if not act:
            QMessageBox.warning(self, "Error", "Activitat no trobada.")
            self._clear()
            self._loading = False
            return

        self.nombre.setText(act.get("nombre", ""))
        self.descripcion.setText(
            act.get("descripcion") or act.get("descripcion_actividad") or ""
        )
        if act.get("fecha_inicio"):
            self.fecha_inicio.setDate(QDate.fromString(str(act["fecha_inicio"]), "yyyy-MM-dd"))
        else:
            self.fecha_inicio.setDate(QDate())
        if act.get("fecha_fin"):
            self.fecha_fin.setDate(QDate.fromString(str(act["fecha_fin"]), "yyyy-MM-dd"))
        else:
            self.fecha_fin.setDate(QDate())

        max_alumnos = act.get("numero_maximo_alumnos")
        if max_alumnos is None:
            max_alumnos = act.get("max_alumnos")
        if max_alumnos is not None:
            self.numero_maximo_alumnos.setValue(max_alumnos)
        else:
            self.numero_maximo_alumnos.setValue(1)
        self._loading = False

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.fecha_inicio.setDate(QDate())
        self.fecha_fin.setDate(QDate())
        self.numero_maximo_alumnos.setValue(0)

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
            "fecha_inicio": self.fecha_inicio.date().toPython() if self.fecha_inicio.date().isValid() else None,
            "fecha_fin": self.fecha_fin.date().toPython() if self.fecha_fin.date().isValid() else None,
            "max_alumnos": self.numero_maximo_alumnos.value(),
        }

    def _save(self):
        if self._loading or self._actividad_id is None:
            return

        if not self._validar():
            QMessageBox.warning(self, "Error", "Dades incompletes o incorrectes.")
            return  
            

        data = self._build_data()
        try:
            modificar_actividad(self._actividad_id, data)
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))