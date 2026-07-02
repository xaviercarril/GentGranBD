from __future__ import annotations

import json
from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy import text

from models import Auditoria, Base


REALTIME_CHANNEL = "gentgran_changes"
_current_username: ContextVar[str] = ContextVar("current_username", default="sistema")
_listeners_installed = False


def set_current_user(user: dict | str | None) -> None:
    if isinstance(user, dict):
        username = user.get("username") or "sistema"
    else:
        username = user or "sistema"
    _current_username.set(str(username))


def get_current_user() -> str:
    return _current_username.get()


def _serialize_value(column_name: str, value: Any) -> Any:
    if column_name in {"password_hash"}:
        return "<oculto>"
    if value is None:
        return None
    if isinstance(value, bytes):
        return f"<binario {len(value)} bytes>"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "... <truncado>"
    return value


def _record_id(target) -> str | None:
    state = inspect(target)
    identity = state.identity
    if not identity:
        identity = tuple(getattr(target, column.key, None) for column in state.mapper.primary_key)
    if not identity or all(value is None for value in identity):
        return None
    if len(identity) == 1:
        return str(identity[0])
    return ",".join(str(value) for value in identity)


def _insert_audit(connection, target, action: str, detail: dict) -> None:
    if isinstance(target, Auditoria):
        return

    table_name = target.__mapper__.local_table.name
    record_id = _record_id(target)
    username = get_current_user()

    connection.execute(
        Auditoria.__table__.insert().values(
            usuario_app=username,
            accion=action,
            tabla=table_name,
            registro_id=record_id,
            detalle=json.dumps(detail, ensure_ascii=False, default=str),
        )
    )
    _notify_realtime_change(connection, table_name, record_id, action, username)


def _notify_realtime_change(connection, table_name: str, record_id: str | None, action: str, username: str) -> None:
    if connection.dialect.name != "postgresql":
        return

    payload = json.dumps(
        {
            "tabla": table_name,
            "registro_id": record_id,
            "accion": action,
            "usuario_app": username,
        },
        ensure_ascii=False,
    )
    connection.execute(
        text("SELECT pg_notify(:channel, :payload)"),
        {"channel": REALTIME_CHANNEL, "payload": payload},
    )


def _column_values(target) -> dict:
    values = {}
    mapper = inspect(target).mapper
    for column in mapper.columns:
        values[column.key] = _serialize_value(column.key, getattr(target, column.key))
    return values


def _after_insert(mapper, connection, target) -> None:
    _insert_audit(connection, target, "CREATE", {"values": _column_values(target)})


def _after_update(mapper, connection, target) -> None:
    changes = {}
    state = inspect(target)
    for column in mapper.columns:
        history = state.attrs[column.key].history
        if not history.has_changes():
            continue
        old_value = history.deleted[0] if history.deleted else None
        new_value = history.added[0] if history.added else getattr(target, column.key)
        changes[column.key] = {
            "old": _serialize_value(column.key, old_value),
            "new": _serialize_value(column.key, new_value),
        }
    if changes:
        _insert_audit(connection, target, "UPDATE", {"changes": changes})


def _after_delete(mapper, connection, target) -> None:
    _insert_audit(connection, target, "DELETE", {"values": _column_values(target)})


def install_audit_listeners() -> None:
    global _listeners_installed
    if _listeners_installed:
        return

    event.listen(Base, "after_insert", _after_insert, propagate=True)
    event.listen(Base, "after_update", _after_update, propagate=True)
    event.listen(Base, "after_delete", _after_delete, propagate=True)
    _listeners_installed = True
