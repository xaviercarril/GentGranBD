from controladores.actividades import listar_actividades, consultar_actividad, eliminar_actividad
from PySide6.QtWidgets import (
  QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableView,
  QPushButton, QMessageBox, QLineEdit, QLabel
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtCore import Qt, QSize
from ui.actividad_dialog import ActividadDialog
from ui.socio_detail import SocioDetailWidget
from ui.actividad_detail import ActividadDetailWidget
from ui.table_models import DictTableModel

class ActividadesTab(QWidget):
  # ==========================================================
  #   ACTIVITATS
  # ==========================================================
  def __init__(self, parent=None):
    super().__init__(parent)
    self.activitats_tabs = QTabWidget()

    # --- Cursos ---
    self._init_cursos_tab()

    # --- Tallers ---
    self._init_tallers_tab()

    # Add main tab
    page = QWidget()
    ly = QVBoxLayout(page)
    ly.addWidget(self.activitats_tabs)
    self.setLayout(ly)

    self._refresh_cursos()
    self._refresh_tallers()

    self.table_cursos.selectionModel().currentRowChanged.connect(self._row_changed_curso)

  def _init_cursos_tab(self):
    self.table_cursos = QTableView()
    self._search_box_cursos = QLineEdit()
    self._search_box_cursos.setPlaceholderText("Cerca cursos...")
    self._search_box_cursos.textChanged.connect(self._filtrar_cursos)

    # Configure table
    self.table_cursos.verticalHeader().setVisible(False)
    self.table_cursos.setSelectionBehavior(QTableView.SelectRows)
    self.table_cursos.setSelectionMode(QTableView.SingleSelection)
    self.table_cursos.setAlternatingRowColors(True)
    self.table_cursos.setStyleSheet("""
      QTableView::item:selected {
        background: #c5d6a1;
        color: black;
      }
      QTableView::item:selected:active {
        background: #a8bd88;
      }
    """)
    self._refresh_cursos()

    self.detail_curso = ActividadDetailWidget(tipo="curso")
    self.detail_curso.saved.connect(self._refresh_cursos)

    

    # Layout for cursos
    hlayout = QHBoxLayout()
    hlayout.addWidget(self.table_cursos, stretch=3)
    self.detail_curso.setFixedWidth(300)
    hlayout.addWidget(self.detail_curso, stretch=0)

    # Buttons for cursos
    btn_nou_curso = QPushButton("Nou Curs")
    btn_nou_curso.setIcon(QIcon("ui/assets/plus.svg"))
    btn_nou_curso.setIconSize(QSize(16, 16))
    btn_esborrar_curso = QPushButton("Eliminar Curs")
    btn_esborrar_curso.setIcon(QIcon("ui/assets/minus.svg"))
    btn_esborrar_curso.setIconSize(QSize(16, 16))

    btn_nou_curso.clicked.connect(self._dialog_nova_actividad)
    btn_esborrar_curso.clicked.connect(self._eliminar_actividad_curso)

    page_cursos = QWidget()
    lyt = QVBoxLayout(page_cursos)
    top_buttons_c = QHBoxLayout()
    top_buttons_c.addWidget(btn_nou_curso)
    top_buttons_c.addWidget(btn_esborrar_curso)
    top_buttons_c.addStretch()

    lyt.addLayout(top_buttons_c)
    lyt.addWidget(self._search_box_cursos)
    lyt.addLayout(hlayout, 1)

    self.activitats_tabs.addTab(page_cursos, "Cursos")


  def _init_tallers_tab(self):
    self.table_tallers = QTableView()
    self._search_box_tallers = QLineEdit()
    self._search_box_tallers.setPlaceholderText("Cerca tallers...")
    self._search_box_tallers.textChanged.connect(self._filtrar_tallers)

    self.table_tallers.setSelectionBehavior(QTableView.SelectRows)

    btn_nou_taller = QPushButton("Nou taller")
    btn_esborrar_taller = QPushButton("Eliminar")

    btn_nou_taller.clicked.connect(self._dialog_nova_actividad)
    btn_esborrar_taller.clicked.connect(self._eliminar_actividad_taller)

    page_tallers = QWidget()
    lyt = QVBoxLayout(page_tallers)
    top_buttons_t = QHBoxLayout()
    top_buttons_t.addWidget(btn_nou_taller)
    top_buttons_t.addWidget(btn_esborrar_taller)
    top_buttons_t.addStretch()

    lyt.addLayout(top_buttons_t)
    lyt.addWidget(self._search_box_tallers)

    hlayout_tallers = QHBoxLayout()
    hlayout_tallers.addWidget(self.table_tallers, stretch=3)
    self.detail_taller = ActividadDetailWidget(tipo="taller")
    self.detail_taller.saved.connect(self._refresh_tallers)
    hlayout_tallers.addWidget(self.detail_taller)
    self.detail_taller.setFixedWidth(300)
    lyt.addLayout(hlayout_tallers, 1)

    self.activitats_tabs.addTab(page_tallers, "Tallers")

  def _refresh_cursos(self):
    rows = listar_actividades()
    self._all_cursos = [a for a in rows if (a.get("tipo") or "").lower() in ["curs", "curso"]]
    headers = [
      ("ID", "id"),
      ("Nom", "nombre"),
      ("Tipus", "tipo"),
      ("Màxim alumnes", "max_alumnos"),
    ]
    filtered_rows = self._filter_activitats_rows(self._search_box_cursos.text(), self._all_cursos)
    model = DictTableModel(filtered_rows, headers)
    self.table_cursos.setModel(model)
    self.table_cursos.resizeColumnsToContents()
    self.table_cursos.hideColumn(0)
    self.table_cursos.hideColumn(2)

    new_sel = self.table_cursos.selectionModel()
    try:
      new_sel.currentRowChanged.disconnect()
    except (TypeError, RuntimeError):
      pass
    new_sel.currentRowChanged.connect(self._row_changed_curso)
    self._sel_model = new_sel
    
  def _refresh_tallers(self):
    rows = listar_actividades()
    self._all_tallers = [a for a in rows if (a.get("tipo") or "").lower() in ["taller", "tallers"]]
    headers = [
      ("ID", "id"),
      ("Nom", "nombre"),
      ("Tipus", "tipo"),
      ("Màxim alumnes", "max_alumnos"),
    ]
    filtered_rows = self._filter_activitats_rows(self._search_box_tallers.text(), self._all_tallers)
    model = DictTableModel(filtered_rows, headers)
    self.table_tallers.setModel(model)
    self.table_tallers.resizeColumnsToContents()
    self.table_tallers.hideColumn(0)
    self.table_tallers.hideColumn(2)

    sel = self.table_tallers.selectionModel()
    try:
        sel.currentRowChanged.disconnect(self._row_changed_taller)
    except (TypeError, RuntimeError):
        pass
    sel.currentRowChanged.connect(self._row_changed_taller)

  def _filter_activitats_rows(self, text, rows):
    if not text.strip():
      return rows
    text = text.lower()
    def matches(a):
      return any(
        text in str(value).lower() if value else ""
        for value in a.values()
      )
    return [a for a in rows if matches(a)]

  def _filtrar_cursos(self):
    self._refresh_cursos()

  def _filtrar_tallers(self):
    self._refresh_tallers()

  def _row_changed_curso(self, curr, _prev):
    if not curr.isValid():
      self.detail_curso.load(None)
      return
    actividad_id = self.table_cursos.model().rows[curr.row()]["id"]
    self.detail_curso.load(actividad_id)

  def _row_changed_taller(self, curr, _prev):
    if not curr.isValid():
      self.detail_taller.load(None)
      return
    actividad_id = self.table_tallers.model().rows[curr.row()]["id"]
    self.detail_taller.load(actividad_id)

  def _dialog_nova_actividad(self):
    dlg = ActividadDialog(self)
    if dlg.exec():
      self._refresh_cursos()
      self._refresh_tallers()

  def _eliminar_actividad_curso(self):
    sel = self.table_cursos.selectionModel().selectedRows()
    if not sel:
      return
    row = sel[0].row()
    actividad = self.table_cursos.model().rows[row]
    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(
      f"Vols eliminar l'activitat «{actividad['nombre']}» (ID {actividad['id']})?\n"
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
    self._refresh_cursos()
    self.detail_curso.load(None)

  def _eliminar_actividad_taller(self):
    sel = self.table_tallers.selectionModel().selectedRows()
    if not sel:
      return
    row = sel[0].row()
    actividad = self.table_tallers.model().rows[row]
    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(
      f"Vols eliminar l'activitat «{actividad['nombre']}» (ID {actividad['id']})?\n"
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
    self._refresh_tallers()
    self.detail_taller.load(None)
