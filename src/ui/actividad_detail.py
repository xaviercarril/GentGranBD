from datetime import date, datetime
import re
import tempfile

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout, QFrame, QHeaderView, QLineEdit, QSpinBox, QMessageBox, QVBoxLayout,
    QTextEdit, QComboBox, QDoubleSpinBox, QTableView, QLabel, QPushButton,
    QHBoxLayout, QSizePolicy, QStyledItemDelegate, QTableWidget, QTableWidgetItem
)
from controladores.actividades import consultar_actividad, modificar_actividad, listar_inscripciones_detalle_por_Actividad, actualizar_estados_inscripciones
from controladores.inscripcion_socio import eliminar_inscripcion, modificar_inscripcion, registrar_inscripcion
from controladores.pagos import modificar_pago, registrar_pago
from controladores.personal import listar_personal
from controladores.punto_recogida import (
    consultar_puntos_recogida,
    eliminar_punto_recogida,
    modificar_punto_recogida,
    registrar_punto_recogida,
)
from controladores.socios import consultar_socio
from exportador.pdf_inscripciones import generar_pdf_matriculados_actividad
from inscripcion_columns import COURSE_INSCRIPTION_COLUMNS, TRIP_INSCRIPTION_COLUMNS
from models import EstadoInscripcion
from ui.seleccionar_socio_dialog import SeleccionarSocioDialog
from ui.table_models import DictTableModel
from ui.table_utils import enable_table_copy
from ui.theme import Palette, fit_combo_popup_to_contents, set_button_variant


class InscripcionesActividadTableModel(QAbstractTableModel):
    EDITABLE_KEYS = {
        "fechaInscripcion",
        "observaciones",
        "pagat",
        "asiento",
        "lugarRecogida",
    }

    def __init__(self, rows, headers, inscription_changed_callback, parent=None):
        super().__init__(parent)
        self.rows = rows or []
        self.labels, self.keys = zip(*headers)
        self._inscription_changed_callback = inscription_changed_callback

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.keys)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        key = self.keys[index.column()]
        value = self.rows[index.row()].get(key, "")

        if role in (Qt.DisplayRole, Qt.EditRole):
            if isinstance(value, date):
                return value.strftime("%d/%m/%Y")
            if value is None:
                return ""
            return str(value)

        if role == Qt.BackgroundRole and self.rows[index.row()].get("estado") == EstadoInscripcion.RESERVA.value:
            return QColor("#fff4cf")

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.labels[section]
        return super().headerData(section, orientation, role)

    def flags(self, index):
        flags = super().flags(index)
        if index.isValid() and self.keys[index.column()] in self.EDITABLE_KEYS:
            return flags | Qt.ItemIsEditable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False

        key = self.keys[index.column()]
        if key not in self.EDITABLE_KEYS:
            return False

        try:
            inscripcion = self.rows[index.row()]
            if key == "fechaInscripcion":
                new_value = self._parse_date(value)
            elif key == "pagat":
                new_value = self._parse_pagat(value)
            else:
                text = str(value).strip() if value is not None else ""
                new_value = text or None
            self._inscription_changed_callback(inscripcion["id"], key, new_value)
            inscripcion[key] = new_value
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        except ValueError as e:
            QMessageBox.warning(None, "Error", str(e))
            return False

    def sort(self, column, order=Qt.AscendingOrder):
        key = self.keys[column]
        reverse = order == Qt.DescendingOrder
        self.layoutAboutToBeChanged.emit()
        self.rows.sort(key=lambda row: self._sort_value(row.get(key)), reverse=reverse)
        self.layoutChanged.emit()

    def _sort_value(self, value):
        if value is None:
            return ""
        if isinstance(value, date):
            return value
        return str(value).lower()

    def _parse_date(self, value):
        text = str(value).strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        raise ValueError("La data ha de tenir format dd/mm/aaaa.")

    def _parse_pagat(self, value):
        text = str(value).strip().lower()
        if text in {"sí", "si", "s", "yes", "pagat", "pagado", "true", "1"}:
            return "Sí"
        if text in {"no", "n", "pendent", "pendiente", "false", "0"}:
            return "No"
        raise ValueError("El camp Pagat ha de ser Sí o No.")


class PagatDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(["No", "Sí"])
        return combo

    def setEditorData(self, editor, index):
        value = str(index.model().data(index, Qt.EditRole) or "No")
        pos = editor.findText(value)
        editor.setCurrentIndex(pos if pos >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


class PuntoRecogidaDelegate(QStyledItemDelegate):
    """Shows the saved pickup points when editing a trip participant."""

    OTROS = "Altres (Observacions)"

    def __init__(self, nombres, parent=None):
        super().__init__(parent)
        self.nombres = list(nombres)

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItem("Sense assignar", None)
        combo.addItem(self.OTROS, self.OTROS)
        for nombre in self.nombres:
            if nombre == self.OTROS:
                continue
            combo.addItem(nombre, nombre)
        fit_combo_popup_to_contents(combo)
        return combo

    def setEditorData(self, editor, index):
        value = str(index.model().data(index, Qt.EditRole) or "").strip()
        pos = editor.findData(value or None)
        if pos < 0 and value:
            editor.addItem(value, value)
            pos = editor.count() - 1
        editor.setCurrentIndex(max(0, pos))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.EditRole)


class PuntosRecogidaDialog(QDialog):
    """Inline, auto-saving editor for the pickup-point catalog."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self.setWindowTitle("Llocs de recollida")
        self.resize(700, 430)
        self.setMinimumSize(600, 360)

        self.table = QTableWidget(0, 2, self)
        self.table.setObjectName("pickupList")
        self.table.verticalHeader().hide()
        self.table.setHorizontalHeaderLabels(["Nom", "Adreça / indicacions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(
            QAbstractItemView.CurrentChanged
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
        )
        self.table.setShowGrid(False)
        self.table.setFocusPolicy(Qt.StrongFocus)
        self.table.setToolTip("Fes clic en una cel·la per editar-la. Els canvis es guarden automàticament.")

        self.btn_nuevo = QPushButton("+")
        self.btn_nuevo.setObjectName("pickupAdd")
        self.btn_nuevo.setToolTip("Afegir un lloc de recollida")
        self.btn_eliminar = QPushButton("−")
        self.btn_eliminar.setObjectName("pickupRemove")
        self.btn_eliminar.setToolTip("Eliminar el lloc seleccionat")
        self.btn_eliminar.setEnabled(False)
        save_state = QLabel("Guardat automàtic")
        save_state.setObjectName("pickupSaveState")

        toolbar = QFrame()
        toolbar.setObjectName("pickupToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(0)
        toolbar_layout.addWidget(self.btn_nuevo)
        toolbar_layout.addWidget(self.btn_eliminar)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(save_state)

        list_panel = QFrame()
        list_panel.setObjectName("pickupListPanel")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self.table, 1)
        list_layout.addWidget(toolbar)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("Tancar")
        set_button_variant(buttons.button(QDialogButtonBox.Close), "secondary")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)
        title = QLabel("Llocs de recollida")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Edita directament la llista. Prem + per afegir un lloc nou.")
        subtitle.setProperty("role", "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(list_panel, 1)
        layout.addWidget(buttons)

        self.setStyleSheet(
            f"""
            QFrame#pickupListPanel {{
                background: {Palette.SURFACE};
                border: 1px solid {Palette.BORDER};
                border-radius: 9px;
            }}
            QTableWidget#pickupList {{
                background: transparent;
                border: none;
                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
                outline: 0;
                gridline-color: transparent;
            }}
            QTableWidget#pickupList::item {{
                padding: 8px 10px;
                border-bottom: 1px solid {Palette.BORDER};
            }}
            QTableWidget#pickupList::item:selected {{
                background: {Palette.PRIMARY};
                color: white;
            }}
            QFrame#pickupToolbar {{
                background: #edf2e7;
                border: none;
                border-top: 1px solid {Palette.BORDER};
                border-bottom-left-radius: 9px;
                border-bottom-right-radius: 9px;
            }}
            QPushButton#pickupAdd, QPushButton#pickupRemove {{
                background: transparent;
                color: {Palette.TEXT_MUTED};
                border: none;
                border-right: 1px solid {Palette.BORDER};
                border-radius: 0;
                padding: 0;
                min-width: 40px;
                max-width: 40px;
                min-height: 32px;
                max-height: 32px;
                font-size: 21px;
                font-weight: 400;
            }}
            QPushButton#pickupAdd:hover, QPushButton#pickupRemove:hover {{
                background: {Palette.PRIMARY_SOFT};
                color: {Palette.TEXT};
            }}
            QPushButton#pickupRemove:disabled {{
                background: transparent;
                color: #aeb5a8;
            }}
            QLabel#pickupSaveState {{
                background: transparent;
                color: {Palette.TEXT_MUTED};
                padding-right: 10px;
                font-size: 12px;
            }}
            """
        )

        self.table.itemSelectionChanged.connect(self._update_delete_action)
        self.table.itemChanged.connect(self._save_item)
        self.btn_nuevo.clicked.connect(self._new)
        self.btn_eliminar.clicked.connect(self._delete)
        buttons.rejected.connect(self.accept)
        self._refresh()

    def _refresh(self, selected_id=None):
        self._loading = True
        puntos = consultar_puntos_recogida()
        self.table.setRowCount(len(puntos))
        for row, punto in enumerate(puntos):
            nombre = QTableWidgetItem(punto["nombre"])
            nombre.setData(Qt.UserRole, punto["id"])
            direccion = QTableWidgetItem(punto.get("direccion") or "")
            self.table.setItem(row, 0, nombre)
            self.table.setItem(row, 1, direccion)
            self.table.setRowHeight(row, 38)
            if punto["id"] == selected_id:
                self.table.setCurrentCell(row, 0)
        self._loading = False
        self._update_delete_action()

    def _new(self):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).data(Qt.UserRole) is None:
                self.table.setCurrentCell(row, 0)
                self.table.editItem(self.table.item(row, 0))
                return

        self._loading = True
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setRowHeight(row, 38)
        self._loading = False
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))
        self._update_delete_action()

    def _save_item(self, item):
        if self._loading:
            return
        row = item.row()
        nombre_item = self.table.item(row, 0)
        direccion_item = self.table.item(row, 1)
        punto_id = nombre_item.data(Qt.UserRole)
        nombre = nombre_item.text().strip()
        direccion = direccion_item.text().strip()

        if punto_id is None and not nombre:
            return

        try:
            if punto_id is None:
                punto_id = registrar_punto_recogida(
                    {"nombre": nombre, "direccion": direccion}
                )
                self._loading = True
                nombre_item.setData(Qt.UserRole, punto_id)
                self._loading = False
            else:
                cambios = (
                    {"nombre": nombre}
                    if item.column() == 0
                    else {"direccion": direccion}
                )
                modificar_punto_recogida(punto_id, cambios)
            self.changed.emit()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            self._refresh(punto_id)

    def _update_delete_action(self):
        self.btn_eliminar.setEnabled(self.table.currentRow() >= 0)

    def _delete(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 0):
            QMessageBox.warning(self, "Error", "Selecciona un lloc de recollida.")
            return
        punto_id = self.table.item(row, 0).data(Qt.UserRole)
        if punto_id is None:
            self.table.removeRow(row)
            self._update_delete_action()
            return
        reply = QMessageBox.question(
            self,
            "Confirmació",
            "Vols eliminar aquest lloc del catàleg? Les assignacions existents es conservaran.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            eliminar_punto_recogida(punto_id)
            self.changed.emit()
            self._refresh()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))


class ActividadDetailWidget(QWidget):
    saved = Signal()

    def __init__(self, parent=None, *, show_details=True, show_inscriptions=True):
        super().__init__(parent)
        self._actividadID = None
        self._cursoAcademicoID = None
        self._loading = False
        self._inscripciones = []
        self._tipo_actividad = "CURS"
        self._show_details = show_details
        self._show_inscriptions = show_inscriptions

        self.nombre = QLineEdit()
        self.personal = QComboBox()
        self.personal.setMinimumWidth(180)
        if self._show_details:
            self._refresh_personal()
        self.numMaxAlumnos = QSpinBox()
        self.numMaxAlumnos.setMinimum(0)
        self.numMaxAlumnos.setMaximum(999)
        self.preuMatricula = QDoubleSpinBox()
        self.preuMatricula.setDecimals(2)
        self.descripcion = QTextEdit()
        self.descripcion.setFixedHeight(95)
        self.socio_preview = QLabel("Sense foto")
        self.socio_preview.setFixedSize(115, 135)
        self.socio_preview.setAlignment(Qt.AlignCenter)
        self.socio_preview.setStyleSheet(f"border: 1px solid {Palette.BORDER_STRONG}; border-radius: 5px; color: {Palette.TEXT_MUTED}; background: {Palette.SURFACE_ALT};")
        self.nombre.setAlignment(Qt.AlignLeft)
        self.numMaxAlumnos.setAlignment(Qt.AlignLeft)
        self.preuMatricula.setAlignment(Qt.AlignLeft)
        self.descripcion.setAlignment(Qt.AlignLeft)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.label_nom = QLabel("Nom:")
        self.label_personal = QLabel("Professor/Voluntari:")
        self.label_maxim = QLabel("Màxim alumnes:")
        self.label_preu = QLabel("Preu matrícula:")
        form.addRow(self.label_nom, self.nombre)
        form.addRow(self.label_personal, self.personal)
        form.addRow(self.label_maxim, self.numMaxAlumnos)
        form.addRow(self.label_preu, self.preuMatricula)

        layout = QVBoxLayout(self)
        self.details_panel = QWidget()
        self.details_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)
        top_layout = QHBoxLayout()
        top_layout.addLayout(form, stretch=1)
        details_layout.addLayout(top_layout)
        self.label_descripcio = QLabel("Descripció:")
        details_layout.addWidget(self.label_descripcio)
        details_layout.addWidget(self.descripcion)
        layout.addWidget(self.details_panel)

        self.label_inscrits = QLabel("INSCRITS: 0/0")
        self.label_inscrits.setProperty("role", "sectionTitle")

        btn_layout = QHBoxLayout()
        self.btn_afegir_soci = QPushButton("Afegir soci")
        self.btn_eliminar_inscripcio = QPushButton("Eliminar inscripció")
        self.btn_refrescar = QPushButton("Refrescar")
        self.btn_asistencia = QPushButton("Assistència")
        self.btn_exportar_pdf = QPushButton("Exportar PDF")
        self.btn_exportar_excel = QPushButton("Exportar Excel")
        self.btn_afegir_soci.setIcon(QIcon("ui/assets/plus.svg"))
        self.btn_eliminar_inscripcio.setIcon(QIcon("ui/assets/minus.svg"))
        self.btn_refrescar.setIcon(QIcon("ui/assets/refresh.svg"))
        self.btn_asistencia.setIcon(QIcon("ui/assets/id-card.svg"))
        self.btn_exportar_pdf.setIcon(QIcon("ui/assets/pdf.svg"))
        self.btn_exportar_excel.setIcon(QIcon("ui/assets/excel.svg"))
        set_button_variant(self.btn_afegir_soci, "primary")
        set_button_variant(self.btn_eliminar_inscripcio, "danger")
        set_button_variant(self.btn_refrescar, "secondary")
        set_button_variant(self.btn_asistencia, "secondary")
        set_button_variant(self.btn_exportar_pdf, "secondary")
        set_button_variant(self.btn_exportar_excel, "secondary")
        btn_layout.addWidget(self.btn_afegir_soci)
        btn_layout.addWidget(self.btn_eliminar_inscripcio)
        btn_layout.addWidget(self.btn_refrescar)
        btn_layout.addWidget(self.btn_asistencia)
        btn_layout.addWidget(self.btn_exportar_pdf)
        btn_layout.addWidget(self.btn_exportar_excel)
        btn_layout.addStretch()

        self.inscrits_table = QTableView()
        self.inscrits_table.verticalHeader().setVisible(False)
        self.inscrits_table.setSelectionBehavior(QTableView.SelectRows)
        self.inscrits_table.setSelectionMode(QTableView.SingleSelection)
        enable_table_copy(self.inscrits_table)
        self.inscrits_table.setAlternatingRowColors(True)
        self.inscrits_table.setSortingEnabled(True)
        # Keep the participants table scrollable without forcing the whole
        # activities view to be taller than the application window.
        self.inscrits_table.setMinimumHeight(140)

        self.inscrits_panel = QWidget()
        self.inscrits_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        inscrits_layout = QVBoxLayout(self.inscrits_panel)
        inscrits_layout.setContentsMargins(0, 0, 0, 0)
        inscrits_layout.addWidget(self.label_inscrits)
        inscrits_layout.addLayout(btn_layout)
        table_photo_layout = QHBoxLayout()
        table_photo_layout.setSpacing(12)
        table_photo_layout.addWidget(self.inscrits_table, 1)
        photo_layout = QVBoxLayout()
        self.socio_preview_name = QLabel("Selecciona un soci")
        self.socio_preview_name.setWordWrap(True)
        self.socio_preview_name.setAlignment(Qt.AlignCenter)
        self.socio_preview_name.setProperty("role", "muted")
        photo_layout.addWidget(self.socio_preview_name)
        photo_layout.addWidget(self.socio_preview, alignment=Qt.AlignTop | Qt.AlignHCenter)
        photo_layout.addStretch()
        table_photo_layout.addLayout(photo_layout)
        inscrits_layout.addLayout(table_photo_layout, 1)
        layout.addWidget(self.inscrits_panel, 1 if show_inscriptions else 0)
        if not show_inscriptions:
            layout.addStretch()

        self.details_panel.setVisible(show_details)
        self.inscrits_panel.setVisible(show_inscriptions)

        self.nombre.editingFinished.connect(self._on_editing_finished)
        self.descripcion.focusOutEvent = self._wrap_focus_out(self.descripcion.focusOutEvent)
        self.personal.currentTextChanged.connect(self._on_editing_finished)
        self.numMaxAlumnos.editingFinished.connect(self._on_editing_finished)
        self.preuMatricula.editingFinished.connect(self._on_editing_finished)
        self.btn_afegir_soci.clicked.connect(self._afegir_soci)
        self.btn_eliminar_inscripcio.clicked.connect(self._eliminar_inscripcio)
        self.btn_refrescar.clicked.connect(self._refresh_inscripcions)
        self.btn_asistencia.clicked.connect(self._abrir_asistencia)
        self.btn_exportar_pdf.clicked.connect(self._exportar_pdf)
        self.btn_exportar_excel.clicked.connect(self._exportar_excel)
        self._set_inscription_actions_enabled(False)
        self.set_tipo_actividad("CURS")

    def _on_editing_finished(self):
        if not self._loading:
            self._save()

    def set_tipo_actividad(self, tipo):
        value = getattr(tipo, "value", tipo) or "CURS"
        self._tipo_actividad = value
        is_viatge = value == "VIATGE"

        self.label_nom.setText("Nom del viatge:" if is_viatge else "Nom:")
        self.label_personal.setText("Responsable:" if is_viatge else "Professor/Voluntari:")
        self.label_maxim.setText("Places:" if is_viatge else "Màxim alumnes:")
        self.label_preu.setText("Preu viatge:" if is_viatge else "Preu matrícula:")
        self.label_descripcio.setText("Descripció / itinerari:" if is_viatge else "Descripció:")
        self.btn_afegir_soci.setText("Afegir participant" if is_viatge else "Afegir soci")
        self.btn_asistencia.setVisible(not is_viatge)
        self.btn_asistencia.setToolTip(
            "Obrir el control d'assistència del viatge"
            if is_viatge
            else "Obrir el control d'assistència del curs"
        )
        self.btn_exportar_excel.setVisible(True)
        self._update_inscrits_counter()

    def load(self, actividadID):
        self._loading = True
        self._actividadID = actividadID
        self._cursoAcademicoID = None

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

        self.set_tipo_actividad(act.get("tipo"))
        self._cursoAcademicoID = act.get("cursoAcademico_id")
        self.nombre.setText(act.get("nombre", ""))

        if self._show_details:
            self._refresh_personal()
            personalID = act.get("personalID")
            if personalID is None:
                self.personal.setCurrentText("Desconegut")
            else:
                index = self.personal.findData(personalID)
                if index >= 0:
                    self.personal.setCurrentIndex(index)

        numMaxAlumnos = act.get("numMaxAlumnos")
        if numMaxAlumnos is None:
            self.numMaxAlumnos.setValue(0)
        else:
            self.numMaxAlumnos.setValue(numMaxAlumnos)

        self.preuMatricula.setValue(act.get("precio_matricula", 0.0))
        self.preuMatricula.setMinimum(0.0)
        self.preuMatricula.setMaximum(999.99)
        self.descripcion.setText(act.get("descripcion", ""))

        if self._show_inscriptions:
            self._load_inscrits_table()
            self._set_inscription_actions_enabled(True)
        self._loading = False

    def _load_inscrits_table(self):
        try:
            inscripciones = listar_inscripciones_detalle_por_Actividad(self._actividadID)
            headers = list(
                TRIP_INSCRIPTION_COLUMNS
                if self._tipo_actividad == "VIATGE"
                else COURSE_INSCRIPTION_COLUMNS
            )
            for inscripcion in inscripciones:
                inscripcion["estado"] = self._estado_value(inscripcion["estado"])
            self._inscripciones = inscripciones
            self._update_inscrits_counter()
            self.inscrits_table.setModel(
                InscripcionesActividadTableModel(
                    self._inscripciones,
                    headers,
                    self._update_inscripcion_field,
                    self,
                )
            )
            if self._tipo_actividad == "VIATGE":
                model = self.inscrits_table.model()
                pagat_col = model.keys.index("pagat") if model and "pagat" in model.keys else -1
                if pagat_col >= 0:
                    self.inscrits_table.setItemDelegateForColumn(pagat_col, PagatDelegate(self.inscrits_table))
                recogida_col = model.keys.index("lugarRecogida") if model and "lugarRecogida" in model.keys else -1
                if recogida_col >= 0:
                    nombres = self._nombres_puntos_recogida()
                    self.inscrits_table.setItemDelegateForColumn(
                        recogida_col,
                        PuntoRecogidaDelegate(nombres, self.inscrits_table),
                    )
                    self.inscrits_table.setToolTip(
                        "Fes doble clic a 'Lloc de recollida' per assignar un punt guardat."
                    )
            self.inscrits_table.hideColumn(0)
            self.inscrits_table.resizeColumnsToContents()
            self._clear_socio_preview()
            selection_model = self.inscrits_table.selectionModel()
            if selection_model:
                selection_model.currentRowChanged.connect(self._update_selected_socio_photo)
            if self._inscripciones:
                self.inscrits_table.selectRow(0)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut carregar les inscripcions: {e}")

    def _clear(self):
        self.nombre.clear()
        self.descripcion.clear()
        self.numMaxAlumnos.setValue(0)
        self._inscripciones = []
        label = "PARTICIPANTS" if self._tipo_actividad == "VIATGE" else "INSCRITS"
        self.label_inscrits.setText(f"{label}: 0/0")
        if self._show_inscriptions:
            self.inscrits_table.setModel(DictTableModel([], []))
        self._clear_socio_preview()
        self._set_inscription_actions_enabled(False)

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
        try:
            modificar_actividad(self._actividadID, data)
            actualizar_estados_inscripciones(self._actividadID)
            if self._show_inscriptions:
                self._load_inscrits_table()
            self.saved.emit()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _afegir_soci(self):
        if self._actividadID is None:
            return

        excluded_socio_ids = [ins["socioID"] for ins in self._inscripciones if ins.get("socioID")]
        dialog = SeleccionarSocioDialog(excluded_socio_ids=excluded_socio_ids, parent=self)
        if not dialog.exec():
            return

        socio = dialog.selected_socio()
        if not socio:
            return

        estado = EstadoInscripcion.RESERVA.value
        max_alumnes = self.numMaxAlumnos.value()
        inscrits_actuals = [
            ins for ins in self._inscripciones
            if ins.get("estado") == EstadoInscripcion.INSCRIT.value
        ]
        if max_alumnes > 0 and len(inscrits_actuals) < max_alumnes:
            estado = EstadoInscripcion.INSCRIT.value

        try:
            data = {
                "socioID": socio.get("id"),
                "actividadID": self._actividadID,
                "fechaInscripcion": date.today(),
                "estado": estado,
                "observaciones": "",
            }
            if socio.get("es_socio") is False:
                data["noSocioNombre"] = socio.get("noSocioNombre")
                data["noSocioApellido1"] = socio.get("noSocioApellido1")
                data["noSocioApellido2"] = socio.get("noSocioApellido2")
                data["noSocioDni"] = socio.get("noSocioDni")
                data["noSocioTelefono"] = socio.get("noSocioTelefono")
                data["noSocioEmail"] = socio.get("noSocioEmail")
                data["noSocioObservaciones"] = socio.get("noSocioObservaciones")
            registrar_inscripcion(data)
            actualizar_estados_inscripciones(self._actividadID)
            self._refresh_inscripcions()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'ha pogut afegir el soci: {e}")

    def _eliminar_inscripcio(self):
        row = self.inscrits_table.currentIndex().row()
        model = self.inscrits_table.model()
        if model is None or row < 0 or row >= len(model.rows):
            QMessageBox.warning(self, "Error", "Selecciona una inscripció primer.")
            return

        inscripcio = model.rows[row]
        nom = " ".join(
            value for value in [
                inscripcio.get("nombre", ""),
                inscripcio.get("apellido1", ""),
                inscripcio.get("apellido2", ""),
            ] if value
        )
        reply = QMessageBox.question(
            self,
            "Confirmació",
            f"Segur que vols eliminar la inscripció de {nom or 'aquest soci'}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            eliminar_inscripcion(inscripcio["id"])
            actualizar_estados_inscripciones(self._actividadID)
            self._refresh_inscripcions()
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'ha pogut eliminar la inscripció: {e}")

    def _refresh_inscripcions(self):
        if self._actividadID is None:
            return
        actualizar_estados_inscripciones(self._actividadID)
        self._load_inscrits_table()
        self.saved.emit()

    def _abrir_asistencia(self):
        if self._actividadID is None or self._cursoAcademicoID is None:
            return
        from ui.asistencia_dialog import AsistenciaDialog

        dialog = AsistenciaDialog(self._actividadID, self._cursoAcademicoID, self)
        dialog.exec()

    def _nombres_puntos_recogida(self):
        try:
            guardados = [punto["nombre"] for punto in consultar_puntos_recogida()]
        except Exception:
            guardados = []
        heredados = [
            str(inscripcion.get("lugarRecogida") or "").strip()
            for inscripcion in self._inscripciones
        ]
        return sorted({nombre for nombre in guardados + heredados if nombre}, key=str.casefold)

    def _update_inscripcion_field(self, inscripcion_id, field, value):
        if field == "pagat":
            self._update_pagat_field(inscripcion_id, value)
            self.saved.emit()
            return

        modificar_inscripcion(inscripcion_id, {field: value})
        if field == "fechaInscripcion":
            actualizar_estados_inscripciones(self._actividadID)
            # El cambio puede intercambiar INSCRIT/RESERVA. Se refrescan
            # primero los participantes y después la tabla superior común
            # a Cursos y Viatges, una vez finalizada la edición del modelo.
            QTimer.singleShot(0, self._finish_fecha_inscripcion_update)
            return
        self.saved.emit()

    def _finish_fecha_inscripcion_update(self):
        self._load_inscrits_table()
        self.saved.emit()

    def _update_pagat_field(self, inscripcion_id, value):
        inscripcion = next((ins for ins in self._inscripciones if ins.get("id") == inscripcion_id), None)
        if not inscripcion:
            raise ValueError("Inscripció no trobada.")
        estado = "PAGAT" if value == "Sí" else "PENDENT"
        pago_id = inscripcion.get("_pago_id")
        if pago_id:
            modificar_pago(pago_id, {"estado": estado})
        else:
            pago_id = registrar_pago(
                {
                    "socioID": inscripcion["socioID"],
                    "actividadID": self._actividadID,
                    "inscripcionID": inscripcion_id,
                    "fecha_pago": date.today(),
                    "importe": self.preuMatricula.value(),
                    "estado": estado,
                    "observaciones": "",
                }
            )
            inscripcion["_pago_id"] = pago_id
        inscripcion["pagat"] = value

    def _exportar_pdf(self):
        if self._actividadID is None:
            return

        inscripcion_ids = self._current_inscription_ids()
        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", self.nombre.text()).strip("_") or "activitat"
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f"matriculats-{nombre}-",
                suffix=".pdf",
                delete=False,
            ) as tmp:
                ruta = tmp.name
            generar_pdf_matriculados_actividad(
                self._actividadID,
                ruta,
                inscripcion_ids=inscripcion_ids,
            )
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
                QMessageBox.warning(
                    self,
                    "Avís",
                    f"No s'ha pogut obrir el visor PDF del sistema.\nPDF temporal: {ruta}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")

    def _current_inscription_ids(self):
        model = self.inscrits_table.model()
        return [
            row["id"]
            for row in getattr(model, "rows", [])
            if row.get("id") is not None
        ]

    def _exportar_excel(self):
        if self._actividadID is None:
            return

        is_viatge = self._tipo_actividad == "VIATGE"
        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", self.nombre.text()).strip("_") or "activitat"
        try:
            from exportador.excel_participantes import (
                generar_excel_inscritos_curso,
                generar_excel_participantes_viaje,
            )

            with tempfile.NamedTemporaryFile(
                prefix=f"{'participants' if is_viatge else 'inscrits'}-{nombre}-",
                suffix=".xlsx",
                delete=False,
            ) as tmp:
                ruta = tmp.name
            if is_viatge:
                generar_excel_participantes_viaje(self._actividadID, ruta)
            else:
                generar_excel_inscritos_curso(self._actividadID, ruta)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
                QMessageBox.warning(
                    self,
                    "Avís",
                    f"No s'ha pogut obrir l'Excel del sistema.\nFitxer temporal: {ruta}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar l'Excel:\n{e}")

    def _update_inscrits_counter(self):
        inscrits = sum(
            1 for ins in self._inscripciones
            if ins.get("estado") == EstadoInscripcion.INSCRIT.value
        )
        label = "PARTICIPANTS" if self._tipo_actividad == "VIATGE" else "INSCRITS"
        self.label_inscrits.setText(f"{label}: {inscrits}/{self.numMaxAlumnos.value()}")

    def _set_inscription_actions_enabled(self, enabled):
        self.btn_afegir_soci.setEnabled(enabled)
        self.btn_eliminar_inscripcio.setEnabled(enabled)
        self.btn_refrescar.setEnabled(enabled)
        self.btn_asistencia.setEnabled(enabled)
        self.btn_exportar_pdf.setEnabled(enabled)
        self.btn_exportar_excel.setEnabled(enabled)

    def _estado_value(self, estado):
        return getattr(estado, "value", estado)

    def _update_selected_socio_photo(self, current, previous):
        if not current.isValid():
            self._clear_socio_preview()
            return

        model = self.inscrits_table.model()
        if not model or current.row() < 0 or current.row() >= len(model.rows):
            self._clear_socio_preview()
            return

        socio_id = model.rows[current.row()].get("socioID")
        nombre = " ".join(
            part for part in (
                model.rows[current.row()].get("nombre"),
                model.rows[current.row()].get("apellido1"),
                model.rows[current.row()].get("apellido2"),
            )
            if part
        )
        self.socio_preview_name.setText(nombre or "Participant")
        if not socio_id:
            self._clear_socio_preview("No soci", reset_name=False)
            return

        socio = consultar_socio(socio_id)
        foto = socio.get("foto") if socio else None
        if not foto:
            self._clear_socio_preview(reset_name=False)
            return

        pix = QPixmap()
        pix.loadFromData(foto)
        self.socio_preview.setText("")
        self.socio_preview.setPixmap(
            pix.scaled(self.socio_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _clear_socio_preview(self, text="Sense foto", *, reset_name=True):
        self.socio_preview.setPixmap(QPixmap())
        self.socio_preview.setText(text)
        if reset_name:
            self.socio_preview_name.setText("Selecciona un soci")

    def _refresh_personal(self):
        """Actualiza la lista de personal en el combo box."""
        self.personal.clear()
        for persona in listar_personal():
            if persona.get("apellido2") is None:
                nombre = f"{persona['apellido1']}, {persona['nombre']}".strip()
            else:
                nombre = f"{persona['apellido1']} {persona['apellido2']}, {persona['nombre']}".strip()
            self.personal.addItem(nombre, userData=persona["id"])
        fit_combo_popup_to_contents(self.personal)

    def _wrap_focus_out(self, original_focus_out):
        def new_focus_out(event):
            if not self._loading:
                self._save()
            return original_focus_out(event)
        return new_focus_out


class InscripcionesActividadDialog(QDialog):
    changed = Signal()

    def __init__(self, actividadID, parent=None):
        super().__init__(parent)
        self.actividadID = actividadID
        actividad = consultar_actividad(actividadID) or {}
        nombre = actividad.get("nombre") or "Activitat"
        tipo = getattr(actividad.get("tipo"), "value", actividad.get("tipo"))
        participantes = "participants" if tipo == "VIATGE" else "inscrits"

        self.setWindowTitle(f"Gestió d'{participantes} - {nombre}")
        self.resize(1180, 680)
        self.setMinimumSize(900, 540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        title = QLabel(nombre)
        title.setProperty("role", "sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Participants i inscripcions de l'activitat")
        subtitle.setProperty("role", "muted")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.inscripciones = ActividadDetailWidget(
            self,
            show_details=False,
            show_inscriptions=True,
        )
        self.inscripciones.saved.connect(self.changed.emit)
        layout.addWidget(self.inscripciones, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Close).setText("Tancar")
        set_button_variant(buttons.button(QDialogButtonBox.Close), "secondary")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.inscripciones.load(actividadID)
