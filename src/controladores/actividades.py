"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from datetime import date, timedelta
from pytest import Session
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Actividad, Clase, CursoAcademico
)

# ───────────────────── DTO ─────────────────────
class ActividadDTO(BaseModel):
    id: int | None = None
    nombre: str
    max_alumnos: int = 1
    lugar: str | None = None
    precio_matricula: float = 0.0
    observaciones: str | None = None

class ActividadUpdateDTO(BaseModel):
    nombre: str | None = None
    max_alumnos: int | None = None
    lugar: str | None = None
    precio_matricula: float | None = None
    observaciones: str | None = None

def _to_dto(a: Actividad) -> ActividadDTO:
    return ActividadDTO(
        id=a.id,
        nombre=a.nombre,
        max_alumnos=a.numero_maximo_alumnos,
        lugar=a.lugar,
        precio_matricula=a.precio_matricula,
        observaciones=a.observaciones
    )


# ───────────────── CRUD ─────────────────
def registrar_actividad(data: dict) -> int:
    """Crea actividad; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = ActividadDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")
    try:
        nueva = Actividad(
            nombre=dto.nombre,
            numero_maximo_alumnos=dto.max_alumnos,
            lugar=dto.lugar,
            precio_matricula=dto.precio_matricula,
            observaciones=dto.observaciones
        )
        with SessionLocal() as db:
            db.add(nueva)
            db.commit()
            db.refresh(nueva)
            return nueva.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar actividad: {e.orig}")
    
def listar_actividades() -> list[dict]:
    """Devuelve todas las actividades como lista de dicts."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).order_by(Actividad.nombre).all()
            return [_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades: {e}")


def modificar_actividad(actividad_id: int, newData: dict) -> None:
    try:
        dto = ActividadUpdateDTO(**newData)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos al modificar clase: {e}")
    
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        if not act:
            raise ValueError("Actividad no encontrada")
        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(act, k, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo no válido: {e}")


def eliminar_actividad(actividad_id: int) -> None:
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividad_id)
            if not act:
                raise ValueError("Actividad no encontrada")
            db.delete(act)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar actividad: {e.orig}")


def consultar_actividad(actividad_id: int) -> dict | None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        return _to_dto(act).model_dump() if act else None


# ────────────────── CRUD API ──────────────────
def listar_actividades_por_CursoAcademico(curso_id: int) -> list[dict]:
    """Devuelve actividades de un curso académico."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).filter(Actividad.curso_academico_id == curso_id).all()
            return [_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por curso: {e}")
    

