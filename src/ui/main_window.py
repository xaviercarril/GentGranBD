import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

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
        menu_arxiu.addSeparator()

        action_backup_db = QAction("Còpia de seguretat de la BD…", self)
        action_backup_db.triggered.connect(self._backup_database)
        menu_arxiu.addAction(action_backup_db)

        action_restore_db = QAction("Restaurar BD des d'una còpia…", self)
        action_restore_db.triggered.connect(self._restore_database)
        menu_arxiu.addAction(action_restore_db)

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

    def _backup_meta_path(self) -> Path:
        from database import _user_data_dir
        return Path(_user_data_dir()) / "backup_info.json"

    def _get_last_backup_timestamp(self) -> datetime | None:
        path = self._backup_meta_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            iso_value = data.get("last_backup_iso")
            if not iso_value:
                return None
            return datetime.fromisoformat(iso_value)
        except Exception:
            return None

    def _set_last_backup_timestamp(self, ts: datetime) -> None:
        path = self._backup_meta_path()
        try:
            path.write_text(json.dumps({"last_backup_iso": ts.isoformat()}))
        except Exception:
            pass

    def _should_prompt_backup(self) -> bool:
        last = self._get_last_backup_timestamp()
        if not last:
            return True
        return datetime.now() - last > timedelta(days=7)

    def _backup_database(self):
        from database import engine

        db_location = engine.url.database
        if not db_location:
            QMessageBox.critical(self, "Error", "No s'ha pogut determinar la ruta de la base de dades.")
            return

        db_path = Path(db_location)
        if not db_path.exists():
            QMessageBox.critical(
                self,
                "Error",
                f"No s'ha trobat la base de dades a {db_path}",
            )
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = f"{db_path.stem}_backup_{timestamp}{db_path.suffix or '.db'}"
        default_dir = db_path.parent if db_path.parent.exists() else Path.home()
        target_str, _ = QFileDialog.getSaveFileName(
            self,
            "Desar còpia de seguretat",
            str(default_dir / suggested),
            "SQLite (*.db);;Tots els arxius (*)",
        )
        if not target_str:
            return

        target_path = Path(target_str)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, target_path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error en la còpia",
                f"No s'ha pogut crear la còpia de seguretat:\n{exc}",
            )
            return

        self._set_last_backup_timestamp(datetime.now())

        QMessageBox.information(
            self,
            "Còpia creada",
            f"Base de dades copiada a:\n{target_path}",
        )

    def _restore_database(self):
        from database import engine

        db_location = engine.url.database
        if not db_location:
            QMessageBox.critical(self, "Error", "No s'ha pogut determinar la ruta de la base de dades.")
            return

        db_path = Path(db_location)
        target_dir = db_path.parent if db_path.parent.exists() else Path.home()

        box = QMessageBox(self)
        box.setWindowTitle("Restaurar base de dades")
        box.setText(
            "Aquesta acció sobreescriurà la base de dades actual amb "
            "el fitxer seleccionat.\nVols continuar?"
        )
        box.setIcon(QMessageBox.Warning)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Sí")
        box.button(QMessageBox.No).setText("No")
        reply = box.exec()
        if reply != QMessageBox.Yes:
            return

        source_str, _ = QFileDialog.getOpenFileName(
            self,
            "Selecciona la còpia de seguretat",
            str(target_dir),
            "SQLite (*.db);;Tots els arxius (*)",
        )
        if not source_str:
            return

        source_path = Path(source_str)
        if not source_path.exists():
            QMessageBox.critical(
                self,
                "Error",
                f"No s'ha trobat el fitxer seleccionat:\n{source_path}",
            )
            return

        if source_path.resolve() == db_path.resolve():
            QMessageBox.information(
                self,
                "Cap acció realitzada",
                "El fitxer seleccionat és la base de dades actual.",
            )
            return

        tmp_target = db_path.with_name(db_path.name + ".tmp_restore")
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            engine.dispose()  # Allibera connexions actives abans de sobreescriure
            shutil.copy2(source_path, tmp_target)
            shutil.move(tmp_target, db_path)
        except Exception as exc:
            if tmp_target.exists():
                tmp_target.unlink(missing_ok=True)
            QMessageBox.critical(
                self,
                "Error en la restauració",
                f"No s'ha pogut restaurar la base de dades:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Restauració completada",
            f"Base de dades restaurada des de:\n{source_path}",
        )
        try:
            self.socios_tab.refresh()
        except Exception:
            pass

    def closeEvent(self, event):
        try:
            prompt_needed = self._should_prompt_backup()
        except Exception:
            prompt_needed = False

        if prompt_needed:
            box = QMessageBox(self)
            box.setWindowTitle("Còpia de seguretat recomanada")
            box.setText(
                "Fa més d'una setmana que no es fa cap còpia de seguretat.\n"
                "Vols fer-ne una ara?"
            )
            box.setIcon(QMessageBox.Question)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.button(QMessageBox.Yes).setText("Sí")
            box.button(QMessageBox.No).setText("No")
            reply = box.exec()
            if reply == QMessageBox.Yes:
                self._backup_database()

        super().closeEvent(event)
