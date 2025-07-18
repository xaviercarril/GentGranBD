from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QDateEdit, QSpinBox, QMessageBox, QVBoxLayout
from PySide6.QtCore import Signal, QDate
from controladores.actividades import consultar_actividad, modificar_actividad

class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actividadID = None
        self._loading = False

        self.nombre = QLineEdit()
        self.descripcion = QLineEdit()
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(0)
        self.numMaxAlumnos.setMaximum(999)

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Descripció:", self.descripcion)
        form.addRow("Màxim alumnes:", self.numMaxAlumnos)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch()

        self.nombre.editingFinished.connect(self._on_editing_finished)
        self.descripcion.editingFinished.connect(self._on_editing_finished)
        self.numMaxAlumnos.editingFinished.connect(self._on_editing_finished)

    def _on_editing_finished(self):
        if not self._loading:
            self._save()

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

        numMaxAlumnos = act.get("numMaxAlumnos")
        if numMaxAlumnos is None:
            numMaxAlumnos = act.get("numMaxAlumnos")
        if numMaxAlumnos is not None:
            self.numMaxAlumnos.setValue(numMaxAlumnos)
        else:
            self.numMaxAlumnos.setValue(1)
        print("Cargando actividad:", act)  # debug
        self._loading = False
        self.saved.emit()

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.numMaxAlumnos.setValue(0)

    def _validar(self) -> bool:
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El camp 'Nom' és obligatori.")
            return False
        return True

    def _build_data(self) -> dict:
        return {
            "nombre": self.nombre.text().strip(),
            "descripcion": self.descripcion.text().strip() or None,
            "numMaxAlumnos": self.numMaxAlumnos.value(),
        }

    def _save(self):
        if self._loading or self._actividadID is None:
            return

        if not self._validar():
            QMessageBox.warning(self, "Error", "Dades incompletes o incorrectes.")
            return  

        data = self._build_data()
        print("Guardando datos:", data)  # debug

        try:
            modificar_actividad(self._actividadID, data)
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))