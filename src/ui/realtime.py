from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from sqlalchemy import func, select

import database
from audit import REALTIME_CHANNEL
from models import Auditoria


class _PostgresNotifyWorker(QObject):
    received = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self):
        super().__init__()
        self._stopped = False
        self._conn = None

    def stop(self) -> None:
        self._stopped = True
        conn = self._conn
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    def run(self) -> None:
        try:
            import psycopg

            self._conn = psycopg.connect(**_postgres_connect_kwargs(), autocommit=True)
            self._conn.execute(f"LISTEN {REALTIME_CHANNEL}")
            while not self._stopped:
                try:
                    notifications = self._conn.notifies(timeout=1.0, stop_after=1)
                except TypeError:
                    notifications = self._conn.notifies(timeout=1.0)

                for notification in notifications:
                    if self._stopped:
                        break
                    self.received.emit(_decode_payload(notification.payload))
        except Exception as exc:
            if not self._stopped:
                self.failed.emit(str(exc))
        finally:
            conn = self._conn
            self._conn = None
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            self.finished.emit()


class RealtimeService(QObject):
    change_received = Signal(object)
    status_changed = Signal(str)

    def __init__(self, parent=None, poll_interval_ms: int = 5000):
        super().__init__(parent)
        self._poll_interval_ms = poll_interval_ms
        self._poll_timer: QTimer | None = None
        self._last_audit_id: int | None = None
        self._thread: QThread | None = None
        self._worker: _PostgresNotifyWorker | None = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        if database.engine.url.get_backend_name() == "postgresql":
            self._start_postgres_listener()
        else:
            self._start_audit_polling("polling")

    def stop(self) -> None:
        self._started = False
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer.deleteLater()
            self._poll_timer = None

        if self._worker is not None:
            self._worker.stop()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(3000)
            self._thread = None
            self._worker = None

    def _start_postgres_listener(self) -> None:
        thread = QThread(self)
        worker = _PostgresNotifyWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.received.connect(self.change_received)
        worker.failed.connect(self._on_postgres_listener_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._thread = thread
        self._worker = worker
        self.status_changed.emit("realtime")

    def _on_postgres_listener_failed(self, message: str) -> None:
        self.status_changed.emit(f"realtime-fallback: {message}")
        self._thread = None
        self._worker = None
        self._start_audit_polling("fallback")

    def _start_audit_polling(self, mode: str) -> None:
        if self._poll_timer is not None:
            return
        self._last_audit_id = self._latest_audit_id()
        timer = QTimer(self)
        timer.setInterval(self._poll_interval_ms)
        timer.timeout.connect(self._poll_audit_changes)
        timer.start()
        self._poll_timer = timer
        self.status_changed.emit(mode)

    def _latest_audit_id(self) -> int:
        try:
            with database.SessionLocal() as db:
                return db.scalar(select(func.max(Auditoria.id))) or 0
        except Exception:
            return 0

    def _poll_audit_changes(self) -> None:
        last_id = self._last_audit_id or 0
        try:
            with database.SessionLocal() as db:
                rows = db.scalars(
                    select(Auditoria)
                    .where(Auditoria.id > last_id)
                    .order_by(Auditoria.id)
                    .limit(200)
                ).all()
        except Exception as exc:
            self.status_changed.emit(f"polling-error: {exc}")
            return

        for row in rows:
            self._last_audit_id = max(self._last_audit_id or 0, row.id)
            self.change_received.emit(
                {
                    "tabla": row.tabla,
                    "registro_id": row.registro_id,
                    "accion": row.accion,
                    "usuario_app": row.usuario_app,
                }
            )


def _postgres_connect_kwargs() -> dict[str, Any]:
    url = database.engine.url
    kwargs: dict[str, Any] = {}
    if url.host:
        kwargs["host"] = url.host
    if url.port:
        kwargs["port"] = url.port
    if url.database:
        kwargs["dbname"] = url.database
    if url.username:
        kwargs["user"] = url.username
    if url.password:
        kwargs["password"] = url.password
    kwargs.update(dict(url.query))
    return kwargs


def _decode_payload(payload: str) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"tabla": "*", "accion": "UNKNOWN", "payload": payload}
    if not isinstance(data, dict):
        return {"tabla": "*", "accion": "UNKNOWN", "payload": payload}
    return data
