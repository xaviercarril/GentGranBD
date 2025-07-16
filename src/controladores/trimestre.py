from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Clase, Trimestre, TrimestreEnum, CursoAcademico
)

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class TrimestreDTO(BaseModel):
    id: int
    nombre: TrimestreEnum
    fecha_inicio: date
    fecha_fin: date
    cursoA_id: int

class TrimestreUpdateDTO(BaseModel):
    nombre: TrimestreEnum | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    cursoA_id: int | None = None

def _to_dto(trimestre: Trimestre) -> TrimestreDTO:
    return TrimestreDTO(
        id=trimestre.id,
        nombre=trimestre.nombre,
        fecha_inicio=trimestre.fecha_inicio,
        fecha_fin=trimestre.fecha_fin,
        cursoA_id=trimestre.cursoA_id
    )

# ───────────────── CRUD ─────────────────
def registrar_trimestre(datos: dict) -> int:
    """Crea un nuevo trimestre; devuelve su ID."""
    try:
        dto = TrimestreDTO(**datos)
    except ValueError as e:
        raise ValueError(f"Datos inválidos: {e}")

    try:
        nuevo_trimestre = Trimestre(
            nombre=dto.nombre,
            fecha_inicio=dto.fecha_inicio,
            fecha_fin=dto.fecha_fin,
            cursoA_id=dto.cursoA_id
        )
        with SessionLocal() as db:
            db.add(nuevo_trimestre)
            db.commit()
            db.refresh(nuevo_trimestre)
            return nuevo_trimestre.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar trimestre: {e.orig}")
    
def modificar_trimestre(trimestre_id: int, cambios: dict) -> None:
    try:
        dto = TrimestreUpdateDTO(**cambios)
    except ValueError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestre_id)
        if not trimestre:
            raise ValueError("Trimestre inexistent")
        
        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(trimestre, k, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar trimestre: {e.orig}")

def eliminar_trimestre(trimestre_id: int) -> None:
    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestre_id)
        if not trimestre:
            raise ValueError("Trimestre inexistent")
        
        try:
            db.delete(trimestre)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar trimestre: {e.orig}")

def consultar_trimestre(trimestre_id: int) -> dict | None:
    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestre_id)
        if trimestre:
            return asdict(
                TrimestreDTO(
                    id=trimestre.id,
                    nombre=trimestre.nombre,
                    fecha_inicio=trimestre.fecha_inicio,
                    fecha_fin=trimestre.fecha_fin,
                    cursoA_id=trimestre.cursoA_id
                )
            )
        return None
# ────────────────── Consultas ──────────────────
def listar_clases_por_trimestre(trimestre_id: int) -> list[dict]:
    """Lista las clases de un trimestre."""
    try:
        with SessionLocal() as db:
            clases = db.query(Clase).filter(Clase.trimestre_id == trimestre_id).all()
            return [clase.model_dump() for clase in clases]
    except Exception as e:
        raise ValueError(f"Error al listar clases: {e}")
    