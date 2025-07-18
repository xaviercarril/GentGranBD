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
class TrimestreDTO(BaseModel):
    id: int | None = None
    nombre: TrimestreEnum
    fechaInicio: date
    fechaFin: date
    cursoAcademicoID: int

class TrimestreUpdateDTO(BaseModel):
    nombre: TrimestreEnum | None = None
    fechaInicio: date | None = None
    fechaFin: date | None = None
    cursoAcademicoID: int | None = None

def _to_dto(trimestre: Trimestre) -> TrimestreDTO:
    return TrimestreDTO(
        id=trimestre.id,
        nombre=trimestre.nombre,
        fechaInicio=trimestre.fechaInicio,
        fechaFin=trimestre.fechaFin,
        cursoAcademicoID=trimestre.cursoAcademicoID
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
            fechaInicio=dto.fechaInicio,
            fechaFin=dto.fechaFin,
            cursoAcademicoID=dto.cursoAcademicoID
        )
        with SessionLocal() as db:
            db.add(nuevo_trimestre)
            db.commit()
            db.refresh(nuevo_trimestre)
            return nuevo_trimestre.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar trimestre: {e.orig}")
    
def modificar_trimestre(trimestreID: int, cambios: dict) -> None:
    try:
        dto = TrimestreUpdateDTO(**cambios)
    except ValueError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestreID)
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

def eliminar_trimestre(trimestreID: int) -> None:
    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestreID)
        if not trimestre:
            raise ValueError("Trimestre inexistent")
        
        try:
            db.delete(trimestre)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar trimestre: {e.orig}")

def consultar_trimestre(trimestreID: int) -> dict | None:
    with SessionLocal() as db:
        trimestre = db.get(Trimestre, trimestreID)
        if trimestre:
            return asdict(
                TrimestreDTO(
                    id=trimestre.id,
                    nombre=trimestre.nombre,
                    fechaInicio=trimestre.fechaInicio,
                    fechaFin=trimestre.fechaFin,
                    cursoAcademicoID=trimestre.cursoAcademicoID
                )
            )
        return None
# ────────────────── Consultas ──────────────────
def listar_clases_por_trimestre(trimestreID: int) -> list[dict]:
    """Lista las clases de un trimestre."""
    try:
        with SessionLocal() as db:
            clases = db.query(Clase).filter(Clase.trimestreID == trimestreID).all()
            return [clase.model_dump() for clase in clases]
    except Exception as e:
        raise ValueError(f"Error al listar clases: {e}")
    