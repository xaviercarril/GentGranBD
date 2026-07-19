import json
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QSize, QThread, QTimer, Signal, QUrl
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QApplication, QMenuBar, QMenu
)
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QFileDialog
from PySide6.QtWidgets import QMessageBox, QProgressBar
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox

from ui.tab_socios import SociosTab
from ui.tab_actividades import ActividadesTab
from ui.tab_cursoAcademico import CursoAcademicoDialog
from ui.tab_personal import PersonalTab


class _UpdateCheckWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, manual: bool):
        super().__init__()
        self.manual = manual

    def run(self):
        try:
            import updater

            _startup_log(f"Checking updates with updater={updater.__file__} current={updater.APP_VERSION}")
            update_info = updater.check_for_update()
            if update_info is None:
                _startup_log("Update check result: no update available")
            else:
                _startup_log(
                    "Update check result: "
                    f"current={update_info.current_version} latest={update_info.latest_version} "
                    f"asset={update_info.asset.name}"
                )
            self.finished.emit(update_info, None)
        except Exception as exc:
            _startup_log(f"Update check exception: {exc}")
            self.finished.emit(None, exc)


class _UpdateInstallWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, update_info):
        super().__init__()
        self.update_info = update_info

    def run(self):
        try:
            import updater

            _startup_log(
                "Update install started: "
                f"target={self.update_info.latest_version} asset={self.update_info.asset.name}"
            )
            result = updater.install_update(self.update_info)
            _startup_log(f"Update install result: {result}")
            self.finished.emit(result, None)
        except Exception as exc:
            _startup_log(f"Update install exception: {exc}")
            self.finished.emit(None, exc)


def _startup_log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} [main_window.py] {message}"
    print(line, flush=True)
    try:
        log_path = Path(__file__).resolve().parents[2] / "logs" / "app-startup.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


class MainWindow(QMainWindow):
    """Finestra principal amb pestanyes (Socis, Activitats, …)."""
    update_check_finished_on_main = Signal(int, object, object, bool)
    update_check_thread_finished_on_main = Signal(int)
    update_install_finished_on_main = Signal(object, object)

    LOGOUT_EXIT_CODE = 42

    def __init__(self, current_user: dict | None = None):
        super().__init__()
        _startup_log("MainWindow init started")
        self.current_user = current_user or {}
        self._logging_out = False
        self._installing_update = False
        self._closing = False
        self._update_check_thread = None
        self._update_check_worker = None
        self._update_check_id = 0
        self._stale_update_check_threads = []
        self._update_install_thread = None
        self._update_install_worker = None
        self._update_progress_dialog = None
        self._base_status_message = ""
        self._sel_model = None  # Model de selecció per a la taula de socis
        self._realtime_service = None
        self._pending_realtime_sections = set()
        self.setWindowTitle("Associació Gent Gran de Castelldefels – Gestió")
        self._initial_window_size = QSize(1350, 780)
        self._centered_on_startup = False
        self.update_check_finished_on_main.connect(self._on_update_check_finished)
        self.update_check_thread_finished_on_main.connect(self._on_update_check_thread_finished)
        self.update_install_finished_on_main.connect(self._on_update_install_finished)
        self._realtime_refresh_timer = QTimer(self)
        self._realtime_refresh_timer.setSingleShot(True)
        self._realtime_refresh_timer.setInterval(500)
        self._realtime_refresh_timer.timeout.connect(self._flush_realtime_refresh)

        # ── QTabWidget ───────────────────────────────────────────
        _startup_log("Creating tabs")
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        _startup_log("Creating SociosTab")
        self.socios_tab = SociosTab()
        self.tabs.addTab(self.socios_tab, "Socis")
        _startup_log("Creating ActividadesTab")
        self.actividades_tab = ActividadesTab()
        self.tabs.addTab(self.actividades_tab, "Activitats")
        _startup_log("Creating PersonalTab")
        self.personal_tab = PersonalTab()
        self.tabs.addTab(self.personal_tab, "Personal")
        self._current_tab_index = self.tabs.currentIndex()
        self._changing_tab_programmatically = False
        self.tabs.currentChanged.connect(self._on_tab_changed)
        # Todas las vistas parten de la misma geometría, sin desactivar los
        # controles nativos de la ventana (incluido maximizar).
        self.resize(self._bounded_window_size(self._initial_window_size))

        # ── Menú superior ───────────────────────────────────────
        _startup_log("Creating menu")
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

        if self._is_admin():
            action_backup_db = QAction("Còpia de seguretat de la BD…", self)
            action_backup_db.triggered.connect(self._backup_database)
            menu_arxiu.addAction(action_backup_db)

            action_restore_db = QAction("Restaurar BD des d'una còpia…", self)
            action_restore_db.triggered.connect(self._restore_database)
            menu_arxiu.addAction(action_restore_db)
            menu_arxiu.addSeparator()

        action_password = QAction("Canviar contrasenya", self)
        action_password.triggered.connect(self._cambiar_password)
        menu_arxiu.addAction(action_password)

        action_logout = QAction("Tancar sessió", self)
        action_logout.triggered.connect(self._logout)
        menu_arxiu.addAction(action_logout)

        menu_ajuda = menu_bar.addMenu("Ajuda")
        action_updates = QAction("Comprovar actualitzacions manualment", self)
        action_updates.triggered.connect(lambda: self._start_update_check(manual=True))
        menu_ajuda.addAction(action_updates)
        action_about = QAction("Informació de la versió", self)
        action_about.triggered.connect(self._show_version_info)
        menu_ajuda.addAction(action_about)

        if self._is_admin():
            menu_admin = menu_bar.addMenu("Administració")
            action_usuaris = QAction("Usuaris", self)
            action_usuaris.triggered.connect(self._mostrar_usuaris)
            menu_admin.addAction(action_usuaris)

        self._update_session_status()
        self._start_realtime_sync()
        _startup_log("MainWindow init finished")
        QTimer.singleShot(1200, lambda: self._start_update_check(manual=False))

    def _update_session_status(self):
        from database import engine

        username = self.current_user.get("username", "")
        safe_url = engine.url.render_as_string(hide_password=True)
        self.setWindowTitle(f"Associació Gent Gran de Castelldefels")
        self._base_status_message = f"Usuari: {username} | BD: {safe_url}"
        self.statusBar().showMessage(self._base_status_message)

    def _show_base_status(self):
        self.statusBar().showMessage(self._base_status_message)

    def _start_realtime_sync(self):
        try:
            from ui.realtime import RealtimeService

            self._realtime_service = RealtimeService(self)
            self._realtime_service.change_received.connect(self._on_realtime_change)
            self._realtime_service.status_changed.connect(self._on_realtime_status)
            self._realtime_service.start()
        except Exception as exc:
            _startup_log(f"Realtime sync disabled: {exc}")

    def _on_realtime_status(self, status: str):
        _startup_log(f"Realtime sync status: {status}")

    def _on_realtime_change(self, payload):
        if self._closing:
            return
        sections = self._realtime_sections_for_table(str((payload or {}).get("tabla") or ""))
        if not sections:
            return
        self._pending_realtime_sections.update(sections)
        if not self._realtime_refresh_timer.isActive():
            self._realtime_refresh_timer.start()

    def _realtime_sections_for_table(self, table_name: str) -> set[str]:
        if table_name == "*":
            return {"socios", "actividades", "personal"}
        sections_by_table = {
            "socios": {"socios"},
            "firma_proteccion_datos": {"socios"},
            "personal": {"personal", "actividades"},
            "actividades": {"actividades"},
            "inscripciones": {"actividades", "socios"},
            "matricula_pagos": {"actividades", "socios"},
            "clases": {"actividades"},
            "asistencias_socio": {"actividades", "socios"},
            "curso_academico": {"actividades"},
            "trimestres": {"actividades"},
            "lugares": {"actividades"},
        }
        return sections_by_table.get(table_name, set())

    def _flush_realtime_refresh(self):
        sections = set(self._pending_realtime_sections)
        self._pending_realtime_sections.clear()
        if not sections:
            return

        widgets = {
            "socios": self.socios_tab,
            "actividades": self.actividades_tab,
            "personal": self.personal_tab,
        }
        refreshed = 0
        skipped = 0
        for section in sorted(sections):
            widget = widgets.get(section)
            if widget is None:
                continue
            try:
                if hasattr(widget, "refresh_from_realtime"):
                    did_refresh = bool(widget.refresh_from_realtime())
                elif hasattr(widget, "refresh"):
                    widget.refresh()
                    did_refresh = True
                else:
                    did_refresh = False
            except Exception as exc:
                _startup_log(f"Realtime refresh failed for {section}: {exc}")
                continue
            if did_refresh:
                refreshed += 1
            else:
                skipped += 1

        if refreshed:
            self.statusBar().showMessage("Dades actualitzades per canvis a la base de dades.", 2500)
        elif skipped:
            self.statusBar().showMessage("Hi ha canvis externs pendents; acaba l'edició per actualitzar.", 5000)

    def _is_admin(self) -> bool:
        return self.current_user.get("rol") == "ADMIN"

    def _is_packaged_app(self) -> bool:
        return getattr(sys, "frozen", False)

    def _show_version_info(self):
        from version import APP_VERSION

        frozen_text = "empaquetada" if getattr(sys, "frozen", False) else "desenvolupament"
        QMessageBox.information(
            self,
            "Informació de la versió",
            "GentGranBD\n\n"
            f"Versió: {APP_VERSION}\n"
            f"Mode: {frozen_text}\n"
            f"Python: {sys.version.split()[0]}\n"
            f"Executable: {sys.executable}",
        )

    def _start_update_check(self, manual: bool = False):
        if self._closing:
            return
        if not self._is_packaged_app():
            if manual:
                QMessageBox.information(
                    self,
                    "Actualitzacions",
                    "La comprovació d'actualitzacions només està disponible en l'aplicació empaquetada.",
                )
            return
        if self._update_check_thread is not None:
            if manual:
                QMessageBox.information(self, "Actualitzacions", "Ja s'estan comprovant les actualitzacions.")
            return

        self._update_check_id += 1
        check_id = self._update_check_id
        _startup_log(f"Update check started id={check_id} manual={manual}")
        self.statusBar().showMessage("Comprovant actualitzacions...")
        thread = QThread(self)
        worker = _UpdateCheckWorker(manual=manual)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(
            lambda info, error: self.update_check_finished_on_main.emit(check_id, info, error, manual)
        )
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.update_check_thread_finished_on_main.emit(check_id))
        self._update_check_thread = thread
        self._update_check_worker = worker
        thread.start()
        QTimer.singleShot(25000, lambda: self._on_update_check_timeout(check_id, manual))

    def _on_update_check_finished(self, check_id: int, update_info, error, manual: bool):
        if check_id != self._update_check_id:
            return
        self._show_base_status()
        if error:
            _startup_log(f"Update check failed: {error}")
            if manual:
                QMessageBox.warning(self, "Actualitzacions", f"No s'ha pogut comprovar actualitzacions:\n{error}")
            return

        if update_info is None:
            if manual:
                QMessageBox.information(self, "Actualitzacions", "Ja tens instal·lada l'última versió.")
            return

        self._show_update_available_dialog(update_info)

    def _on_update_check_thread_finished(self, check_id: int):
        if check_id != self._update_check_id:
            return
        _startup_log(f"Update check thread finished id={check_id}")
        self._update_check_thread = None
        self._update_check_worker = None
        self._show_base_status()

    def _on_update_check_timeout(self, check_id: int, manual: bool):
        if check_id != self._update_check_id or self._update_check_thread is None:
            return
        _startup_log(f"Update check timeout id={check_id}")
        stale_thread = self._update_check_thread
        self._stale_update_check_threads.append(stale_thread)
        stale_thread.finished.connect(lambda: self._discard_stale_update_thread(stale_thread))
        self._update_check_id += 1
        self._update_check_thread = None
        self._update_check_worker = None
        self.statusBar().showMessage("No s'ha pogut comprovar actualitzacions: temps esgotat.", 6000)
        if manual:
            QMessageBox.warning(
                self,
                "Actualitzacions",
                "La comprovació d'actualitzacions ha trigat massa. Torna-ho a provar més tard.",
            )

    def _discard_stale_update_thread(self, thread):
        try:
            self._stale_update_check_threads.remove(thread)
        except ValueError:
            pass

    def _show_update_available_dialog(self, update_info):
        body = (update_info.body or "").strip()
        if len(body) > 1200:
            body = body[:1200].rstrip() + "\n..."

        box = QMessageBox(self)
        box.setWindowTitle("Actualització disponible")
        box.setIcon(QMessageBox.Information)
        box.setText(
            f"Hi ha una nova versió de GentGranBD.\n\n"
            f"Versió actual: {update_info.current_version}\n"
            f"Nova versió: {update_info.latest_version}"
        )
        if body:
            box.setInformativeText(body)
        install_button = box.addButton("Instal·lar ara", QMessageBox.AcceptRole)
        later_button = box.addButton("Més tard", QMessageBox.RejectRole)
        release_button = None
        if update_info.release_url:
            release_button = box.addButton("Veure release", QMessageBox.ActionRole)
        box.setDefaultButton(install_button)
        box.exec()

        clicked = box.clickedButton()
        if clicked == install_button:
            self._start_update_install(update_info)
        elif release_button is not None and clicked == release_button:
            QDesktopServices.openUrl(QUrl(update_info.release_url))
        else:
            later_button.setEnabled(True)

    def _start_update_install(self, update_info):
        if self._closing:
            return
        if self._update_install_thread is not None and not self._installing_update:
            QMessageBox.information(self, "Actualitzacions", "Ja s'està preparant una actualització.")
            return
        if not self._confirm_all_pending_changes():
            return

        progress = QDialog(self)
        progress.setWindowTitle("Instal·lant actualització")
        progress.setModal(True)
        layout = QVBoxLayout(progress)
        layout.addWidget(QLabel("Descarregant i verificant l'actualització..."))
        bar = QProgressBar(progress)
        bar.setRange(0, 0)
        layout.addWidget(bar)
        progress.setMinimumWidth(420)
        progress.show()
        self._update_progress_dialog = progress

        thread = QThread(self)
        worker = _UpdateInstallWorker(update_info)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, error: self.update_install_finished_on_main.emit(result, error))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_update_install_thread_finished)
        self._update_install_thread = thread
        self._update_install_worker = worker
        thread.start()

    def _on_update_install_thread_finished(self):
        _startup_log("Update install thread finished")
        self._update_install_thread = None
        self._update_install_worker = None

    def _on_update_install_finished(self, result, error):
        if self._update_progress_dialog is not None:
            self._update_progress_dialog.close()
            self._update_progress_dialog.deleteLater()
            self._update_progress_dialog = None

        if error:
            _startup_log(f"Update install failed: {error}")
            QMessageBox.critical(self, "Actualització", f"No s'ha pogut instal·lar l'actualització:\n{error}")
            return

        backup_note = ""
        if getattr(result, "backup_path", None):
            backup_note = f"\n\nCòpia de seguretat creada:\n{result.backup_path}"
        QMessageBox.information(
            self,
            "Actualització",
            f"{result.message}\n\nL'aplicació es tancarà per completar la instal·lació.{backup_note}",
        )
        self._installing_update = True
        self.close()
        QApplication.quit()

    def _mostrar_usuaris(self):
        if not self._is_admin():
            QMessageBox.warning(self, "Accés denegat", "Només els administradors poden gestionar usuaris.")
            return
        from ui.usuarios_dialog import UsuariosDialog

        dlg = UsuariosDialog(self)
        dlg.exec()

    def _cambiar_password(self):
        from ui.usuarios_dialog import cambiar_password_actual

        cambiar_password_actual(self, self.current_user)

    def _logout(self):
        if not self._confirm_all_pending_changes():
            return
        self._logging_out = True
        self.close()
        QApplication.exit(self.LOGOUT_EXIT_CODE)

    def _confirm_all_pending_changes(self) -> bool:
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if hasattr(widget, "confirm_pending_changes"):
                if not widget.confirm_pending_changes():
                    return False
        return True

    def _on_tab_changed(self, index: int):
        if self._changing_tab_programmatically:
            return

        previous_index = getattr(self, "_current_tab_index", index)
        previous_widget = self.tabs.widget(previous_index)
        if hasattr(previous_widget, "confirm_pending_changes"):
            if not previous_widget.confirm_pending_changes():
                self._changing_tab_programmatically = True
                try:
                    self.tabs.setCurrentIndex(previous_index)
                finally:
                    self._changing_tab_programmatically = False
                return

        self._current_tab_index = index

    def showEvent(self, event):
        """Centra la ventana una vez Qt haya calculado su marco nativo."""
        super().showEvent(event)
        if not self._centered_on_startup:
            self._centered_on_startup = True
            if not self.isMaximized():
                QTimer.singleShot(0, self._center_on_primary_screen)

    def _center_on_primary_screen(self) -> None:
        if self.isMaximized():
            return

        app = QApplication.instance()
        screen = self.screen() or (app.primaryScreen() if app else None)
        if not screen:
            _startup_log("No primary screen detected")
            return

        available = screen.availableGeometry()
        horizontal_margin = 24
        top_margin = 24
        # En macOS, Qt puede incluir el Dock en ``availableGeometry``. Esta
        # reserva evita que la ventana inicial quede por debajo de él.
        dock_clearance = 80 if sys.platform == "darwin" else 24
        frame = self.frameGeometry()

        # ``resize`` trabaja sobre el área cliente, mientras que el Dock y los
        # límites de pantalla se comparan con el marco completo de macOS.
        # Ajustamos después de mostrar la ventana, cuando ese marco ya existe.
        max_frame_width = max(1, available.width() - 2 * horizontal_margin)
        max_frame_height = max(1, available.height() - top_margin - dock_clearance)
        excess_width = max(0, frame.width() - max_frame_width)
        excess_height = max(0, frame.height() - max_frame_height)
        if excess_width or excess_height:
            self.resize(
                max(1, self.width() - excess_width),
                max(1, self.height() - excess_height),
            )
            frame = self.frameGeometry()

        min_x = available.left() + horizontal_margin
        min_y = available.top() + top_margin
        max_x = available.right() - horizontal_margin - frame.width() + 1
        max_y = available.bottom() - dock_clearance - frame.height() + 1
        x = min_x + (max_x - min_x) // 2
        y = min_y + (max_y - min_y) // 2
        self.move(
            max(min_x, min(x, max_x)) if max_x >= min_x else available.left(),
            max(min_y, min(y, max_y)) if max_y >= min_y else available.top(),
        )
        _startup_log(f"Window centered on primary screen: {available}")

    def _bounded_window_size(self, target: QSize) -> QSize:
        app = QApplication.instance()
        screen = app.primaryScreen() if app else None
        if not screen:
            return target
        available = screen.availableGeometry()
        horizontal_margin = 24
        top_margin = 24
        dock_clearance = 80 if sys.platform == "darwin" else 24
        return QSize(
            min(target.width(), max(1, available.width() - 2 * horizontal_margin)),
            min(target.height(), max(1, available.height() - top_margin - dock_clearance)),
        )

    def _mostrar_dialog_nou_curs(self):
        from ui.tab_cursoAcademico import CursoAcademicoDialog
        dlg = CursoAcademicoDialog(self)
        dlg.exec()

    def _importar_socis(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecciona un arxiu Excel", "", "Excel Files (*.xlsx *.xls *.csv)")
        if path:
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle("Importació de Socis")
            progress_dialog.setModal(False)
            progress_layout = QVBoxLayout(progress_dialog)
            progress_label = QLabel("Important socis…")
            progress_bar = QProgressBar(progress_dialog)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_layout.addWidget(progress_label)
            progress_layout.addWidget(progress_bar)
            progress_dialog.setMinimumWidth(420)
            progress_dialog.show()

            process = QProcess(self)
            process.setProcessChannelMode(QProcess.MergedChannels)
            project_root = Path(__file__).resolve().parents[2]
            process.setWorkingDirectory(str(project_root))
            self._import_process = process
            output_buffer = {"text": ""}
            final_result = {"data": None}
            last_progress = {"pct": -1, "time": 0.0}
            _startup_log(f"Import started with QProcess: {path}")

            def update_progress(done: int, total: int):
                pct = int((done / total) * 100) if total else 0
                now = time.monotonic()
                if done != total and pct == last_progress["pct"] and now - last_progress["time"] < 0.25:
                    return
                last_progress["pct"] = pct
                last_progress["time"] = now
                progress_label.setText(f"Important socis… {done}/{total}")
                progress_bar.setValue(pct)

            def cleanup():
                self._import_process = None

            def handle_payload(payload: dict):
                msg_type = payload.get("type")
                if msg_type == "progress":
                    update_progress(int(payload.get("done", 0)), int(payload.get("total", 0)))
                elif msg_type == "result":
                    final_result["data"] = payload
                elif msg_type == "error":
                    final_result["data"] = payload

            def on_ready_read():
                output_buffer["text"] += bytes(process.readAllStandardOutput()).decode("utf-8", errors="replace")
                while "\n" in output_buffer["text"]:
                    line, rest = output_buffer["text"].split("\n", 1)
                    output_buffer["text"] = rest
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        handle_payload(json.loads(line))
                    except json.JSONDecodeError:
                        _startup_log(f"Import process output: {line}")

            def on_finished(exit_code: int, exit_status):
                on_ready_read()
                cleanup()
                progress_bar.setValue(100)
                progress_dialog.close()
                progress_dialog.deleteLater()

                result = final_result["data"]
                if exit_code != 0 or not result or result.get("type") == "error":
                    message = result.get("message") if isinstance(result, dict) else output_buffer["text"]
                    _startup_log(f"Import failed in process: exit={exit_code}, message={message}")
                    self._show_scrollable_text("Errors d'importació", message or "El procés d'importació ha fallat.")
                    return

                creados = result["created"]
                warnings = result.get("warnings", [])
                warning_count = result["warning_count"]
                error_count = result["error_count"]
                _startup_log(
                    f"Import finished: created={creados}, failed={result['failed']}, warnings={warning_count}"
                )

                summary = [f"Importació completada: {creados} socis creats."]
                if warning_count:
                    summary.append(f"S'han detectat {warning_count} avisos (p. ex. camps buits).")
                if error_count:
                    summary.append(f"S'han detectat {error_count} errors.")
                QMessageBox.information(self, "Resultat importació", "\n".join(summary))
                try:
                    self.socios_tab.refresh()
                except Exception:
                    pass
                if warnings:
                    warning_text = "\n".join(warnings)
                    if warning_count > len(warnings):
                        warning_text += f"\n\n... i {warning_count - len(warnings)} avisos més."
                    self._show_scrollable_text("Avisos de la importació", warning_text)

            process.readyReadStandardOutput.connect(on_ready_read)
            process.finished.connect(on_finished)

            python_exe = Path(sys.executable)
            script = project_root / "scripts" / "import_socios_cli.py"
            process.start(str(python_exe), [str(script), path])

    def _solicitar_guardat_errors_importacio(self, filas_erroneas, exportador):
        suggested_name = f"errors_socis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        ruta, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar errors d'importació",
            suggested_name,
            "Excel (*.xlsx);;CSV (*.csv)"
        )
        if not ruta:
            return

        suffix = Path(ruta).suffix
        if not suffix:
            if selected_filter.startswith("CSV"):
                ruta = f"{ruta}.csv"
            else:
                ruta = f"{ruta}.xlsx"

        try:
            exportador(filas_erroneas, ruta)
            QMessageBox.information(
                self,
                "Errors guardats",
                f"S'ha guardat el fitxer amb {len(filas_erroneas)} files errònies."
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error en guardar",
                f"No s'ha pogut guardar el fitxer amb errors:\n{exc}"
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
        if not self._is_admin():
            QMessageBox.warning(
                self,
                "Accés denegat",
                "Només els administradors poden fer còpies de seguretat de la BD.",
            )
            return

        from database import _user_data_dir, engine
        from database_backup import BackupError, backup_extension, create_database_backup

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            extension = backup_extension(engine)
        except BackupError as exc:
            QMessageBox.critical(self, "Còpia no disponible", str(exc))
            return

        suggested = f"gentgran_backup_{timestamp}{extension}"
        default_dir = Path(_user_data_dir()) / "backups"
        default_dir.mkdir(parents=True, exist_ok=True)
        file_filter = (
            "SQLite (*.db);;Tots els arxius (*)"
            if extension == ".db"
            else "Còpia PostgreSQL (*.dump);;Tots els arxius (*)"
        )
        target_str, _ = QFileDialog.getSaveFileName(
            self,
            "Desar còpia de seguretat",
            str(default_dir / suggested),
            file_filter,
        )
        if not target_str:
            return

        try:
            target_path = create_database_backup(
                engine,
                target_str,
                user_role=self.current_user.get("rol", ""),
            )
        except BackupError as exc:
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
            f"Còpia de seguretat creada correctament a:\n{target_path}",
        )

    def _restore_database(self):
        if not self._is_admin():
            QMessageBox.warning(
                self,
                "Accés denegat",
                "Només els administradors poden restaurar la BD.",
            )
            return

        from database import _user_data_dir, engine

        if engine.url.get_backend_name() == "postgresql":
            source_str, _ = QFileDialog.getOpenFileName(
                self,
                "Selecciona la còpia PostgreSQL",
                str(Path(_user_data_dir()) / "backups"),
                "Còpia PostgreSQL (*.dump);;Tots els arxius (*)",
            )
            if not source_str:
                return

            box = QMessageBox(self)
            box.setWindowTitle("Restaurar base de dades PostgreSQL")
            box.setText(
                "Aquesta acció eliminarà i recrearà les dades de la base de dades "
                "DigitalOcean actual amb la còpia seleccionada.\n\n"
                f"Fitxer: {source_str}\n\nVols continuar?"
            )
            box.setIcon(QMessageBox.Warning)
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.button(QMessageBox.Yes).setText("Sí, restaurar")
            box.button(QMessageBox.No).setText("No")
            if box.exec() != QMessageBox.Yes:
                return

            try:
                from database_backup import BackupError, restore_postgresql_backup

                restore_postgresql_backup(
                    engine,
                    source_str,
                    user_role=self.current_user.get("rol", ""),
                )
            except BackupError as exc:
                QMessageBox.critical(self, "Error en la restauració", str(exc))
                return

            QMessageBox.information(
                self,
                "Restauració completada",
                "La còpia PostgreSQL s'ha restaurat correctament. "
                "Tanca i torna a obrir l'aplicació abans de continuar treballant.",
            )
            return

        if engine.url.get_backend_name() != "sqlite":
            QMessageBox.information(self, "Restauració no disponible", "Aquest motor no és compatible.")
            return

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
        if self._update_install_thread is not None and not self._installing_update:
            QMessageBox.information(
                self,
                "Actualització en curs",
                "Espera que acabi la instal·lació de l'actualització abans de tancar l'aplicació.",
            )
            event.ignore()
            return

        if not self._logging_out and not self._installing_update and not self._confirm_all_pending_changes():
            event.ignore()
            return

        self._closing = True
        if not self._stop_update_thread("_update_check_thread"):
            self._closing = False
            event.ignore()
            return
        if not self._stop_update_thread("_update_install_thread"):
            self._closing = False
            event.ignore()
            return
        if self._realtime_service is not None:
            try:
                self._realtime_service.stop()
            except Exception as exc:
                _startup_log(f"Realtime sync stop failed: {exc}")
            self._realtime_service = None
        super().closeEvent(event)

    def _stop_update_thread(self, attr_name: str) -> bool:
        thread = getattr(self, attr_name, None)
        if thread is None:
            return True
        try:
            if thread.isRunning():
                thread.quit()
                if not thread.wait(25000):
                    QMessageBox.warning(
                        self,
                        "Tancament ajornat",
                        "Encara hi ha una tasca d'actualització en curs. Torna a tancar l'aplicació en uns segons.",
                    )
                    return False
        except RuntimeError:
            pass
        setattr(self, attr_name, None)
        return True
