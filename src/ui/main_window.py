from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableView,
    QPushButton, QMessageBox, QLineEdit
)
from PySide6.QtGui import QPixmap, QIcon          # <- afegit
from ui.socio_detail import SocioDetailWidget
from PySide6.QtCore import Qt, QSize

from controladores.socios import (
    listar_socios, modificar_socio, eliminar_socio, consultar_socio, generar_carnet_pdf
)
from controladores.actividades import listar_actividades
from ui.table_models import DictTableModel
from ui.socio_dialog import SocioDialog


class MainWindow(QMainWindow):
    """Finestra principal amb pestanyes (Socis, Activitats, …)."""

    def __init__(self):
        super().__init__()
        self._sel_model = None  # Model de selecció per a la taula de socis
        self.setWindowTitle("Gent Gran – Gestió")
        self.resize(900, 600)

        # ── QTabWidget ───────────────────────────────────────────
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Pestaña Socis
        self._init_tab_socis()

        # Pestaña Activitats (placeholder)
        self._init_tab_activitats()

    # ==========================================================
    #   SOCIS
    # ==========================================================
    def _init_tab_socis(self):
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
        # Verd pastel corporatiu per a la fila seleccionada
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
        self.detail.saved.connect(self._refresh_socios)  # Auto-refresca quan es guarda

        # Quan seleccionem fila → carregar detall
        self.table_socis.selectionModel().currentRowChanged.connect(self._row_changed)

        # Layout horitzontal amb taula (flexible) i detall (ample fix, no movable)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.table_socis, stretch=3)   # taula ocupa la resta
        self.detail.setFixedWidth(300)                   # ample fix en píxels
        hlayout.addWidget(self.detail, stretch=0)

        # Botons alta / baixa
        btn_nou = QPushButton("Nou soci")
        btn_nou.setIcon(QIcon("ui/assets/plus.svg"))      # icona +
        btn_nou.setIconSize(QSize(16, 16))
        btn_esborrar = QPushButton("Eliminar")
        btn_esborrar.setIcon(QIcon("ui/assets/minus.svg"))  # icona –
        btn_esborrar.setIconSize(QSize(16, 16))
        btn_carnet = QPushButton("Generar Carnet")
        btn_carnet.setIcon(QIcon("ui/assets/id-card.svg"))   # usa una icona id-card
        btn_carnet.setIconSize(QSize(16, 16))
        btn_carnet.clicked.connect(self._generar_carnet_socio)
        btn_nou.clicked.connect(self._dialog_nou_socio)
        btn_esborrar.clicked.connect(self._eliminar_socio)

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addWidget(self._search_box)
        # Botons en la mateixa línia
        top_buttons = QHBoxLayout()
        top_buttons.addWidget(btn_nou)
        top_buttons.addWidget(btn_esborrar)
        top_buttons.addWidget(btn_carnet)
        top_buttons.addStretch()          # espai flexible a la dreta

        ly.addLayout(top_buttons)
        ly.addLayout(hlayout, 1)

        self.tabs.addTab(page, "Socis")

    def _refresh_socios(self):
        rows = listar_socios()
        self._all_socios = rows  # guarda'ls sense filtrar
        headers = [
            ("ID", "id"),
            ("DNI/NIE", "dni_nie"),
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
        # model.edited.connect(self._guardar_edicio_inline)
        self.table_socis.setModel(model)
        self.table_socis.resizeColumnsToContents()
         # --- tornar a connectar el senyal sense duplicitats ---
        new_sel = self.table_socis.selectionModel()

        # Desconnecta del model anterior si és diferent
        try:
            new_sel.currentRowChanged.disconnect()   # sense paràmetres
        except (TypeError, RuntimeError):
            pass

        # Connecta al nou model de selecció
        new_sel.currentRowChanged.connect(self._row_changed)
        self._sel_model = new_sel     # guarda referència per la propera vegada

    # ---- CRUD actions ----
    def _dialog_nou_socio(self):
        dlg = SocioDialog(self)
        if dlg.exec():
            self._refresh_socios()

    def _editar_socio_dialog(self, index):
        fila = self.table_socis.model().rows[index.row()]
        socio_id = fila["id"]
        socio_complet = consultar_socio(socio_id)      # inclou bytes de foto
        dlg = SocioDialog(self, socio=socio_complet)
        if dlg.exec():
            self._refresh_socios()

    def _eliminar_socio(self):
        """Elimina el soci seleccionat després de confirmar amb l'usuari (botons Sí / No)."""
        sel = self.table_socis.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        socio = self.table_socis.model().rows[row]
        nom_complet = f"{socio['nombre']} {socio.get('apellido1', '')}".strip()

        # QMessageBox personalitzat amb botons traduïts
        box = QMessageBox(self)
        box.setWindowTitle("Confirmar eliminació")
        box.setText(
            f"Vols eliminar el soci «{nom_complet}» (ID {socio['id']})?\n"
            "Aquesta acció no es pot desfer."
        )
        icon_path = "ui/assets/trash.svg"   # assegura't que existeix
        pix = QPixmap(icon_path)
        if pix.isNull() and icon_path.lower().endswith(".svg"):
            # Carrega SVG via QIcon per convertir-lo a QPixmap
            icon = QIcon(icon_path)
            pix = icon.pixmap(48, 48)
        if not pix.isNull():
            box.setIconPixmap(pix)
        else:
            box.setIcon(QMessageBox.Warning)   # fallback
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
        socio_id = self.table_socis.model().rows[curr.row()]["id"]
        self.detail.load(socio_id)

    # ==========================================================
    #   ACTIVITATS (placeholder de moment)
    # ==========================================================
    def _init_tab_activitats(self):
        table_act = QTableView()
        rows = listar_actividades()
        headers = ["id", "nombre", "tipo", "max_alumnos"]
        table_act.setModel(DictTableModel(rows, headers))
        table_act.resizeColumnsToContents()

        page = QWidget()
        ly = QVBoxLayout(page)
        ly.addWidget(table_act, 1)

        self.tabs.addTab(page, "Activitats")

    def _generar_carnet_socio(self):
        """Genera carnet PDF per al soci seleccionat i demana on guardar-lo."""
        sel = self.table_socis.selectionModel().selectedRows()
        if not sel:
            return

        row = sel[0].row()
        socio = self.table_socis.model().rows[row]
        from PySide6.QtWidgets import QFileDialog

        suggested_name = f"carnet_soci_{socio['id']}.pdf"
        outfile, _ = QFileDialog.getSaveFileName(
            self,
            "Desar carnet com a PDF",
            suggested_name,
            "PDF Files (*.pdf)"
        )
        if not outfile:
            return

        generar_carnet_pdf(socio['id'], outfile)

        QMessageBox.information(
            self,
            "Carnet generat",
            f"S'ha generat el carnet PDF:\n{outfile}"
        )

    def _filtrar_socios(self):
        """Refresca la taula segons la cerca."""
        self._refresh_socios()

    def _filter_rows(self, text):
        """Filtra els socis per qualsevol camp que contingui el text."""
        if not text.strip():
            return self._all_socios
        text = text.lower()
        def matches(s):
            return any(
                text in str(value).lower() if value else ""
                for value in s.values()
            )
        return [s for s in self._all_socios if matches(s)]