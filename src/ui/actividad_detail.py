from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QDateEdit, QSpinBox, QMessageBox, QVBoxLayout, QTextEdit, QComboBox, QDoubleSpinBox, QTableView, QLabel
from PySide6.QtCore import Signal, QDate, Qt
from controladores.actividades import consultar_actividad, modificar_actividad, listar_inscripciones_por_Actividad, actualizar_estados_inscripciones
from controladores.personal import consultar_personal, listar_personal
from controladores.socios import consultar_socio
from ui.table_models import DictTableModel

class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actividadID = None
        self._loading = False

        self.nombre = QLineEdit()
        self.personal = QComboBox()
        self._refresh_personal()
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(0)
        self.numMaxAlumnos.setMaximum(999)
        self.preuMatricula = QDoubleSpinBox()
        self.preuMatricula.setDecimals(2)
        self.descripcion = QTextEdit()

        form = QFormLayout()
        form.addRow("Nom:", self.nombre)
        form.addRow("Professor/Voluntari:", self.personal)
        form.addRow("Màxim alumnes:", self.numMaxAlumnos)
        form.addRow("Preu matrícula:", self.preuMatricula)
        form.addRow("Descripció:", self.descripcion)

        layout = QVBoxLayout(self)
        layout.addLayout(form)

        self.label_inscrits = QLabel("Socis inscrits:")
        self.inscrits_table = QTableView()
        self.inscrits_table.verticalHeader().setVisible(False)
        self.inscrits_table.setSelectionBehavior(QTableView.SelectRows)
        self.inscrits_table.setSelectionMode(QTableView.NoSelection)
        self.inscrits_table.setAlternatingRowColors(True)

        layout.addWidget(self.label_inscrits)
        layout.addWidget(self.inscrits_table)
        layout.addStretch()

        self.nombre.editingFinished.connect(self._on_editing_finished)
        self.descripcion.focusOutEvent = self._wrap_focus_out(self.descripcion.focusOutEvent)
        self.personal.currentTextChanged.connect(self._on_editing_finished)
        self.numMaxAlumnos.editingFinished.connect(self._on_editing_finished)
        self.preuMatricula.editingFinished.connect(self._on_editing_finished)

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

        self._refresh_personal()
        personalID = act.get("personalID")
        if personalID is None:
            self.personal.setCurrentText("Desconegut")
        else:
            personal = consultar_personal(personalID)
            if personal.get("apellido2") is None:
                self.personal.setCurrentText(f"{personal['apellido1']}, {personal['nombre']}".strip())
            else:
                self.personal.setCurrentText(
                    f"{personal.get('apellido1', '')} {personal.get('apellido2', '')}, {personal.get('nombre', '')}".strip()
                )

        numMaxAlumnos = act.get("numMaxAlumnos")
        if numMaxAlumnos is None:
            self.numMaxAlumnos.setValue(0)
        else:
            self.numMaxAlumnos.setValue(numMaxAlumnos)

        self.preuMatricula.setValue(act.get("precio_matricula", 0.0))
        self.preuMatricula.setMinimum(0.0)
        self.preuMatricula.setMaximum(999.99)
        self.descripcion.setText(act.get("descripcion", ""))
        print("Cargando actividad:", act)  # debug

        self._load_inscrits_table()
        self._loading = False

    def _load_inscrits_table(self):
        try:
            inscripciones = listar_inscripciones_por_Actividad(self._actividadID)
            headers = [
                ("Nom", "nombre"),
                ("Cognom", "apellido1"),
                ("Data Inscripció", "fechaInscripcion"),
                ("Estat", "estado")
            ]
            for inscripcion in inscripciones:
                socio = consultar_socio(inscripcion["socioID"])
                inscripcion["estado"] = inscripcion["estado"].value
                inscripcion["fechaInscripcion"] = inscripcion["fechaInscripcion"].strftime("%d-%m-%Y")
                if socio:
                    inscripcion["nombre"] = socio.get("nombre", "")
                    inscripcion["apellido1"] = socio.get("apellido1", "")
                    
                else:
                    inscripcion["nombre"] = "Desconegut"
                    inscripcion["apellido1"] = ""
            self.inscrits_table.setModel(DictTableModel(inscripciones, headers))
            self.inscrits_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut carregar les inscripcions: {e}")

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.numMaxAlumnos.setValue(0)
        self.inscrits_table.setModel(DictTableModel([], []))

    def _validar(self) -> bool:
        if not self.nombre.text().strip():
            QMessageBox.warning(self, "Error", "El camp 'Nom' és obligatori.")
            return False
        return True

    def _build_data(self) -> dict:
        return {
            "nombre": self.nombre.text().strip(),
            "personalID": self.personal.currentData(),
            "numMaxAlumnos": self.numMaxAlumnos.value(),
            "precio_matricula": self.preuMatricula.value(),
            "descripcion": self.descripcion.toPlainText().strip() or None,
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
            actualizar_estados_inscripciones(self._actividadID)
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _refresh_personal(self):
        """Actualiza la lista de personal en el combo box."""
        self.personal.clear()
        for persona in listar_personal():
            if persona.get("apellido2") is None:
                nombre = f"{persona['apellido1']}, {persona['nombre']}".strip()
            else:
                nombre = f"{persona['apellido1']} {persona['apellido2']}, {persona['nombre']}".strip()
            self.personal.addItem(nombre, userData=persona["id"])

    def _wrap_focus_out(self, original_focus_out):
        def new_focus_out(event):
            if not self._loading:
                self._save()
            return original_focus_out(event)
        return new_focus_out
