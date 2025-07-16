"""
Controller for managing 'lugar' entities in the application.
Includes data transfer objects (DTOs) for validation and conversion,
and CRUD operations using SQLAlchemy's ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError
from database import SessionLocal
from models import Actividad, Lugar

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class LugarDTO:
    id: int | None = None
    nombre: str
    direccion: str | None = None

class LugarUpdateDTO(BaseModel):
    nombre: str | None = None
    direccion: str | None = None

def _to_dto(lugar: Lugar) -> LugarDTO:
    return LugarDTO(
        id=lugar.id,
        nombre=lugar.nombre,
        direccion=lugar.direccion
    )

# ───────────────── CRUD ─────────────────
def registrar_lugar(data: dict) -> int:
    """Crea un nuevo lugar; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = LugarDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")
    
    try:
        nuevo_lugar = Lugar(
            nombre=dto.nombre,
            direccion=dto.direccion
        )
        with SessionLocal() as db:
            db.add(nuevo_lugar)
            db.commit()
            db.refresh(nuevo_lugar)
            return nuevo_lugar.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar lugar: {e.orig}")
    
def modificar_lugar(lugarID: int, cambios: dict) -> None:
    try:
        dto = LugarUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        lugar = db.get(Lugar, lugarID)
        if not lugar:
            raise ValueError("Lugar inexistent")
        
        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(lugar, k, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar lugar: {e.orig}")
        
def eliminar_lugar(lugarID: int) -> None:
    with SessionLocal() as db:
        lugar = db.get(Lugar, lugarID)
        if not lugar:
            raise ValueError("Lugar inexistent")
        
        db.delete(lugar)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar lugar: {e.orig}")
        
def consultar_lugar(lugarID: int) -> dict | None:
    with SessionLocal() as db:
        lugar = db.get(Lugar, lugarID)
        return _to_dto(lugar).model_dump() if lugar else None

# ────────────────── Consultas ──────────────────
def consultar_lugares() -> list[dict]:
    with SessionLocal() as db:
        lugares = db.query(Lugar).order_by(Lugar.nombre).all()
        return [_to_dto(l).model_dump() for l in lugares]

def listar_actividades_por_lugar(lugarID: int) -> list[dict]:
    """Devuelve actividades asociadas a un lugar."""
    try:
        with SessionLocal() as db:
            actividades = db.query(Actividad).filter(Actividad.lugarID == lugarID).all()
            return [a.model_dump() for a in actividades]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por lugar: {e}")




