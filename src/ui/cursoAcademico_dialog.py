from PySide6.QtCore import QDate, QSignalBlocker
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDateEdit,
    QVBoxLayout,
)

from controladores.curso_academico import registrar_cursoA
from ui.theme import set_button_variant


class CursoAcademicoFormDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nou Curs Academic")
        self.curso_id = None
        self._loading = False
        self._ultimo_nombre_auto = ""
        self._fin_auto = True

        layout = QVBoxLayout()

        intro = QLabel("Defineix les dates del curs. Els quatre trimestres es crearan automaticament.")
        intro.setProperty("role", "muted")
        layout.addWidget(intro)

        form_layout = QFormLayout()

        self.nom = QLineEdit()
        self.inici = self._crear_date_edit()
        self.fi = self._crear_date_edit()

        form_layout.addRow("Nom del curs:", self.nom)
        form_layout.addRow("Inici:", self.inici)
        form_layout.addRow("Fi:", self.fi)
        layout.addLayout(form_layout)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        set_button_variant(self.btn_cancelar, "secondary")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_crear = QPushButton("Crear curs")
        set_button_variant(self.btn_crear, "primary")
        self.btn_crear.clicked.connect(self._guardar)

        actions.addWidget(self.btn_cancelar)
        actions.addWidget(self.btn_crear)
        layout.addLayout(actions)

        self.setLayout(layout)
        self._aplicar_fechas_por_defecto()

        self.inici.dateChanged.connect(self._inicio_cambiado)
        self.fi.dateChanged.connect(self._fin_cambiado)

    def _crear_date_edit(self):
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd-MM-yyyy")
        return edit

    def _aplicar_fechas_por_defecto(self):
        hoy = QDate.currentDate()
        inicio_year = hoy.year() if hoy.month() >= 6 else hoy.year() - 1
        inicio = QDate(inicio_year, 9, 1)
        fin = QDate(inicio_year + 1, 6, 30)

        self._loading = True
        blockers = [QSignalBlocker(self.nom), QSignalBlocker(self.inici), QSignalBlocker(self.fi)]
        self.inici.setDate(inicio)
        self.fi.setDate(fin)
        self._actualizar_nombre_auto(force=True)
        del blockers
        self._loading = False

    def _inicio_cambiado(self):
        if self._loading:
            return

        if self._fin_auto:
            inicio = self.inici.date()
            fin = QDate(inicio.year() + 1, 6, 30)
            if fin <= inicio:
                fin = inicio.addYears(1).addDays(-1)
            blocker = QSignalBlocker(self.fi)
            self.fi.setDate(fin)
            del blocker

        self._actualizar_nombre_auto()

    def _fin_cambiado(self):
        if not self._loading:
            self._fin_auto = False
            self._actualizar_nombre_auto()

    def _actualizar_nombre_auto(self, force=False):
        inicio_year = self.inici.date().year()
        fin_year = self.fi.date().year()
        nombre_auto = f"{inicio_year}-{fin_year}"
        nombre_actual = self.nom.text().strip()
        if force or not nombre_actual or nombre_actual == self._ultimo_nombre_auto:
            self.nom.setText(nombre_auto)
            self._ultimo_nombre_auto = nombre_auto

    def _guardar(self):
        nombre = self.nom.text().strip()
        inicio = self.inici.date().toPython()
        fin = self.fi.date().toPython()

        if not nombre:
            QMessageBox.warning(self, "Revisa les dades", "El nom del curs es obligatori.")
            return
        if inicio > fin:
            QMessageBox.warning(
                self,
                "Revisa les dates",
                "La data d'inici del curs no pot ser posterior a la data final.",
            )
            return

        try:
            self.curso_id = registrar_cursoA({
                "nombre": nombre,
                "fechaInicio": inicio,
                "fechaFin": fin,
            })
        except ValueError as e:
            QMessageBox.warning(self, "No s'ha pogut crear el curs", str(e))
            return

        self.accept()
