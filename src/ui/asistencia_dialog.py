import re
import tempfile

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QTimeEdit, QSpinBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt, QTime, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont
from controladores.socios import consultar_socio
from controladores.trimestre import listar_clases_por_trimestre
from controladores.curso_academico import listar_trimestres_por_cursoA
from controladores.actividades import consultar_actividad, listar_inscripciones_por_Actividad
from controladores.asistencia_socio import registrar_asistenciaSocio, eliminar_asistenciaSocio, consultar_asistenciaSocio, generar_pdf_asistencias
from controladores.clase import generar_clases_semana, registrar_clase
from ui.theme import Palette, set_button_variant


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

    def __init__(self, actividadID, cursoAcademicoID, parent=None):
        super().__init__(parent)
        self.resize(1200, 700)
        self.setWindowTitle("Gestió d'assistència")
        self.actividadID = actividadID
        self.cursoAcademicoID = cursoAcademicoID
       
        self.trimestre_selector = QComboBox()
        self.btn_exportar = QPushButton("Exportar a PDF")
        self.btn_generar_dialog = QPushButton("Generar classes auto.")
        self.btn_añadir_manual = QPushButton("Afegir una classe")
        set_button_variant(self.btn_exportar, "secondary")
        set_button_variant(self.btn_generar_dialog, "primary")
        set_button_variant(self.btn_añadir_manual, "primary")
        self.btn_generar_dialog.clicked.connect(self._abrir_dialog_generar)
        self.btn_añadir_manual.clicked.connect(self._abrir_dialog_afegir)
        self.btn_exportar.clicked.connect(self._exportar_asistencia_pdf)

        self._syncing_table = False
        self.table = QTableWidget()
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setSectionsClickable(True)
        self.table.verticalHeader().sectionClicked.connect(self._seleccionar_fila)
        self.table.horizontalHeader().sectionClicked.connect(self._seleccionar_columna)
        self.table.cellClicked.connect(self._on_cell_clicked)

        top_layout = QHBoxLayout()
        label_trimestre = QLabel("Trimestre:")
        label_trimestre.setFixedWidth(70)
        top_layout.addWidget(label_trimestre)
        top_layout.addWidget(self.trimestre_selector)
        top_layout.addWidget(self.btn_exportar)
        top_layout.addWidget(self.btn_generar_dialog)
        top_layout.addWidget(self.btn_añadir_manual)

        layout = QVBoxLayout(self)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)

        self.trimestre_selector.currentIndexChanged.connect(self._cargar_parrilla)
        self._cargar_trimestres()

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

        self._syncing_table = True
        try:
            self.table.setStyleSheet(f"""
                QTableWidget::item {
                    padding: 10px;
                    border: 1px solid {Palette.BORDER};
                    background-color: {Palette.SURFACE};
                }
                QTableWidget::item:selected {
                    background-color: {Palette.SELECTION};
                    color: {Palette.TEXT};
                }
            """)
            self.table.clear()
            self.table.clearSpans()
            self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
            self.table.horizontalHeader().setVisible(False)
            self.table.verticalHeader().setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setAlternatingRowColors(True)
            self.table.setShowGrid(True)
            self.table.setWordWrap(True)
            self.table.setRowCount(data_row_count)
            self.table.setColumnCount(col_count)
            self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
            self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
            self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
            self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.table.setWordWrap(False)
            self.table.horizontalHeader().setMinimumSectionSize(80)
            self.table.horizontalHeader().setDefaultSectionSize(90)
            self.table.horizontalHeader().setStretchLastSection(False)

            # Habilitar el botón de la esquina superior izquierda de la tabla
            self.table.setCornerButtonEnabled(True)

            self.cell_items = [[None for _ in range(col_count)] for _ in range(row_count)]
            self.default_cell_colors = [[None for _ in range(col_count)] for _ in range(row_count)]
            self._month_column_ranges = {}

            self.table.setVerticalHeaderItem(0, QTableWidgetItem("Mes"))
            self.table.setVerticalHeaderItem(1, QTableWidgetItem("Dia"))
            header_font = QFont()
            header_font.setBold(True)

            from collections import defaultdict

            meses = defaultdict(list)
            for col, clase in enumerate(clases):
                fecha = clase["fecha"]
                meses[(fecha.year, fecha.month)].append(col)

                day_item = QTableWidgetItem(str(fecha.day))
                day_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                day_item.setTextAlignment(Qt.AlignCenter)
                day_item.setBackground(QColor(Palette.SURFACE_ALT))
                day_item.setFont(header_font)
                self.table.setItem(1, col, day_item)

            for _, columnas in meses.items():
                if not columnas:
                    continue
                first_col = columnas[0]
                fecha = clases[first_col]["fecha"]
                month_item = QTableWidgetItem(MESOS_CAT[fecha.month])
                month_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                month_item.setTextAlignment(Qt.AlignCenter)
                month_item.setBackground(QColor(Palette.PRIMARY_SOFT))
                month_item.setFont(header_font)
                self.table.setItem(0, first_col, month_item)
                if len(columnas) > 1:
                    self.table.setSpan(0, first_col, 1, len(columnas))
                for col in columnas:
                    self._month_column_ranges[col] = columnas

            colores_por_columna = {}
            for i, (_, columnas) in enumerate(meses.items()):
                color = QColor("#eef5e8") if i % 2 == 0 else QColor(Palette.SURFACE)
                for col in columnas:
                    colores_por_columna[col] = color

            for row, insc in enumerate(inscripciones):
                table_row = row + self.HEADER_ROWS
                socio = consultar_socio(insc["socioID"])
                header_item = QTableWidgetItem(f"{socio['nombre']} {socio['apellido1']}")
                header_item.setFlags(Qt.ItemIsEnabled)
                header_item.setTextAlignment(Qt.AlignCenter)
                self.table.setVerticalHeaderItem(table_row, header_item)

                for col, clase in enumerate(clases):
                    asistencia = consultar_asistenciaSocio(insc["socioID"], clase["id"])
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    item.setCheckState(Qt.Checked if asistencia else Qt.Unchecked)
                    item.setData(Qt.UserRole, (insc["socioID"], clase["id"]))
                    item.setData(Qt.TextAlignmentRole, Qt.AlignCenter)

                    default_color = colores_por_columna.get(col)
                    if default_color:
                        item.setBackground(default_color)
                    else:
                        item.setData(Qt.BackgroundRole, None)

                    self.table.setItem(table_row, col, item)
                    self.cell_items[row][col] = item
                    self.default_cell_colors[row][col] = default_color

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            self.table.setRowHeight(0, 28)
            self.table.setRowHeight(1, 28)
        finally:
            self._syncing_table = False

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
                if color:
                    item.setBackground(color)
                else:
                    item.setData(Qt.BackgroundRole, None)

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

        todos_marcados = all(item.checkState() == Qt.Checked for item in columna_items)
        nuevo_estado = Qt.Unchecked if todos_marcados else Qt.Checked

        for item in columna_items:
            if item.checkState() != nuevo_estado:
                item.setCheckState(nuevo_estado)

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
            for f in filas:
                self._seleccionar_fila(f + self.HEADER_ROWS)
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

        if not fila_items:
            return

        todos_marcados = all(item.checkState() == Qt.Checked for item in fila_items)
        nuevo_estado = Qt.Unchecked if todos_marcados else Qt.Checked

        for item in fila_items:
            if item.checkState() != nuevo_estado:
                item.setCheckState(nuevo_estado)
    
    def keyPressEvent(self, event):
        from PySide6.QtGui import QKeyEvent
        from controladores.clase import eliminar_clase
        if isinstance(event, QKeyEvent) and event.key() == Qt.Key_Delete:
            columnas = sorted(set(index.column() for index in self.table.selectedIndexes()))
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
        checked = item.checkState() == Qt.Checked
        self._guardar_asistencia(socio_id, clase_id, checked)

    def _on_cell_clicked(self, row, column):
        if row == 0:
            columnas = getattr(self, "_month_column_ranges", {}).get(column, [column])
            self._seleccionar_columnas(columnas)
        elif row == 1:
            self._seleccionar_columna(column)

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




    
