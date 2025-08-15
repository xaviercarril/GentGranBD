from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QApplication, QMenuBar, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog

from ui.tab_socios import SociosTab
from ui.tab_actividades import ActividadesTab
from ui.tab_cursoAcademico import CursoAcademicoDialog
from ui.tab_personal import PersonalTab

class MainWindow(QMainWindow):
    """Finestra principal amb pestanyes (Socis, Activitats, …)."""

    def __init__(self):
        super().__init__()
        self._sel_model = None  # Model de selecció per a la taula de socis
        self.setWindowTitle("Associació Gent Gran de Castelldefels – Gestió")
        self.resize(900, 600)

        # Obtiene lista de pantallas
        app = QApplication.instance()
        screens = app.screens()

        if len(screens) > 1:
            second_screen = screens[1]
            geometry = second_screen.geometry()
            self.move(
                geometry.left() + (geometry.width() - self.width()) // 2,
                geometry.top() + (geometry.height() - self.height()) // 2
            )
        else:
            print("Solo hay una pantalla detectada")

        # ── QTabWidget ───────────────────────────────────────────
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(SociosTab(), "Socis")
        self.tabs.addTab(ActividadesTab(), "Activitats")
        self.tabs.addTab(PersonalTab(), "Personal")

        # ── Menú superior ───────────────────────────────────────
        # Crear barra de menú
        menu_bar = self.menuBar()
        menu_arxiu = menu_bar.addMenu("Arxiu")

        # Acción para crear curso académico
        action_nou_curs = QAction("Gestionar Curs Acadèmic", self)
        action_nou_curs.triggered.connect(self._mostrar_dialog_nou_curs)
        menu_arxiu.addAction(action_nou_curs)

        action_importar_socis = QAction("Importar Socis (CSV/Excel)", self)
        action_importar_socis.triggered.connect(self._importar_socis)
        menu_arxiu.addAction(action_importar_socis)

    def _mostrar_dialog_nou_curs(self):
        from ui.tab_cursoAcademico import CursoAcademicoDialog
        dlg = CursoAcademicoDialog(self)
        dlg.exec()

    def _importar_socis(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona un arxiu Excel", "", "Excel Files (*.xlsx *.xls *.csv)")
        if path:
            try:
                # Lazy import to avoid pandas overhead at startup
                from importador.importar_socios_excel import importar_socios_desde_excel
                importar_socios_desde_excel(path)
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error", f"No s'han pogut importar els socis: {e}")
