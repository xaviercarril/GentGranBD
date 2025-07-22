from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QLineEdit, QMessageBox, QTabWidget
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize

from controladores.personal import listar_profesores, eliminar_personal, listar_voluntarios
from ui.profe_detail import ProfeDetailWidget
from ui.profe_dialog import ProfeDialog
from ui.table_models import DictTableModel
from ui.volun_detail import VolunDetailWidget
from ui.volun_dialog import VolunDialog

class PersonalTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.subtabs = QTabWidget()
        self.profe_tab = QWidget()
        self.volun_tab = QWidget()

        self.subtabs.addTab(self.profe_tab, "Professors")
        self.subtabs.addTab(self.volun_tab, "Voluntaris")

        layout.addWidget(self.subtabs)

        self._init_profe_tab()
        self._init_volun_tab()

    def _init_profe_tab(self):
        layout = QVBoxLayout()
        # Initialize the profes table
        self.prof_table = QTableView()

        # Add search box
        self.search_box_profe = QLineEdit()
        self.search_box_profe.setPlaceholderText("Cerca professors...")
        self.search_box_profe.textChanged.connect(self._filter_profe)

        # Oculta la columna de número de fila
        self.prof_table.verticalHeader().setVisible(False)
        # -- Configuració de selecció i estil --
        self.prof_table.setSelectionBehavior(QTableView.SelectRows)
        self.prof_table.setSelectionMode(QTableView.SingleSelection)
        self.prof_table.setAlternatingRowColors(True)
        self.prof_table.setStyleSheet("""
            QTableView::item:selected {
                background: #c5d6a1;
                color: black;
            }
            QTableView::item:selected:active {
                background: #a8bd88;
            }
        """)
        self._refresh_profe()

        # Panell de detall dreta
        self.detail_profe = ProfeDetailWidget()
        self.detail_profe.saved.connect(self._refresh_profe)

        # Connect selection change to detail view
        self.prof_table.selectionModel().currentRowChanged.connect(self._row_changed_profe)

        # Layout for buttons
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.prof_table, stretch=3)
        self.detail_profe.setFixedWidth(300)
        hlayout.addWidget(self.detail_profe, stretch=0)

        btn_nou = QPushButton("Nou Professor")
        btn_nou.setIcon(QIcon("ui/assets/plus.svg"))
        btn_nou.setIconSize(QSize(16, 16))
        btn_eliminar = QPushButton("Eliminar Professor")
        btn_eliminar.setIcon(QIcon("ui/assets/minus.svg"))
        btn_eliminar.setIconSize(QSize(16, 16))
        btn_nou.clicked.connect(self._dialog_nou_profe)
        btn_eliminar.clicked.connect(self._eliminar_profe)

        top_buttons = QHBoxLayout()
        top_buttons.addWidget(btn_nou)
        top_buttons.addWidget(btn_eliminar)
        top_buttons.addStretch()

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addLayout(top_buttons)
        ly.addWidget(self.search_box_profe)
        ly.addLayout(hlayout, 1)
        self.profe_tab.setLayout(ly)

    def _init_volun_tab(self):
        layout = QVBoxLayout()
        # Initialize the voluns table
        self.volun_table = QTableView()

        # Add search box
        self.search_box_volun = QLineEdit()
        self.search_box_volun.setPlaceholderText("Cerca voluntaris...")
        self.search_box_volun.textChanged.connect(self._filter_volun)

        # Oculta la columna de número de fila
        self.volun_table.verticalHeader().setVisible(False)
        # -- Configuració de selecció i estil --
        self.volun_table.setSelectionBehavior(QTableView.SelectRows)
        self.volun_table.setSelectionMode(QTableView.SingleSelection)
        self.volun_table.setAlternatingRowColors(True)
        self.volun_table.setStyleSheet("""
            QTableView::item:selected {
                background: #c5d6a1;
                color: black;
            }
            QTableView::item:selected:active {
                background: #a8bd88;
            }
        """)
        self._refresh_volun()

        # Panell de detall dreta
        self.detail_volun = VolunDetailWidget()
        self.detail_volun.saved.connect(self._refresh_volun)

        # Connect selection change to detail view
        # signal will be connected in _refresh_volun after setting the model

        # Layout for buttons
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.volun_table, stretch=3)
        self.detail_volun.setFixedWidth(300)
        hlayout.addWidget(self.detail_volun, stretch=0)

        btn_nou = QPushButton("Nou Voluntari")
        btn_nou.setIcon(QIcon("ui/assets/plus.svg"))
        btn_nou.setIconSize(QSize(16, 16))
        btn_eliminar = QPushButton("Eliminar Voluntari")
        btn_eliminar.setIcon(QIcon("ui/assets/minus.svg"))
        btn_eliminar.setIconSize(QSize(16, 16))
        btn_nou.clicked.connect(self._dialog_nou_volun)
        btn_eliminar.clicked.connect(self._eliminar_volun)

        top_buttons = QHBoxLayout()
        top_buttons.addWidget(btn_nou)
        top_buttons.addWidget(btn_eliminar)
        top_buttons.addStretch()

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addLayout(top_buttons)
        ly.addWidget(self.search_box_volun)
        ly.addLayout(hlayout, 1)
        self.volun_tab.setLayout(ly)
    
    ########################
    # ---- Methods for managing profes ----
    ########################
    def _refresh_profe(self):
        # Logic to refresh the profes table
        rows = listar_profesores()
        self._all_profes = rows  # Store all profes for filtering
        headers = [
            ("ID", "id"),
            ("Nom", "nombre"),
            ("1r Cognom", "apellido1"),
            ("2n Cognom", "apellido2"),
            ("DNI", "dniNie"),
            ("Email", "email"),
            ("Telèfon", "telfMovil"),
            ("Observacions", "observaciones")
        ]
        filtered_rows = self._filter_profe_rows(self.search_box_profe.text(), rows)
        model = DictTableModel(filtered_rows, headers)
        self.prof_table.setModel(model)
        self.prof_table.resizeColumnsToContents()
        self.prof_table.hideColumn(0)  # Hide ID column

        new_sel = self.prof_table.selectionModel()
        try:
            new_sel.currentRowChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        new_sel.currentRowChanged.connect(self._row_changed_profe)
        self._sel_model = new_sel

    def _dialog_nou_profe(self):
      dlg = ProfeDialog(self)
      if dlg.exec():
        self._refresh_profe()

    def _eliminar_profe(self):
        sel = self.prof_table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, "Error", "Selecciona un professor per eliminar.")
            return
        
        row = sel[0].row()
        profe = self.prof_table.model().rows[row]
        nom_complet = f"{profe['nombre']} {profe.get('apellido1', '')} {profe.get('apellido2', '')}".strip()
        
        box = QMessageBox()
        box.setWindowTitle("Eliminar Professor")
        box.setText(
          f"Vols eliminar el professor «{nom_complet}» (ID {profe['id']})?\n"
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
        
        eliminar_personal(profe["id"])
        self._refresh_profe()
        self.detail_profe.load(None)

    def _row_changed_profe(self, current, previous):
        if self.subtabs.currentWidget() != self.profe_tab:
            return
        if current.isValid():
            row = current.row()
            profe = self.prof_table.model().rows[row]
            self.detail_profe.load(profe.get("id"))
        else:
            self.detail_profe.load(None)

    def _filter_profe(self, text):
       self._refresh_profe()

    def _filter_profe_rows(self, text, rows):
        if not text.strip():
            return self._all_profes
        text = text.lower()

        def matches(p):
            return any(
                text in str(value).lower() if value else ""
                for value in p.values()
            )
        return [p for p in rows if matches(p)]

    ########################
    # ---- Methods for managing voluntarios ----
    ########################
    def _refresh_volun(self):
        # Logic to refresh the voluntarios table
        rows = listar_voluntarios()
        self._all_voluns = rows  # Store all voluntarios for filtering
        headers = [
            ("ID", "id"),
            ("Nom", "nombre"),
            ("1r Cognom", "apellido1"),
            ("2n Cognom", "apellido2"),
            ("DNI", "dniNie"),
            ("Email", "email"),
            ("Telèfon", "telfMovil"),
            ("Observacions", "observaciones")
        ]
        filtered_rows = self._filter_volun_rows(self.search_box_volun.text(), rows)
        model = DictTableModel(filtered_rows, headers)
        self.volun_table.setModel(model)
        if self.volun_table.selectionModel():
            try:
                self.volun_table.selectionModel().currentRowChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.volun_table.selectionModel().currentRowChanged.connect(self._row_changed_volun)
            self._sel_model = self.volun_table.selectionModel()
        self.volun_table.resizeColumnsToContents()
        self.volun_table.hideColumn(0)  # Hide ID column

    def _dialog_nou_volun(self):
      dlg = VolunDialog(self)
      if dlg.exec():
        self._refresh_volun()

    def _eliminar_volun(self):
        sel = self.volun_table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.warning(self, "Error", "Selecciona un voluntari per eliminar.")
            return
        
        row = sel[0].row()
        volun = self.volun_table.model().rows[row]
        nom_complet = f"{volun['nombre']} {volun.get('apellido1', '')} {volun.get('apellido2', '')}".strip()
        
        box = QMessageBox()
        box.setWindowTitle("Eliminar Voluntari")
        box.setText(
          f"Vols eliminar el voluntari «{nom_complet}» (ID {volun['id']})?\n"
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

        eliminar_personal(volun["id"])
        self._refresh_volun()
        self.detail_volun.load(None)

    def _row_changed_volun(self, current, previous):
        if self.subtabs.currentWidget() != self.volun_tab:
            return
        if current.isValid():
            row = current.row()
            volun = self.volun_table.model().rows[row]
            self.detail_volun.load(volun.get("id"))
        else:
            self.detail_volun.load(None)

    def _filter_volun(self, text):
       self._refresh_volun()

    def _filter_volun_rows(self, text, rows):
        if not text.strip():
            return self._all_voluns
        text = text.lower()

        def matches(p):
            return any(
                text in str(value).lower() if value else ""
                for value in p.values()
            )
        return [p for p in rows if matches(p)]
