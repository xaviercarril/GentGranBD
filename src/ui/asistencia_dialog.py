import re
import tempfile

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QTimeEdit, QSpinBox, QGroupBox, QGridLayout,
    QFrame, QSizePolicy, QHeaderView
)
from PySide6.QtCore import Qt, QTime, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont
from controladores.socios import consultar_socio
from controladores.trimestre import listar_clases_por_trimestre
from controladores.curso_academico import listar_trimestres_por_cursoA
from controladores.actividades import consultar_actividad, listar_inscripciones_por_Actividad
from controladores.asistencia_socio import registrar_asistenciaSocio, eliminar_asistenciaSocio, consultar_asistenciaSocio, generar_pdf_asistencias
from controladores.clase import generar_clases_semana, registrar_clase
from ui.table_utils import enable_table_copy
from ui.theme import Palette, set_button_icon, set_button_variant


MESOS_CAT = {
    1: "GENER",
    2: "FEBRER",
    3: "MARÇ",
    4: "ABRIL",
    5: "MAIG",
    6: "JUNY",
    7: "JULIOL",
    8: "AGOST",
    9: "SETEMBRE",
    10: "OCTUBRE",
    11: "NOVEMBRE",
    12: "DESEMBRE",
}


class AsistenciaDialog(QDialog):
    HEADER_ROWS = 2
    NAME_COLUMN = 0
    DATA_COLUMN_OFFSET = 1
    ATTENDANCE_ROLE = Qt.UserRole + 1

    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.resize(1280, 760)
        self.setWindowTitle("Gestió d'assistència")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID
        actividad = consultar_actividad(self.actividadID)
        self.actividad_nombre = actividad.get("nombre", "Activitat") if actividad else "Activitat"
       
        self.trimestre_selector = QComboBox()
        self.btn_exportar = QPushButton("Exportar a PDF")
        self.btn_generar_dialog = QPushButton("Generar classes auto.")
        self.btn_añadir_manual = QPushButton("Afegir una classe")
        set_button_variant(self.btn_exportar, "secondary")
        set_button_variant(self.btn_generar_dialog, "primary")
        set_button_variant(self.btn_añadir_manual, "primary")
        set_button_icon(self.btn_exportar, "ui/assets/pdf.svg")
        set_button_icon(self.btn_generar_dialog, "ui/assets/refresh.svg")
        set_button_icon(self.btn_añadir_manual, "ui/assets/plus.svg")
        self.btn_exportar.setMinimumWidth(150)
        self.btn_generar_dialog.setMinimumWidth(185)
        self.btn_añadir_manual.setMinimumWidth(160)
        self.btn_generar_dialog.clicked.connect(self._abrir_dialog_generar)
        self.btn_añadir_manual.clicked.connect(self._abrir_dialog_afegir)
        self.btn_exportar.clicked.connect(self._exportar_asistencia_pdf)

        self._syncing_table = False
        self.table = QTableWidget()
        self.table.setObjectName("attendanceGrid")
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        enable_table_copy(self.table)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)
        self.table.verticalHeader().sectionClicked.connect(self._seleccionar_fila)
        self.table.horizontalHeader().sectionClicked.connect(self._seleccionar_columna)
        self.table.cellClicked.connect(self._on_cell_clicked)

        title_label = QLabel("Assistència")
        title_label.setProperty("role", "sectionTitle")
        title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle_label = QLabel(self.actividad_nombre)
        subtitle_label.setProperty("role", "muted")
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("attendanceSummary")

        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        header_text.addWidget(title_label)
        header_text.addWidget(subtitle_label)

        header_layout = QHBoxLayout()
        header_layout.addLayout(header_text)
        header_layout.addStretch()
        header_layout.addWidget(self.summary_label)

        toolbar = QFrame()
        toolbar.setObjectName("attendanceToolbar")
        toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_layout = QHBoxLayout(toolbar)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.setSpacing(10)
        label_trimestre = QLabel("Trimestre:")
        label_trimestre.setProperty("role", "muted")
        top_layout.addWidget(label_trimestre)
        top_layout.addWidget(self.trimestre_selector)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_exportar)
        top_layout.addWidget(self.btn_generar_dialog)
        top_layout.addWidget(self.btn_añadir_manual)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(12)
        layout.addLayout(header_layout)
        layout.addWidget(toolbar)
        layout.addWidget(self.table)
        self._apply_attendance_styles()
        self._update_summary(0, 0, 0)

        self.trimestre_selector.currentIndexChanged.connect(self._cargar_parrilla)
        self._cargar_trimestres()

    def _apply_attendance_styles(self):
        self.setStyleSheet(f"""
            QFrame#attendanceToolbar {{
                background: {Palette.SURFACE};
                border: 1px solid {Palette.BORDER};
                border-radius: 7px;
            }}
            QLabel#attendanceSummary {{
                background: {Palette.PRIMARY_SOFT};
                color: {Palette.TEXT};
                border: 1px solid {Palette.BORDER_STRONG};
                border-radius: 7px;
                padding: 7px 11px;
                font-weight: 600;
            }}
            QTableWidget#attendanceGrid {{
                background: {Palette.SURFACE};
                border: 1px solid {Palette.BORDER};
                border-radius: 8px;
                gridline-color: #e8ede2;
                outline: 0;
                selection-background-color: #d9e9bf;
                selection-color: {Palette.TEXT};
            }}
            QTableWidget#attendanceGrid::item {{
                border: 1px solid #e8ede2;
                padding: 0px 8px;
            }}
            QTableWidget#attendanceGrid::item:selected {{
                background: #d9e9bf;
                color: {Palette.TEXT};
            }}
        """)

    def _cargar_trimestres(self):
        self.trimestres = listar_trimestres_por_cursoA(self.cursoAcademicoID)
        self.trimestre_selector.clear()
        for t in self.trimestres:
            self.trimestre_selector.addItem(str(t["nombre"].value), t["id"])

    def _cargar_parrilla(self):
        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            return

        clases = [c for c in listar_clases_por_trimestre(trimestre_id) if c["actividadID"] == self.actividadID]
        clases.sort(key=lambda c: (c["fecha"], c.get("horaInicio")))
        inscripciones = listar_inscripciones_por_Actividad(self.actividadID)
        inscripciones = [i for i in inscripciones if i.get("socioID") and i.get("estado").value == "INSCRIT"]
        row_count = len(inscripciones)
        col_count = len(clases)
        data_row_count = row_count + self.HEADER_ROWS
        total_asistencias = 0

        self._syncing_table = True
        try:
            self.table.clear()
            self.table.clearSpans()
            self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.table.horizontalHeader().setVisible(False)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(False)
            self.table.setShowGrid(True)
            self.table.setWordWrap(True)
            self.table.setRowCount(data_row_count)
            self.table.setColumnCount(col_count + self.DATA_COLUMN_OFFSET)
            self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
            self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
            self.table.setSizeAdjustPolicy(QTableWidget.AdjustIgnored)
            self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.table.setWordWrap(False)
            self.table.horizontalHeader().setMinimumSectionSize(58)
            self.table.horizontalHeader().setDefaultSectionSize(68)
            self.table.horizontalHeader().setStretchLastSection(False)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

            # Habilitar el botón de la esquina superior izquierda de la tabla
            self.table.setCornerButtonEnabled(True)

            self.cell_items = [[None for _ in range(col_count)] for _ in range(row_count)]
            self.default_cell_colors = [[None for _ in range(col_count)] for _ in range(row_count)]
            self.row_header_items = []
            self._month_column_ranges = {}

            header_font = QFont()
            header_font.setBold(True)

            participant_item = QTableWidgetItem("Participant")
            participant_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            participant_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            participant_item.setBackground(QColor("#e8f0df"))
            participant_item.setForeground(QColor(Palette.TEXT))
            participant_item.setFont(header_font)
            self.table.setItem(0, self.NAME_COLUMN, participant_item)
            self.table.setSpan(0, self.NAME_COLUMN, self.HEADER_ROWS, 1)

            from collections import defaultdict

            meses = defaultdict(list)
            for col, clase in enumerate(clases):
                fecha = clase["fecha"]
                meses[(fecha.year, fecha.month)].append(col)

                day_item = QTableWidgetItem(str(fecha.day))
                day_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                day_item.setTextAlignment(Qt.AlignCenter)
                day_item.setBackground(QColor("#f6f9f2"))
                day_item.setForeground(QColor(Palette.TEXT))
                day_item.setFont(header_font)
                self.table.setItem(1, col + self.DATA_COLUMN_OFFSET, day_item)

            for _, columnas in meses.items():
                if not columnas:
                    continue
                first_col = columnas[0]
                fecha = clases[first_col]["fecha"]
                month_item = QTableWidgetItem(MESOS_CAT[fecha.month])
                month_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                month_item.setTextAlignment(Qt.AlignCenter)
                month_item.setBackground(QColor("#dbe9c9"))
                month_item.setForeground(QColor(Palette.TEXT))
                month_item.setFont(header_font)
                self.table.setItem(0, first_col + self.DATA_COLUMN_OFFSET, month_item)
                if len(columnas) > 1:
                    self.table.setSpan(0, first_col + self.DATA_COLUMN_OFFSET, 1, len(columnas))
                for col in columnas:
                    self._month_column_ranges[col] = columnas

            colores_por_columna = {}
            for i, (_, columnas) in enumerate(meses.items()):
                color = QColor("#f7faf3") if i % 2 == 0 else QColor(Palette.SURFACE)
                for col in columnas:
                    colores_por_columna[col] = color

            for row, insc in enumerate(inscripciones):
                table_row = row + self.HEADER_ROWS
                socio = consultar_socio(insc["socioID"])
                header_item = QTableWidgetItem(f"{socio['nombre']} {socio['apellido1']}")
                header_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                header_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                header_item.setBackground(QColor("#eef5e8" if row % 2 == 0 else "#f7faf3"))
                header_item.setForeground(QColor(Palette.TEXT))
                header_item.setFont(header_font)
                self.table.setItem(table_row, self.NAME_COLUMN, header_item)
                self.row_header_items.append(header_item)

                for col, clase in enumerate(clases):
                    asistencia = consultar_asistenciaSocio(insc["socioID"], clase["id"])
                    total_asistencias += 1 if asistencia else 0
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setData(Qt.UserRole, (insc["socioID"], clase["id"]))
                    item.setTextAlignment(Qt.AlignCenter)

                    default_color = colores_por_columna.get(col)
                    self._set_cell_presence(item, bool(asistencia), save=False, default_color=default_color)

                    self.table.setItem(table_row, col + self.DATA_COLUMN_OFFSET, item)
                    self.cell_items[row][col] = item
                    self.default_cell_colors[row][col] = default_color

            self.table.setColumnWidth(self.NAME_COLUMN, 270)
            for col in range(col_count):
                self.table.setColumnWidth(col + self.DATA_COLUMN_OFFSET, 68)
            self.table.setRowHeight(0, 34)
            self.table.setRowHeight(1, 34)
            for row in range(row_count):
                self.table.setRowHeight(row + self.HEADER_ROWS, 44)
        finally:
            self._syncing_table = False
            self._update_summary(row_count, col_count, total_asistencias)

    def _update_summary(self, participants, classes, attendances):
        self._summary_participants = participants
        self._summary_classes = classes
        self._summary_attendances = attendances
        self.summary_label.setText(
            f"{participants} participants | {classes} classes | {attendances} assistències"
        )

    def _is_item_checked(self, item):
        return bool(item and item.data(self.ATTENDANCE_ROLE))

    def _set_cell_presence(self, item, checked, save=True, default_color=None):
        previous = self._is_item_checked(item)
        item.setData(self.ATTENDANCE_ROLE, checked)
        item.setText("✓" if checked else "")
        font = item.font()
        font.setBold(checked)
        font.setPointSize(15 if checked else 13)
        item.setFont(font)
        item.setForeground(QColor("#2e5b2d" if checked else Palette.TEXT_MUTED))
        item.setBackground(QColor("#dff0dc") if checked else (default_color or QColor(Palette.SURFACE)))
        if save and previous != checked and not self._syncing_table:
            data = item.data(Qt.UserRole)
            if data and isinstance(data, tuple) and len(data) == 2:
                socio_id, clase_id = data
                self._guardar_asistencia(socio_id, clase_id, checked)
                self._update_summary(
                    getattr(self, "_summary_participants", 0),
                    getattr(self, "_summary_classes", 0),
                    getattr(self, "_summary_attendances", 0) + (1 if checked else -1),
                )

    def _reset_colores(self):
        cell_items = getattr(self, "cell_items", [])
        default_colors = getattr(self, "default_cell_colors", [])
        for fila in range(len(cell_items)):
            for col in range(len(cell_items[fila])):
                item = cell_items[fila][col]
                if not item:
                    continue
                color = None
                if fila < len(default_colors) and col < len(default_colors[fila]):
                    color = default_colors[fila][col]
                self._set_cell_presence(item, self._is_item_checked(item), save=False, default_color=color)
        for item in getattr(self, "row_header_items", []):
            if item:
                row = item.row() - self.HEADER_ROWS
                item.setBackground(QColor("#eef5e8" if row % 2 == 0 else "#f7faf3"))

    def _seleccionar_columna(self, columna):
        self._seleccionar_columnas([columna])

    def _seleccionar_columnas(self, columnas):
        # Permitir aplicar cambios a todas las columnas seleccionadas si hay más de una
        columnas = sorted(set(columnas))
        cell_items = getattr(self, "cell_items", [])
        if not cell_items:
            return
        col_count = len(cell_items[0]) if cell_items else 0
        columnas = [col for col in columnas if 0 <= col < col_count]
        if not columnas:
            return

        self._reset_colores()
        self.table.clearSelection()

        columna_items = []
        for columna in columnas:
            for fila in range(len(cell_items)):
                item = cell_items[fila][columna]
                if not item:
                    continue
                item.setSelected(True)
                item.setBackground(QColor("#d0e8ff"))
                columna_items.append(item)

        if not columna_items:
            return

        todos_marcados = all(self._is_item_checked(item) for item in columna_items)
        nuevo_estado = not todos_marcados

        for item in columna_items:
            self._set_cell_presence(item, nuevo_estado, save=True)

    def _seleccionar_fila(self, fila):
        fila -= self.HEADER_ROWS
        if fila < 0:
            return
        # Permitir aplicar cambios a todas las filas seleccionadas si hay más de una
        filas = sorted(
            set(index.row() - self.HEADER_ROWS for index in self.table.selectedIndexes())
        )
        filas = [f for f in filas if f >= 0]
        if len(filas) > 1:
            self._reset_colores()
            self.table.clearSelection()
            for f in filas:
                if 0 <= f < len(getattr(self, "cell_items", [])):
                    fila_items = [item for item in self.cell_items[f] if item]
                    nuevo_estado = not all(self._is_item_checked(item) for item in fila_items)
                    for item in fila_items:
                        item.setSelected(True)
                        self._set_cell_presence(item, nuevo_estado, save=True)
                    row_headers = getattr(self, "row_header_items", [])
                    if f < len(row_headers) and row_headers[f]:
                        row_headers[f].setBackground(QColor("#d0e8ff"))
            return
        cell_items = getattr(self, "cell_items", [])
        if not cell_items:
            return
        if fila < 0 or fila >= len(cell_items):
            return

        self._reset_colores()
        self.table.clearSelection()

        fila_items = []
        for col in range(len(cell_items[fila])):
            item = cell_items[fila][col]
            if not item:
                continue
            item.setSelected(True)
            item.setBackground(QColor("#d0e8ff"))
            fila_items.append(item)
        row_headers = getattr(self, "row_header_items", [])
        if fila < len(row_headers) and row_headers[fila]:
            row_headers[fila].setBackground(QColor("#d0e8ff"))

        if not fila_items:
            return

        todos_marcados = all(self._is_item_checked(item) for item in fila_items)
        nuevo_estado = not todos_marcados

        for item in fila_items:
            self._set_cell_presence(item, nuevo_estado, save=True)
    
    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeyEvent
        from controladores.clase import eliminar_clase
        if isinstance(event, QKeyEvent) and event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            items = []
            for index in self.table.selectedIndexes():
                row = index.row() - self.HEADER_ROWS
                col = index.column() - self.DATA_COLUMN_OFFSET
                if row >= 0 and col >= 0:
                    item = self.table.item(index.row(), index.column())
                    if item:
                        items.append(item)
            if items:
                nuevo_estado = not all(self._is_item_checked(item) for item in items)
                for item in items:
                    self._set_cell_presence(item, nuevo_estado, save=True)
                return
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key_Delete:
            columnas = sorted(
                set(index.column() - self.DATA_COLUMN_OFFSET for index in self.table.selectedIndexes())
            )
            columnas = [col for col in columnas if col >= 0]
            if not columnas:
                return
            trimestre_id = self.trimestre_selector.currentData()
            clases = [c for c in listar_clases_por_trimestre(trimestre_id) if c["actividadID"] == self.actividadID]
            clases.sort(key=lambda c: (c["fecha"], c.get("horaInicio")))
            clases_a_eliminar = [clases[col] for col in columnas if col < len(clases)]
            if not clases_a_eliminar:
                return
            confirm = QMessageBox.question(self, "Confirmar eliminació",
                                           f"Vols eliminar {len(clases_a_eliminar)} classe(s) seleccionada(es)?",
                                           QMessageBox.Yes | QMessageBox.No)
            if confirm == QMessageBox.Yes:
                for clase in clases_a_eliminar:
                    eliminar_clase(clase["id"])
                self._cargar_parrilla()

    def _guardar_asistencia(self, socio_id, clase_id, checked):
        if checked:
            registrar_asistenciaSocio({
                "socioID": socio_id,
                "claseID": clase_id,
                "presente": True
            })
        else:
            eliminar_asistenciaSocio(socio_id, clase_id)

    def _on_item_changed(self, item):
        if self._syncing_table:
            return
        data = item.data(Qt.UserRole)
        if not data or not isinstance(data, tuple) or len(data) != 2:
            return
        socio_id, clase_id = data
        checked = self._is_item_checked(item)
        self._guardar_asistencia(socio_id, clase_id, checked)

    def _on_cell_clicked(self, row, column):
        if column == self.NAME_COLUMN and row >= self.HEADER_ROWS:
            self._seleccionar_fila(row)
        elif row == 0 and column >= self.DATA_COLUMN_OFFSET:
            clase_col = column - self.DATA_COLUMN_OFFSET
            columnas = getattr(self, "_month_column_ranges", {}).get(clase_col, [clase_col])
            self._seleccionar_columnas(columnas)
        elif row == 1 and column >= self.DATA_COLUMN_OFFSET:
            self._seleccionar_columna(column - self.DATA_COLUMN_OFFSET)
        elif row >= self.HEADER_ROWS and column >= self.DATA_COLUMN_OFFSET:
            item = self.table.item(row, column)
            if item:
                color = None
                data_row = row - self.HEADER_ROWS
                data_col = column - self.DATA_COLUMN_OFFSET
                if data_row < len(getattr(self, "default_cell_colors", [])):
                    row_colors = self.default_cell_colors[data_row]
                    if data_col < len(row_colors):
                        color = row_colors[data_col]
                self._set_cell_presence(item, not self._is_item_checked(item), save=True, default_color=color)

    def _abrir_dialog_generar(self):
        dlg = GenerarClasesDialog(self.actividadID, self.cursoAcademicoID, self)
        if dlg.exec():
            self._cargar_parrilla()

    def _abrir_dialog_afegir(self):
        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            QMessageBox.warning(self, "Error", "Selecciona un trimestre primer")
            return
        dlg = AñadirClaseDialog(self.actividadID, trimestre_id, self)
        if dlg.exec():
            self._cargar_parrilla()

    def _exportar_asistencia_pdf(self):
        trimestre_id = self.trimestre_selector.currentData()
        actividad = consultar_actividad(self.actividadID)
        nombre = re.sub(r"[^A-Za-z0-9._-]+", "_", actividad["nombre"]).strip("_") or "activitat"

        try:
            with tempfile.NamedTemporaryFile(
                prefix=f"assistencia-{nombre}-",
                suffix=".pdf",
                delete=False,
            ) as tmp:
                ruta = tmp.name
            generar_pdf_asistencias(self.actividadID, trimestre_id, ruta)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
                QMessageBox.warning(
                    self,
                    "Avís",
                    f"No s'ha pogut obrir el visor PDF del sistema.\nPDF temporal: {ruta}",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")
            
class GenerarClasesDialog(QDialog):
    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Generar classes automàticament")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID

        from controladores.curso_academico import listar_trimestres_por_cursoA
        self.trimestres = listar_trimestres_por_cursoA(cursoAcademicoID)

        self.trimestre_selector = QComboBox()
        for t in self.trimestres:
            self.trimestre_selector.addItem(str(t["nombre"].value), t["id"])

        self.dias_checkboxes = []
        dias_layout = QGridLayout()
        dias_nombres = ["Dilluns", "Dimarts", "Dimecres", "Dijous", "Divendres", "Dissabte", "Diumenge"]
        for i, nombre in enumerate(dias_nombres):
            cb = QCheckBox(nombre)
            cb.setProperty("weekday", i)
            dias_layout.addWidget(cb, i // 4, i % 4)
            self.dias_checkboxes.append(cb)
        dias_group = QGroupBox("Dies de la setmana")
        dias_group.setLayout(dias_layout)

        self.hora_inicio = QTimeEdit(QTime(9, 0))
        self.hora_fin = QTimeEdit(QTime(10, 0))
        self.intervalo_semanas = QSpinBox()
        self.intervalo_semanas.setMinimum(1)
        self.intervalo_semanas.setValue(1)

        btn_ok = QPushButton("Generar")
        set_button_variant(btn_ok, "primary")
        btn_ok.clicked.connect(self._generar_clases)

        layout = QVBoxLayout(self)

        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Trimestre:"), 0, 0)
        form_layout.addWidget(self.trimestre_selector, 0, 1)
        form_layout.addWidget(QLabel("Dies de la setmana:"), 1, 0)
        form_layout.addWidget(dias_group, 1, 1)
        form_layout.addWidget(QLabel("Hora inici:"), 2, 0)
        form_layout.addWidget(self.hora_inicio, 2, 1)
        form_layout.addWidget(QLabel("Hora fi:"), 3, 0)
        form_layout.addWidget(self.hora_fin, 3, 1)
        form_layout.addWidget(QLabel("Cada N setmanes:"), 4, 0)
        form_layout.addWidget(self.intervalo_semanas, 4, 1)

        layout.addLayout(form_layout)
        layout.addWidget(btn_ok)

    def _generar(self):
        trimestre_id = self.trimestre_selector.currentData()
        dias_semana = [cb.property("weekday") for cb in self.dias_checkboxes if cb.isChecked()]
        trimestre = next((t for t in self.trimestres if t["id"] == trimestre_id), None)

        if not trimestre or not dias_semana:
            QMessageBox.warning(self, "Error", "Trimestre o dies no vàlids")
            return

        try:
            generar_clases_semana(
                actividadID=self.actividadID,
                trimestreID=trimestre_id,
                fechaInicio=trimestre["fechaInicio"],
                fechaFin=trimestre["fechaFin"],
                horaInicio=self.hora_inicio.time().toPython(),
                horaFin=self.hora_fin.time().toPython(),
                cada_n_semanas=self.intervalo_semanas.value(),
                dias_semana=dias_semana
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'han pogut generar les classes:\n{e}")

    def _generar_clases(self):
        from controladores.clase import generar_clases_semana

        trimestre_id = self.trimestre_selector.currentData()
        if not trimestre_id:
            QMessageBox.warning(self, "Error", "Selecciona un trimestre")
            return

        dias_semana = [cb.property("weekday") for cb in self.dias_checkboxes if cb.isChecked()]
        if not dias_semana:
            QMessageBox.warning(self, "Error", "Selecciona almenys un dia de la setmana")
            return

        trimestre = next((t for t in self.trimestres if t["id"] == trimestre_id), None)
        if not trimestre:
            QMessageBox.warning(self, "Error", "Trimestre no trobat")
            return

        fecha_inicio = trimestre["fechaInicio"]
        fecha_fin = trimestre["fechaFin"]

        hora_inicio = self.hora_inicio.time().toPython()
        hora_fin = self.hora_fin.time().toPython()

        ok = QMessageBox.question(
            self,
            "Confirmar generació",
            f"Vols generar classes del {fecha_inicio} al {fecha_fin} per als dies seleccionats?",
            QMessageBox.Yes | QMessageBox.No
        )
        if ok != QMessageBox.Yes:
            return

        try:
            generar_clases_semana(
                actividadID=self.actividadID,
                trimestreID=trimestre_id,
                fechaInicio=fecha_inicio,
                fechaFin=fecha_fin,
                horaInicio=hora_inicio,
                horaFin=hora_fin,
                cada_n_semanas=self.intervalo_semanas.value(),
                dias_semana=dias_semana
            )
            QMessageBox.information(self, "Èxit", "Classes generades correctament")
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No s'han pogut generar les classes:\n{e}")


class AñadirClaseDialog(QDialog):
    def __init__(self, actividadID, trimestreID, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afegir una classe manualment")
        self.actividadID = actividadID
        self.trimestreID = trimestreID

        from PySide6.QtWidgets import QDateEdit
        from datetime import datetime

        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDate(datetime.today().date())
        self.hora_inicio = QTimeEdit(QTime(9, 0))
        self.hora_fin = QTimeEdit(QTime(10, 0))

        form = QVBoxLayout()
        form.addWidget(QLabel("Data de la classe:"))
        form.addWidget(self.fecha)
        form.addWidget(QLabel("Hora inici:"))
        form.addWidget(self.hora_inicio)
        form.addWidget(QLabel("Hora fi:"))
        form.addWidget(self.hora_fin)

        btn_ok = QPushButton("Afegir")
        set_button_variant(btn_ok, "primary")
        btn_ok.clicked.connect(self._afegir)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn_ok)

    def _afegir(self):
        try:
            registrar_clase({
                "actividadID": self.actividadID,
                "trimestreID": self.trimestreID,
                "fecha": self.fecha.date().toPython(),
                "horaInicio": self.hora_inicio.time().toPython(),
                "horaFin": self.hora_fin.time().toPython()
            })
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No s'ha pogut afegir la classe:\n{e}")




    
