from datetime import timedelta

from PySide6.QtCore import QDate, QSignalBlocker
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QDateEdit,
)

from controladores.curso_academico import (
    duplicar_cursoA,
    eliminar_cursoA,
    listar_cursosA,
    listar_trimestres_por_cursoA,
    modificar_cursoA,
)
from controladores.trimestre import modificar_trimestre
from ui.table_models import DictTableModel
from ui.table_utils import enable_table_copy
from ui.theme import set_button_icon, set_button_variant


class DuplicarCursoDialog(QDialog):
    def __init__(self, nombre_origen, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Duplicar curs academic")
        self._nombre_origen = nombre_origen
        self._nombre_copia = f"{nombre_origen} - copia"
        self._nombre_siguiente = self._calcular_nombre_siguiente(nombre_origen)
        self._nombre_editado = False

        layout = QVBoxLayout()
        form = QFormLayout()

        self.nombre_edit = QLineEdit(self._nombre_copia)
        self.sumar_anio_check = QCheckBox("Sumar un any a les dates del curs i trimestres")

        form.addRow("Nom del nou curs:", self.nombre_edit)
        form.addRow("", self.sumar_anio_check)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        set_button_variant(self.btn_cancelar, "secondary")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_duplicar = QPushButton("Duplicar")
        set_button_variant(self.btn_duplicar, "primary")
        self.btn_duplicar.clicked.connect(self._acceptar)

        actions.addWidget(self.btn_cancelar)
        actions.addWidget(self.btn_duplicar)
        layout.addLayout(actions)
        self.setLayout(layout)

        self.nombre_edit.textEdited.connect(self._marcar_nombre_editado)
        self.sumar_anio_check.toggled.connect(self._sumar_anio_cambiado)

    def nombre(self):
        return self.nombre_edit.text().strip()

    def sumar_anio(self):
        return self.sumar_anio_check.isChecked()

    def _marcar_nombre_editado(self):
        self._nombre_editado = True

    def _sumar_anio_cambiado(self, checked):
        if self._nombre_editado:
            return
        if checked and self._nombre_siguiente:
            self.nombre_edit.setText(self._nombre_siguiente)
        elif not checked:
            self.nombre_edit.setText(self._nombre_copia)

    def _acceptar(self):
        if not self.nombre():
            QMessageBox.warning(self, "Revisa les dades", "El nom del nou curs es obligatori.")
            return
        self.accept()

    @staticmethod
    def _calcular_nombre_siguiente(nombre):
        partes = nombre.strip().split("-")
        if len(partes) != 2:
            return ""
        try:
            inicio = int(partes[0].strip())
            fin = int(partes[1].strip())
        except ValueError:
            return ""
        return f"{inicio + 1}-{fin + 1}"


class CursoAcademicoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestio de cursos academics")
        self.resize(980, 560)

        self._curso_actual = None
        self._trimestres_actuales = []
        self._loading = False
        self._dirty = False
        self._suppress_selection_warning = False

        main_layout = QVBoxLayout()

        btn_nou = QPushButton("Nou Curs Academic")
        set_button_icon(btn_nou, "ui/assets/plus.svg")
        set_button_variant(btn_nou, "primary")
        btn_nou.clicked.connect(self._mostrar_dialog_crear)

        btn_duplicar = QPushButton("Duplicar Curs Academic")
        set_button_icon(btn_duplicar, "ui/assets/plus.svg")
        set_button_variant(btn_duplicar, "secondary")
        btn_duplicar.clicked.connect(self._duplicar_curso)

        btn_borrar = QPushButton("Eliminar Curs Academic")
        set_button_icon(btn_borrar, "ui/assets/minus.svg")
        set_button_variant(btn_borrar, "danger")
        btn_borrar.clicked.connect(self._eliminar_curso)

        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.addWidget(btn_nou)
        top_buttons_layout.addWidget(btn_duplicar)
        top_buttons_layout.addWidget(btn_borrar)
        top_buttons_layout.addStretch()
        main_layout.addLayout(top_buttons_layout)

        content_layout = QHBoxLayout()

        self.tabla = QTableView()
        self.tabla.setSelectionBehavior(QTableView.SelectRows)
        self.tabla.setSelectionMode(QTableView.SingleSelection)
        self.tabla.setAlternatingRowColors(True)
        enable_table_copy(self.tabla)
        content_layout.addWidget(self.tabla, 3)

        editor_layout = QVBoxLayout()
        self._crear_editor_curso(editor_layout)
        self._crear_editor_trimestres(editor_layout)
        editor_layout.addStretch()
        content_layout.addLayout(editor_layout, 2)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        self._set_editor_enabled(False)
        self._refresh_table()

    def _crear_editor_curso(self, parent_layout):
        self.curso_box = QGroupBox("Curs seleccionat")
        form = QFormLayout()

        self.curso_nombre = QLineEdit()
        self.curso_inicio = self._crear_date_edit()
        self.curso_fin = self._crear_date_edit()

        form.addRow("Nom:", self.curso_nombre)
        form.addRow("Inici del curs:", self.curso_inicio)
        form.addRow("Final del curs:", self.curso_fin)

        self.curso_box.setLayout(form)
        parent_layout.addWidget(self.curso_box)

        self.curso_nombre.textEdited.connect(self._mark_dirty)
        self.curso_inicio.dateChanged.connect(self._mark_dirty)
        self.curso_fin.dateChanged.connect(self._mark_dirty)

    def _crear_editor_trimestres(self, parent_layout):
        self.trimestre_box = QGroupBox("Trimestres")
        box_layout = QVBoxLayout()

        quick_layout = QHBoxLayout()
        self.btn_repartir = QPushButton("Repartir dates")
        set_button_variant(self.btn_repartir, "secondary")
        self.btn_repartir.setToolTip("Divideix el curs seleccionat en quatre trimestres seguits.")
        self.btn_repartir.clicked.connect(self._repartir_trimestres)

        self.btn_encadenar = QPushButton("Encadenar")
        set_button_variant(self.btn_encadenar, "secondary")
        self.btn_encadenar.setToolTip("Fa que cada trimestre comenci l'endema de l'anterior.")
        self.btn_encadenar.clicked.connect(self._encadenar_trimestres)

        quick_layout.addWidget(self.btn_repartir)
        quick_layout.addWidget(self.btn_encadenar)
        quick_layout.addStretch()
        box_layout.addLayout(quick_layout)

        form = QFormLayout()
        self.trimestres_edits = []
        for i in range(4):
            inicio = self._crear_date_edit()
            fin = self._crear_date_edit()
            self.trimestres_edits.append((inicio, fin))

            row_layout = QHBoxLayout()
            row_layout.addWidget(QLabel("Inici"))
            row_layout.addWidget(inicio)
            row_layout.addWidget(QLabel("Fi"))
            row_layout.addWidget(fin)
            form.addRow(f"T{i + 1}:", row_layout)

            inicio.dateChanged.connect(self._mark_dirty)
            fin.dateChanged.connect(self._mark_dirty)

        box_layout.addLayout(form)

        actions_layout = QHBoxLayout()
        self.lbl_estado = QLabel("")
        self.lbl_estado.setProperty("role", "muted")
        self.btn_descartar = QPushButton("Descartar")
        set_button_variant(self.btn_descartar, "secondary")
        self.btn_descartar.clicked.connect(self._cargar_editor_desde_seleccion)

        self.btn_guardar = QPushButton("Guardar canvis")
        set_button_variant(self.btn_guardar, "primary")
        self.btn_guardar.clicked.connect(lambda: self._guardar_cambios())

        actions_layout.addWidget(self.lbl_estado)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_descartar)
        actions_layout.addWidget(self.btn_guardar)
        box_layout.addLayout(actions_layout)

        self.trimestre_box.setLayout(box_layout)
        parent_layout.addWidget(self.trimestre_box)

    def _crear_date_edit(self):
        edit = QDateEdit()
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("dd-MM-yyyy")
        return edit

    def _mostrar_dialog_crear(self):
        from ui.cursoAcademico_dialog import CursoAcademicoFormDialog

        dlg = CursoAcademicoFormDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._refresh_table(select_id=getattr(dlg, "curso_id", None))

    def _refresh_table(self, select_id=None):
        cursos = listar_cursosA()
        self._all_cursos = [curso.copy() for curso in cursos]
        rows = []
        for curso in cursos:
            row = curso.copy()
            row["fechaInicio"] = row["fechaInicio"].strftime("%d-%m-%Y")
            row["fechaFin"] = row["fechaFin"].strftime("%d-%m-%Y")
            rows.append(row)

        headers = [
            ("Nom", "nombre"),
            ("Inici", "fechaInicio"),
            ("Fi", "fechaFin"),
        ]
        model = DictTableModel(rows, headers)
        self.tabla.setModel(model)
        self.tabla.resizeColumnsToContents()

        new_sel = self.tabla.selectionModel()
        try:
            new_sel.currentRowChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        new_sel.currentRowChanged.connect(self._row_changed)
        self._sel_model = new_sel

        if rows:
            row_to_select = 0
            if select_id is not None:
                row_to_select = next(
                    (index for index, item in enumerate(rows) if item["id"] == select_id),
                    0,
                )
            self.tabla.selectRow(row_to_select)
        else:
            self._curso_actual = None
            self._trimestres_actuales = []
            self._set_editor_enabled(False)

    def _eliminar_curso(self):
        sel = self.tabla.selectionModel().selectedRows()
        if not sel:
            return

        curso = self.tabla.model().rows[sel[0].row()]
        nom_complet = curso["nombre"]

        box = QMessageBox(self)
        box.setWindowTitle("Confirmar eliminacio")
        box.setText(
            f"Vols eliminar el curs \"{nom_complet}\" (ID {curso['id']})?\n"
            "Aquesta accio no es pot desfer."
        )
        icon_path = "ui/assets/trash.svg"
        pix = QPixmap(icon_path)
        if pix.isNull() and icon_path.lower().endswith(".svg"):
            icon = QIcon(icon_path)
            pix = icon.pixmap(48, 48)
        if not pix.isNull():
            box.setIconPixmap(pix)
        else:
            box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Si")
        box.button(QMessageBox.No).setText("No")

        if box.exec() != QMessageBox.Yes:
            return

        eliminar_cursoA(curso["id"])
        self._refresh_table()

    def _duplicar_curso(self):
        sel = self.tabla.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(
                self,
                "Duplicar curs academic",
                "Selecciona el curs academic que vols duplicar.",
            )
            return

        curso = self.tabla.model().rows[sel[0].row()]
        dlg = DuplicarCursoDialog(curso["nombre"], self)
        if dlg.exec() != QDialog.Accepted:
            return

        try:
            nuevo_id = duplicar_cursoA(
                curso["id"],
                dlg.nombre(),
                sumar_anio=dlg.sumar_anio(),
            )
            self._refresh_table(select_id=nuevo_id)
        except ValueError as e:
            QMessageBox.warning(self, "No s'ha pogut duplicar", str(e))

    def _row_changed(self, curr, _prev):
        if self._suppress_selection_warning:
            return

        if not curr.isValid():
            self._curso_actual = None
            self._trimestres_actuales = []
            self._set_editor_enabled(False)
            return

        row_id = self.tabla.model().rows[curr.row()]["id"]
        if self._dirty and self._curso_actual and row_id != self._curso_actual["id"]:
            if not self._confirmar_cambios_pendientes():
                self._seleccionar_curso(self._curso_actual["id"])
                return

        self._curso_actual = next((c for c in self._all_cursos if c["id"] == row_id), None)
        self._trimestres_actuales = listar_trimestres_por_cursoA(row_id)
        self._cargar_editor_desde_seleccion()

    def _cargar_editor_desde_seleccion(self):
        if not self._curso_actual:
            self._set_editor_enabled(False)
            return

        self._loading = True
        blockers = [
            QSignalBlocker(self.curso_nombre),
            QSignalBlocker(self.curso_inicio),
            QSignalBlocker(self.curso_fin),
        ]
        for inicio_edit, fin_edit in self.trimestres_edits:
            blockers.append(QSignalBlocker(inicio_edit))
            blockers.append(QSignalBlocker(fin_edit))

        self.curso_nombre.setText(self._curso_actual["nombre"])
        self.curso_inicio.setDate(self._to_qdate(self._curso_actual["fechaInicio"]))
        self.curso_fin.setDate(self._to_qdate(self._curso_actual["fechaFin"]))

        fechas_generadas = self._calcular_trimestres(
            self._curso_actual["fechaInicio"],
            self._curso_actual["fechaFin"],
        )
        if not fechas_generadas:
            fechas_generadas = [
                (self._curso_actual["fechaInicio"], self._curso_actual["fechaFin"])
            ] * 4
        for i, (inicio_edit, fin_edit) in enumerate(self.trimestres_edits):
            if i < len(self._trimestres_actuales):
                trimestre = self._trimestres_actuales[i]
                inicio_edit.setDate(self._to_qdate(trimestre["fechaInicio"]))
                fin_edit.setDate(self._to_qdate(trimestre["fechaFin"]))
                inicio_edit.setEnabled(True)
                fin_edit.setEnabled(True)
            else:
                inicio, fin = fechas_generadas[i]
                inicio_edit.setDate(self._to_qdate(inicio))
                fin_edit.setDate(self._to_qdate(fin))
                inicio_edit.setEnabled(False)
                fin_edit.setEnabled(False)

        del blockers
        self._loading = False
        self._set_editor_enabled(True)
        self._set_dirty(False)

    def _guardar_cambios(self, refresh=True):
        if not self._curso_actual:
            return False

        error = self._validar_editor()
        if error:
            QMessageBox.warning(self, "Revisa les dates", error)
            return False

        curso_id = self._curso_actual["id"]
        curso_data = {
            "nombre": self.curso_nombre.text().strip(),
            "fechaInicio": self.curso_inicio.date().toPython(),
            "fechaFin": self.curso_fin.date().toPython(),
        }

        try:
            modificar_cursoA(curso_id, curso_data)
            for index, trimestre in enumerate(self._trimestres_actuales[:4]):
                inicio, fin = self.trimestres_edits[index]
                modificar_trimestre(
                    trimestre["id"],
                    {
                        "fechaInicio": inicio.date().toPython(),
                        "fechaFin": fin.date().toPython(),
                    },
                )
        except ValueError as e:
            QMessageBox.warning(self, "No s'han pogut guardar els canvis", str(e))
            return False

        self.lbl_estado.setText("Canvis guardats")
        self._set_dirty(False)
        self._curso_actual.update(curso_data)
        for index, trimestre in enumerate(self._trimestres_actuales[:4]):
            inicio, fin = self.trimestres_edits[index]
            trimestre["fechaInicio"] = inicio.date().toPython()
            trimestre["fechaFin"] = fin.date().toPython()
        if refresh:
            self._refresh_table(select_id=curso_id)
        return True

    def _confirmar_cambios_pendientes(self):
        box = QMessageBox(self)
        box.setWindowTitle("Canvis pendents")
        box.setText(
            "Hi ha canvis sense guardar en el curs actual.\n"
            "Vols guardar-los abans de seleccionar un altre curs?"
        )
        btn_guardar = box.addButton("Guardar", QMessageBox.AcceptRole)
        btn_descartar = box.addButton("Descartar", QMessageBox.DestructiveRole)
        btn_cancelar = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(btn_guardar)
        box.exec()

        clicked = box.clickedButton()
        if clicked == btn_cancelar:
            return False
        if clicked == btn_descartar:
            self._set_dirty(False)
            return True
        if clicked == btn_guardar:
            return self._guardar_cambios(refresh=False)
        return False

    def _seleccionar_curso(self, curso_id):
        self._suppress_selection_warning = True
        try:
            for row, item in enumerate(self.tabla.model().rows):
                if item["id"] == curso_id:
                    self.tabla.selectRow(row)
                    break
        finally:
            self._suppress_selection_warning = False

    def _validar_editor(self):
        if not self.curso_nombre.text().strip():
            return "El nom del curs es obligatori."

        curso_inicio = self.curso_inicio.date().toPython()
        curso_fin = self.curso_fin.date().toPython()
        if curso_inicio > curso_fin:
            return "La data d'inici del curs no pot ser posterior a la data final."

        anterior_fin = None
        for index, (inicio_edit, fin_edit) in enumerate(self.trimestres_edits):
            if index >= len(self._trimestres_actuales):
                continue
            inicio = inicio_edit.date().toPython()
            fin = fin_edit.date().toPython()
            if inicio > fin:
                return f"El trimestre T{index + 1} acaba abans de comencar."
            if anterior_fin and inicio <= anterior_fin:
                return f"El trimestre T{index + 1} se solapa amb el trimestre anterior."
            anterior_fin = fin

        return None

    def _repartir_trimestres(self):
        curso_inicio = self.curso_inicio.date().toPython()
        curso_fin = self.curso_fin.date().toPython()
        if curso_inicio > curso_fin:
            QMessageBox.warning(
                self,
                "Revisa les dates",
                "La data d'inici del curs no pot ser posterior a la data final.",
            )
            return

        trimestres = self._calcular_trimestres(curso_inicio, curso_fin)
        if not trimestres:
            QMessageBox.warning(
                self,
                "Revisa les dates",
                "El curs ha de tenir almenys quatre dies per repartir-lo en trimestres.",
            )
            return

        self._loading = True
        blockers = []
        for index, (inicio_edit, fin_edit) in enumerate(self.trimestres_edits):
            blockers.extend([QSignalBlocker(inicio_edit), QSignalBlocker(fin_edit)])
            inicio, fin = trimestres[index]
            inicio_edit.setDate(self._to_qdate(inicio))
            fin_edit.setDate(self._to_qdate(fin))
        del blockers
        self._loading = False
        self._set_dirty(True)

    def _encadenar_trimestres(self):
        for index in range(1, len(self.trimestres_edits)):
            anterior_fin = self.trimestres_edits[index - 1][1].date().toPython()
            nuevo_inicio = anterior_fin + timedelta(days=1)
            self.trimestres_edits[index][0].setDate(self._to_qdate(nuevo_inicio))
        self._set_dirty(True)

    def _mark_dirty(self, *_args):
        if not self._loading:
            self._set_dirty(True)

    def _set_dirty(self, dirty):
        self._dirty = dirty
        self.btn_guardar.setEnabled(dirty and self._curso_actual is not None)
        self.btn_descartar.setEnabled(dirty and self._curso_actual is not None)
        if dirty:
            self.lbl_estado.setText("Canvis pendents")
        elif self._curso_actual:
            self.lbl_estado.setText("")

    def _set_editor_enabled(self, enabled):
        self.curso_box.setEnabled(enabled)
        self.trimestre_box.setEnabled(enabled)
        self.btn_guardar.setEnabled(False)
        self.btn_descartar.setEnabled(False)
        if not enabled:
            self.lbl_estado.setText("Selecciona un curs")

    @staticmethod
    def _to_qdate(value):
        return QDate(value.year, value.month, value.day)

    @staticmethod
    def _calcular_trimestres(inicio, fin):
        total_days = (fin - inicio).days + 1
        if total_days < 4:
            return []

        base = total_days // 4
        extra = total_days % 4
        actual = inicio
        trimestres = []
        for index in range(4):
            dias = base + (1 if index < extra else 0)
            trimestre_fin = actual + timedelta(days=dias - 1)
            if index == 3:
                trimestre_fin = fin
            trimestres.append((actual, trimestre_fin))
            actual = trimestre_fin + timedelta(days=1)
        return trimestres
