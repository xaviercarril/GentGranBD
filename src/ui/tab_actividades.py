import re
import tempfile

from controladores.actividades import listar_actividades, consultar_actividad, eliminar_actividad, listar_inscripciones_por_Actividad
from controladores.personal import consultar_personal
from controladores.curso_academico import listar_cursosA, listar_actividades_por_CursoAcademico
from PySide6.QtWidgets import (
  QWidget, QVBoxLayout, QHBoxLayout, QTableView,
  QPushButton, QMessageBox, QLineEdit, QComboBox, QSizePolicy, QTabWidget, QMenu
)
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtCore import QSize, QModelIndex, QItemSelectionModel, Qt, QUrl, QTimer
from exportador.pdf_actividades import generar_pdf_actividades_curso
from ui.actividad_dialog import ActividadDialog
from ui.actividad_detail import ActividadDetailWidget
from ui.table_models import DictTableModel
from ui.table_utils import add_table_copy_actions, enable_table_copy
from ui.asistencia_dialog import AsistenciaDialog
from ui.theme import set_button_icon, set_button_variant
from models import EstadoInscripcion

class ActividadesTab(QWidget):
  def __init__(self, parent=None):
    super().__init__(parent)
    self._sort_key = "nombre"
    self._sort_order = Qt.AscendingOrder
    self._current_export_rows = []
    self._tipo_actual = "CURS"

    self._curso_selector = QComboBox()
    self._curso_selector.addItem("Tots els cursos", None)
    for curso in listar_cursosA():
        self._curso_selector.addItem(curso["nombre"], curso["id"])
    from datetime import date
    hoy = date.today()
    for i in range(1, self._curso_selector.count()):
        curso_id = self._curso_selector.itemData(i)
        curso_nombre = self._curso_selector.itemText(i)
        for curso in listar_cursosA():
            if curso["id"] == curso_id and curso["fechaInicio"] <= hoy <= curso["fechaFin"]:
                self._curso_selector.setCurrentIndex(i)
                break
    self._curso_selector.currentIndexChanged.connect(self._refresh_activitats)
    self._curso_selector.view().window().installEventFilter(self)

    self.table_activitats = QTableView()
    self._search_box = QLineEdit()
    self._search_box.setPlaceholderText("Cerca cursos...")
    self._search_box.textChanged.connect(self._refresh_activitats)

    self.table_activitats.verticalHeader().setVisible(False)
    self.table_activitats.setSelectionBehavior(QTableView.SelectRows)
    self.table_activitats.setSelectionMode(QTableView.SingleSelection)
    enable_table_copy(self.table_activitats)
    self.table_activitats.setAlternatingRowColors(True)
    self.table_activitats.setContextMenuPolicy(Qt.CustomContextMenu)
    self.table_activitats.customContextMenuRequested.connect(self._show_actividad_context_menu)
    self.table_activitats.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    header = self.table_activitats.horizontalHeader()
    header.setSectionsClickable(True)
    header.sectionClicked.connect(self._sort_by_header)
    self.table_activitats.doubleClicked.connect(self._abrir_asistencia)

    self.detail_actividad = ActividadDetailWidget()
    self.detail_actividad.saved.connect(self._refresh_activitats)
    self.detail_actividad.setMinimumWidth(460)
    self.detail_actividad.setMaximumWidth(620)
    self.detail_actividad.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    self.inscrits_panel = self.detail_actividad.inscrits_panel
    self.inscrits_panel.setParent(self)

    self.btn_nova_actividad = QPushButton("Nou Curs")
    set_button_icon(self.btn_nova_actividad, "ui/assets/plus.svg")
    set_button_variant(self.btn_nova_actividad, "primary")
    self.btn_eliminar_actividad = QPushButton("Eliminar Curs")
    set_button_icon(self.btn_eliminar_actividad, "ui/assets/minus.svg")
    set_button_variant(self.btn_eliminar_actividad, "danger")
    self.btn_exportar_activitats = QPushButton("Exportar PDF")
    set_button_icon(self.btn_exportar_activitats, "ui/assets/pdf.svg")

    self.btn_nova_actividad.clicked.connect(self._dialog_nova_actividad)
    self.btn_eliminar_actividad.clicked.connect(self._eliminar_actividad)
    self.btn_exportar_activitats.clicked.connect(self._exportar_activitats_pdf)

    main_layout = QVBoxLayout(self)
    self.subtabs = QTabWidget()
    self.cursos_tab = QWidget()
    self.viatges_tab = QWidget()
    self.cursos_tab.setLayout(QVBoxLayout())
    self.viatges_tab.setLayout(QVBoxLayout())
    self.cursos_tab.layout().setContentsMargins(8, 8, 8, 8)
    self.viatges_tab.layout().setContentsMargins(8, 8, 8, 8)
    self.subtabs.addTab(self.cursos_tab, "Cursos")
    self.subtabs.addTab(self.viatges_tab, "Viatges")
    self.subtabs.currentChanged.connect(self._on_subtab_changed)
    main_layout.addWidget(self.subtabs, 1)

    top_buttons = QHBoxLayout()
    top_buttons.addWidget(self.btn_nova_actividad)
    top_buttons.addWidget(self.btn_eliminar_actividad)
    top_buttons.addWidget(self.btn_exportar_activitats)
    top_buttons.addStretch()

    self._content_widget = QWidget()
    content_layout = QVBoxLayout(self._content_widget)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.addWidget(self._curso_selector)
    content_layout.addLayout(top_buttons)
    content_layout.addWidget(self._search_box)

    mid_layout = QHBoxLayout()
    mid_layout.setContentsMargins(0, 0, 0, 0)
    mid_layout.setSpacing(12)
    mid_layout.addWidget(self.table_activitats, stretch=4)
    mid_layout.addWidget(self.detail_actividad, stretch=3)
    top_content = QWidget()
    top_content.setLayout(mid_layout)
    top_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    top_height = self.detail_actividad.sizeHint().height()
    top_content.setFixedHeight(top_height)
    self.table_activitats.setFixedHeight(top_height)
    self.detail_actividad.set_top_section_height(top_height)

    content_layout.addWidget(top_content, 0)
    content_layout.addWidget(self.inscrits_panel, 2)
    self.cursos_tab.layout().addWidget(self._content_widget)

    self._refresh_activitats()

  def _refresh_activitats(self):
    """Actualiza la lista de actividades y el detalle."""

    curso_id = self._curso_selector.currentData()
    self.btn_nova_actividad.setEnabled(curso_id is not None)
    rows = (
      listar_actividades_por_CursoAcademico(curso_id, tipo=self._tipo_actual)
      if curso_id
      else listar_actividades(tipo=self._tipo_actual)
    )
    headers = self._headers_with_sort_indicator([
      ("ID", "id"),
      ("Nom", "nombre"),
      ("Responsable" if self._tipo_actual == "VIATGE" else "Personal", "personal_nombre"),
      ("Preu viatge" if self._tipo_actual == "VIATGE" else "Preu matrícula", f"precio_matricula"),
      ("Participants" if self._tipo_actual == "VIATGE" else "Inscrits", "inscritos"),
      ("Places" if self._tipo_actual == "VIATGE" else "Màxim alumnes", "numMaxAlumnos"),
      ("Descripció / itinerari" if self._tipo_actual == "VIATGE" else "Descripció", "descripcion")
    ])

    # Enriquecer datos con nombre del personal y contar inscritos
    for row in rows:
        row["precio_matricula"] = f"{row['precio_matricula']:.2f} €"
        try:
            personal = consultar_personal(row["personalID"]) if row["personalID"] else None
            row["personal_nombre"] = f"{personal['nombre']} {personal['apellido1']}" if personal else "Desconegut"
        except Exception:
            row["personal_nombre"] = "Desconegut"

        try:
            inscripciones = listar_inscripciones_por_Actividad(row["id"])
            row["inscritos"] = sum(
                1 for ins in inscripciones
                if getattr(ins.get("estado"), "value", ins.get("estado")) == EstadoInscripcion.INSCRIT.value
            )
        except Exception:
            row["inscritos"] = "?"

    filtered_rows = self._filter_activitats_rows(self._search_box.text(), rows)
    filtered_rows = self._sort_rows(filtered_rows)
    self._current_export_rows = filtered_rows

    # Guardar ID seleccionado
    selected_id = None
    sel_model = self.table_activitats.selectionModel()
    if sel_model and sel_model.currentIndex().isValid():
        selected_id = self.table_activitats.model().rows[sel_model.currentIndex().row()]["id"]

    # Asignar nuevo modelo
    model = DictTableModel(filtered_rows, headers)
    self.table_activitats.setModel(model)
    self.table_activitats.resizeColumnsToContents()
    self.table_activitats.hideColumn(0)

    # Conectar el nuevo modelo
    sel_model = self.table_activitats.selectionModel()
    sel_model.currentChanged.connect(self._row_changed_actividad)

    # Restaurar selección
    restored_selection = False
    if selected_id is not None:
        for row_idx, r in enumerate(model.rows):
            if r["id"] == selected_id:
                index = model.index(row_idx, 0)
                sel_model.setCurrentIndex(index, QItemSelectionModel.SelectCurrent | QItemSelectionModel.Rows)
                restored_selection = True
                break
    if not restored_selection:
        self.detail_actividad.load(None)

  def _filter_activitats_rows(self, text, rows):
    if not text.strip():
      return rows
    text = text.lower()
    return [a for a in rows if any(text in str(value).lower() if value else "" for value in a.values())]

  def _headers_with_sort_indicator(self, headers):
    indicator = "▲" if self._sort_order == Qt.AscendingOrder else "▼"
    return [
      (f"{label} {indicator}" if key == self._sort_key else label, key)
      for label, key in headers
    ]

  def _sort_rows(self, rows):
    def value_for_sort(row):
      value = row.get(self._sort_key)
      if value is None:
        return (1, "")
      if self._sort_key in {"id", "inscritos", "numMaxAlumnos"}:
        try:
          return (0, int(value))
        except (TypeError, ValueError):
          return (0, str(value))
      if self._sort_key == "precio_matricula":
        try:
          return (0, float(str(value).replace("€", "").replace(",", ".").strip()))
        except (TypeError, ValueError):
          return (0, str(value))
      if isinstance(value, str):
        return (0, value.casefold())
      return (0, str(value).casefold())

    return sorted(
      rows,
      key=value_for_sort,
      reverse=self._sort_order == Qt.DescendingOrder,
    )

  def _sort_by_header(self, section):
    model = self.table_activitats.model()
    if not model or section < 0 or section >= len(getattr(model, "keys", [])):
      return
    key = model.keys[section]
    if key == self._sort_key:
      self._sort_order = Qt.DescendingOrder if self._sort_order == Qt.AscendingOrder else Qt.AscendingOrder
    else:
      self._sort_key = key
      self._sort_order = Qt.AscendingOrder
    self._refresh_activitats()

  def _row_changed_actividad(self, current: QModelIndex, previous: QModelIndex):
    if not current.isValid():
      self.detail_actividad.load(None)
      return
    actividadID = self.table_activitats.model().rows[current.row()]["id"]
    self.detail_actividad.load(actividadID)

  def _abrir_asistencia(self, index: QModelIndex):
    if not index.isValid():
        return
    actividad = self.table_activitats.model().rows[index.row()]
    dlg = AsistenciaDialog(actividad["id"], actividad["cursoAcademico_id"], self)
    dlg.exec()

  def _show_actividad_context_menu(self, pos):
    index = self.table_activitats.indexAt(pos)
    if not index.isValid():
      return

    self.table_activitats.setCurrentIndex(index)
    self.table_activitats.selectionModel().select(
      index,
      QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )

    menu = QMenu(self)
    add_table_copy_actions(menu, self.table_activitats, index)
    menu.addSeparator()
    asistencia_action = menu.addAction("Obrir assistència")
    asistencia_action.triggered.connect(
      lambda _checked=False, idx=index: self._abrir_asistencia(idx)
    )
    menu.exec(self.table_activitats.viewport().mapToGlobal(pos))

  def _dialog_nova_actividad(self):
    curso_id = self._curso_selector.currentData()
    if curso_id is None:
        from datetime import date
        hoy = date.today()
        for c in listar_cursosA():
            if c["fechaInicio"] <= hoy <= c["fechaFin"]:
                curso_id = c["id"]
                break
    dlg = ActividadDialog(self, cursoAcademico_id=curso_id, tipo=self._tipo_actual)
    if dlg.exec():
        self._refresh_activitats()

  def _eliminar_actividad(self):
    sel = self.table_activitats.selectionModel().selectedRows()
    if not sel:
      return
    row = sel[0].row()
    actividad = self.table_activitats.model().rows[row]
    tipo_label = "viatge" if self._tipo_actual == "VIATGE" else "curs"
    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(
      f"Vols eliminar el {tipo_label} «{actividad['nombre']}» (ID {actividad['id']})?\n"
      "Aquesta acció no es pot desfer."
    )
    box.setIcon(QMessageBox.Warning)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.button(QMessageBox.Yes).setText("Sí")
    box.button(QMessageBox.No).setText("No")
    reply = box.exec()
    if reply != QMessageBox.Yes:
      return
    eliminar_actividad(actividad["id"])
    self._refresh_activitats()
    self.detail_actividad.load(None)

  def _exportar_activitats_pdf(self):
    curso_nombre = self._curso_selector.currentText()
    tipo_nom = "viatges" if self._tipo_actual == "VIATGE" else "cursos"
    export_title = f"{curso_nombre} - {tipo_nom.capitalize()}"
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", f"{curso_nombre}-{tipo_nom}").strip("_") or "activitats"
    try:
      with tempfile.NamedTemporaryFile(
        prefix=f"{tipo_nom}-{safe_name}-",
        suffix=".pdf",
        delete=False,
      ) as tmp:
        ruta = tmp.name
      generar_pdf_actividades_curso(export_title, self._current_export_rows, ruta)
      if not QDesktopServices.openUrl(QUrl.fromLocalFile(ruta)):
        QMessageBox.warning(
          self,
          "Avís",
          f"No s'ha pogut obrir el visor PDF del sistema.\nPDF temporal: {ruta}",
        )
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar el PDF:\n{e}")

  def _actualizar_cursos(self):
    self._curso_selector.blockSignals(True)
    curso_actual = self._curso_selector.currentData()
    self._curso_selector.clear()
    self._curso_selector.addItem("Tots els cursos", None)
    for curso in listar_cursosA():
        self._curso_selector.addItem(curso["nombre"], curso["id"])
    index = self._curso_selector.findData(curso_actual)
    self._curso_selector.setCurrentIndex(index if index >= 0 else 0)
    self._curso_selector.blockSignals(False)

  def eventFilter(self, source, event):
    from PySide6.QtCore import QEvent
    if event.type() == QEvent.Show and source is self._curso_selector.view().window():
        self._actualizar_cursos()
    return super().eventFilter(source, event)

  def showEvent(self, event):
    super().showEvent(event)
    self._refresh_activitats()

  def _on_subtab_changed(self, index):
    window = self.window()
    previous_size = window.size() if window else None
    self._tipo_actual = "VIATGE" if index == 1 else "CURS"
    is_viatge = self._tipo_actual == "VIATGE"
    target_tab = self.viatges_tab if is_viatge else self.cursos_tab
    target_tab.layout().addWidget(self._content_widget)
    self.btn_nova_actividad.setText("Nou Viatge" if is_viatge else "Nou Curs")
    self.btn_eliminar_actividad.setText("Eliminar Viatge" if is_viatge else "Eliminar Curs")
    self._search_box.setPlaceholderText("Cerca viatges..." if is_viatge else "Cerca cursos...")
    self.detail_actividad.set_tipo_actividad(self._tipo_actual)
    self.detail_actividad.load(None)
    self._refresh_activitats()
    if window and previous_size:
      QTimer.singleShot(0, lambda: window.resize(previous_size))
