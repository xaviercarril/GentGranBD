from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QApplication, QMenuBar, QMenu
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QProgressDialog, QMessageBox
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox

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

        self.socios_tab = SociosTab()
        self.tabs.addTab(self.socios_tab, "Socis")
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
            prog = None
            try:
                # Lazy import to avoid pandas overhead at startup
                from importador.importar_socios_excel import importar_socios_desde_excel

                # Setup progress dialog
                prog = QProgressDialog("Important socis…", "Cancel·lar", 0, 100, self)
                prog.setWindowTitle("Importació de Socis")
                prog.setAutoClose(True)   # close automatically when reaching max
                prog.setAutoReset(True)
                prog.show()

                warnings: list[str] = []
                errors: list[str] = []
                total_cache = {"total": 0}

                def on_progress(done: int, total: int):
                    # First call seeds range if needed
                    total_cache["total"] = max(total_cache.get("total", 0), total)
                    pct = int((done / total) * 100) if total else 0
                    prog.setValue(pct)
                    QApplication.processEvents()
                    if prog.wasCanceled():
                        # Not supported mid-transaction; inform user after
                        pass

                def on_warning(idx: int, msg: str):
                    warnings.append(f"Fila {idx+1}: {msg}")

                def on_error(idx: int, msg: str):
                    errors.append(f"Fila {idx+1}: {msg}")

                creados = importar_socios_desde_excel(
                    path,
                    on_progress=on_progress,
                    on_warning=on_warning,
                    on_error=on_error,
                )
                if prog:
                    prog.setValue(100)
                    prog.close()
                    prog.deleteLater()
                    prog = None

                summary = [f"Importació completada: {creados} socis creats."]
                if warnings:
                    summary.append(f"S'han detectat {len(warnings)} avisos (p. ex. camps buits).")
                if errors:
                    summary.append(f"S'han detectat {len(errors)} errors.")
                QMessageBox.information(self, "Resultat importació", "\n".join(summary))
                # Refresh Socis tab so new entries are visible immediately
                try:
                    self.socios_tab.refresh()
                except Exception:
                    pass
                if warnings:
                    self._show_scrollable_text("Avisos de la importació", "\n".join(warnings))
            except Exception as e:
                if prog:
                    prog.close()
                    prog.deleteLater()
                    prog = None
                # Show detailed, scrollable errors if any were captured
                detail_lines = errors if 'errors' in locals() and errors else [str(e)]
                self._show_scrollable_text(
                    "Errors d'importació",
                    "\n".join(detail_lines)
                )

    def _show_scrollable_text(self, title: str, text: str):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Si us plau, revisa els següents missatges:"))
        editor = QPlainTextEdit(dlg)
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setMinimumSize(700, 400)
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, parent=dlg)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)
        dlg.exec()
