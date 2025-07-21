"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Actividad, Clase, InscripcionSocio
)

# ───────────────────── DTO ─────────────────────
class ActividadDTO(BaseModel):
    id: int | None = None
    nombre: str
    descripcion: str | None = None
    numMaxAlumnos: int | None = 0
    cursoAcademico_id: int
    lugarID: int | None = None
    personalID: int | None = None   
    precio_matricula: float = 0.0

class ActividadUpdateDTO(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    numMaxAlumnos: int | None = None
    cursoAcademico_id: int | None = None
    lugarID: int | None = None
    personalID: int | None = None
    precio_matricula: float | None = None

def _to_dto(a: Actividad) -> ActividadDTO:
    return ActividadDTO(
        id=a.id,
        nombre=a.nombre,
        descripcion=a.descripcion,
        numMaxAlumnos=a.numMaxAlumnos,
        cursoAcademico_id=a.cursoAcademicoID,
        lugarID=a.lugarID,
        personalID=a.personalID,
        precio_matricula=a.precio_matricula
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
            descripcion=dto.descripcion,
            numMaxAlumnos=dto.numMaxAlumnos,
            cursoAcademicoID=dto.cursoAcademico_id,
            lugarID=dto.lugarID,
            personalID=dto.personalID,
            precio_matricula=dto.precio_matricula,
        )
        with SessionLocal() as db:
            db.add(nueva)
            db.commit()
            db.refresh(nueva)
            return nueva.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar actividad: {e.orig}")

def modificar_actividad(actividadID: int, newData: dict) -> None:
    try:
        dto = ActividadUpdateDTO(**newData)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos al modificar clase: {e}")
    
    with SessionLocal() as db:
        act = db.get(Actividad, actividadID)
        if not act:
            raise ValueError("Actividad no encontrada")
        try:
            mapeo = {
                "numMaxAlumnos": "numMaxAlumnos",
                "cursoAcademico_id": "cursoAcademicoID",
                "personalID": "personalID",
                "lugarID": "lugarID",  # Este ya coincide, pero lo puedes mantener por consistencia
            }

            for k, v in dto.model_dump(exclude_unset=True).items():
                attr = mapeo.get(k, k)  # Usa el mapeo si existe, si no el mismo nombre
                setattr(act, attr, v)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo no válido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar actividad: {e.orig}")

def consultar_actividad(actividadID: int) -> dict | None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividadID)
        return _to_dto(act).model_dump() if act else None

def eliminar_actividad(actividadID: int) -> None:
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            if not act:
                raise ValueError("Actividad no encontrada")
            db.delete(act)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar actividad: {e.orig}")


# ────────────────── Consultas ────────────

def listar_actividades() -> list[dict]:
    """Devuelve todas las actividades como lista de dicts."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).order_by(Actividad.nombre).all()
            return [_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades: {e}")

def listar_incripciones_por_Actividad(actividadID: int) -> list[dict]:
    """Devuelve inscripciones de una actividad."""
    try:
        with SessionLocal() as db:
            inscripciones = db.query(InscripcionSocio).filter(InscripcionSocio.actividadID == actividadID).all()
            return [i.model_dump() for i in inscripciones]
    except Exception as e:
        raise ValueError(f"Error al listar inscripciones por actividad: {e}")
    
def listar_clases_por_Actividad(actividadID: int) -> list[dict] :
    """Devuelve clases de una actividad."""
    try:
        with SessionLocal() as db:
            clases = db.query(Clase).filter(Clase.actividadID == actividadID).all()
            return [c.model_dump() for c in clases] if clases else None
    except Exception as e:
        raise ValueError(f"Error al listar clases por actividad: {e}")
    
    
def consultar_lugarID_Actividad(actividadID: int) -> int | None:
    """Consulta el lugar de una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.lugarID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar lugar: {e}")

def consultar_cursoAcademicoID_Actividad(actividadID: int) -> int | None:
    """Consulta el curso académico de una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.cursoAcademicoID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar curso académico: {e}")
    
def consultar_personalID_Actividad(actividadID: int) -> int | None:
    """Consulta el personal asignado a una actividad."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, actividadID)
            return act.personalID if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar personal de actividad: {e}")
    

