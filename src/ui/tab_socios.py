# src/ui/tab_socios.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QLineEdit, QMessageBox
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize
from PySide6.QtCore import QEvent, Qt
from ui.table_models import DictTableModel
from ui.socio_detail import SocioDetailWidget
from controladores.socios import (
    listar_socios, eliminar_socio, consultar_socio, generar_carnet_pdf
)
from ui.socio_dialog import SocioDialog

class SociosTab(QWidget):
  # ==========================================================
  #   SOCIS
  # ==========================================================
  def __init__(self, parent=None):
    super().__init__(parent)
    # Taula esquerra
    self.table_socis = QTableView()

    # Caixa de cerca
    self._search_box = QLineEdit()
    self._search_box.setPlaceholderText("Cerca...")
    self._search_box.textChanged.connect(self._filtrar_socios)

    # Oculta la columna de número de fila
    self.table_socis.verticalHeader().setVisible(False)
    # -- Configuració de selecció i estil --
    self.table_socis.setSelectionBehavior(QTableView.SelectRows)
    self.table_socis.setSelectionMode(QTableView.SingleSelection)
    self.table_socis.setAlternatingRowColors(True)
    self.table_socis.setStyleSheet("""
      QTableView::item:selected {
        background: #c5d6a1;
        color: black;
      }
      QTableView::item:selected:active {
        background: #a8bd88;
      }
    """)
    self._refresh_socios()

    # Panell de detall dreta
    self.detail = SocioDetailWidget()
    self.detail.saved.connect(self._refresh_socios)

    # Quan seleccionem fila → carregar detall
    self.table_socis.selectionModel().currentRowChanged.connect(self._row_changed)
    self.table_socis.doubleClicked.connect(self._abrir_inscripciones_socio)

    # Layout horitzontal amb taula (flexible) and detall (ample fix, no movable)
    hlayout = QHBoxLayout()
    hlayout.addWidget(self.table_socis, stretch=3)
    self.detail.setFixedWidth(300)
    hlayout.addWidget(self.detail, stretch=0)

    # Botons alta / baixa
    btn_nou = QPushButton("Nou soci")
    btn_nou.setIcon(QIcon("ui/assets/plus.svg"))
    btn_nou.setIconSize(QSize(16, 16))
    btn_esborrar = QPushButton("Eliminar")
    btn_esborrar.setIcon(QIcon("ui/assets/minus.svg"))
    btn_esborrar.setIconSize(QSize(16, 16))
    btn_carnet = QPushButton("Generar Carnet")
    btn_carnet.setIcon(QIcon("ui/assets/id-card.svg"))
    btn_carnet.setIconSize(QSize(16, 16))
    btn_carnet.clicked.connect(self._generar_carnet_socio)
    # --- PDF LOPD Button ---
    btn_lopd = QPushButton("Generar LOPD")
    btn_lopd.setIcon(QIcon("ui/assets/signature.svg"))
    btn_lopd.setIconSize(QSize(16, 16))
    btn_lopd.clicked.connect(self._generar_lopd_pdf)
    btn_nou.clicked.connect(self._dialog_nou_socio)
    btn_esborrar.clicked.connect(self._eliminar_socio)

    top_buttons = QHBoxLayout()
    top_buttons.addWidget(btn_nou)
    top_buttons.addWidget(btn_esborrar)
    top_buttons.addWidget(btn_carnet)
    top_buttons.addWidget(btn_lopd)
    top_buttons.addStretch()

    page = QWidget()
    ly = QVBoxLayout(page)
    ly.addLayout(top_buttons)
    ly.addWidget(self._search_box)
    ly.addLayout(hlayout, 1)
    self.setLayout(ly)
    self.table_socis.installEventFilter(self)

  def _refresh_socios(self):
    rows = listar_socios()
    self._all_socios = rows
    headers = [
      ("Soci ID", "id"),
      ("DNI/NIE", "dniNie"),
      ("Nom", "nombre"),
      ("1r Cognom", "apellido1"),
      ("2n Cognom", "apellido2"),
      ("Adreça", "direccion"),
      ("Tel. fix", "telefonoFijo"),
      ("Mòbil", "telefonoMovil"),
      ("Email", "email"),
      ("Grup Difusió", "grupoDifusion"),
    ]
    filtered_rows = self._filter_rows(self._search_box.text())
    model = DictTableModel(filtered_rows, headers)
    self.table_socis.setModel(model)
    self.table_socis.resizeColumnsToContents()
    # self.table_socis.hideColumn(0)

    new_sel = self.table_socis.selectionModel()
    try:
      new_sel.currentRowChanged.disconnect()
    except (TypeError, RuntimeError):
      pass
    new_sel.currentRowChanged.connect(self._row_changed)
    self._sel_model = new_sel

  def _dialog_nou_socio(self):
    dlg = SocioDialog(self)
    if dlg.exec():
      self._refresh_socios()

  def _eliminar_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    row = sel[0].row()
    socio = self.table_socis.model().rows[row]
    nom_complet = f"{socio['nombre']} {socio.get('apellido1', '')}".strip()

    box = QMessageBox(self)
    box.setWindowTitle("Confirmar eliminació")
    box.setText(
      f"Vols eliminar el soci «{nom_complet}» (ID {socio['id']})?\n"
      "Aquesta acció no es pot desfer."
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
    box.button(QMessageBox.Yes).setText("Sí")
    box.button(QMessageBox.No).setText("No")

    reply = box.exec()

    if reply != QMessageBox.Yes:
      return

    eliminar_socio(socio["id"])
    self._refresh_socios()
    self.detail.load(None)

  def _row_changed(self, curr, _prev):
    if not curr.isValid():
      self.detail.load(None)
      return
    socioID = self.table_socis.model().rows[curr.row()]["id"]
    self.detail.load(socioID)

  def _generar_carnet_socio(self):
    sel = self.table_socis.selectionModel().selectedRows()
    if not sel:
      QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
      return

    row = sel[0].row()
    socio = self.table_socis.model().rows[row]

    from PySide6.QtWidgets import QFileDialog
    suggested = f"carnet_{socio['id']:06d}.pdf"
    pdf_path, _ = QFileDialog.getSaveFileName(self, "Desar carnet PDF", suggested, "PDF Files (*.pdf)")
    if not pdf_path:
      return
    try:
      generar_carnet_pdf(socio['id'], pdf_path)
    except Exception as e:
      QMessageBox.critical(self, "Error", f"No s'ha pogut generar el carnet:\n{e}")
      return

    try:
      from PySide6.QtPdf import QPdfDocument
      from PySide6.QtPrintSupport import QPrinter, QPrintDialog

      doc = QPdfDocument()
      load_result = doc.load(pdf_path)
      if load_result != 0:
        raise Exception("Error loading PDF")

      printer = QPrinter(QPrinter.HighResolution)
      dialog = QPrintDialog(printer, self)
      if dialog.exec() == QPrintDialog.Accepted:
        raise AttributeError("QPdfDocument has no print method")
    except Exception:
      import os
      import sys
      if sys.platform.startswith("darwin"):
        os.system(f'open "{pdf_path}"')
      elif sys.platform.startswith("win"):
        try:
          os.startfile(pdf_path)
        except Exception:
          # Fallback via Explorer
          os.system(f'start "" "{pdf_path}"')
      else:
        os.system(f'xdg-open "{pdf_path}"')

  def _filtrar_socios(self):
    self._refresh_socios()

  def _filter_rows(self, text):
    if not text.strip():
      return self._all_socios
    text = text.lower()

    def matches(s):
      return any(
        text in str(value).lower() if value else ""
        for value in s.values()
      )

    return [s for s in self._all_socios if matches(s)]

  def _abrir_inscripciones_socio(self, index):
      if not index.isValid():
          return
      socio = self.table_socis.model().rows[index.row()]
      from ui.inscripciones_dialog import InscripcionesDialog
      dlg = InscripcionesDialog(socio["id"], self)
      dlg.exec()

  def showEvent(self, event):
      super().showEvent(event)
      self._refresh_socios()
  def eventFilter(self, obj, event):
      if obj == self.table_socis and event.type() == QEvent.KeyPress:
          if event.key() == Qt.Key_Delete:
              self._eliminar_socio()
              return True
      return super().eventFilter(obj, event)
  
  def _generar_lopd_pdf(self):
      sel = self.table_socis.selectionModel().selectedRows()
      if not sel:
          QMessageBox.warning(self, "Error", "No s'ha seleccionat cap soci.")
          return

      row = sel[0].row()
      socio = self.table_socis.model().rows[row]

      from controladores.socios import generar_pdf_LOPD
      from PySide6.QtWidgets import QFileDialog

      output_path, _ = QFileDialog.getSaveFileName(self, "Desar PDF LOPD", f"lopd_{socio['id']}.pdf", "PDF Files (*.pdf)")
      if not output_path:
          return

      generar_pdf_LOPD(socio['id'], output_path)
      QMessageBox.information(self, "Èxit", "El PDF s'ha generat correctament.")