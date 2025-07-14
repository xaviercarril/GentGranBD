from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QApplication
)

from ui.tab_socios import SociosTab
from ui.tab_actividades import ActividadesTab



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
