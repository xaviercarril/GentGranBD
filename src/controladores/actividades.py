"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Actividad, Clase, CursoAcademico, InscripcionSocio, ActividadPersonal, Lugar
)

# ───────────────────── DTO ─────────────────────
class ActividadDTO(BaseModel):
    id: int | None = None
    nombre: str
    max_alumnos: int = 1
    cursoAcademico_id: int
    lugar_id: int | None = None
    precio_matricula: float = 0.0
    observaciones: str | None = None

class ActividadUpdateDTO(BaseModel):
    nombre: str | None = None
    max_alumnos: int | None = None
    cursoAcademico_id: int | None = None
    lugar_id: int | None = None
    precio_matricula: float | None = None
    observaciones: str | None = None

def _to_dto(a: Actividad) -> ActividadDTO:
    return ActividadDTO(
        id=a.id,
        nombre=a.nombre,
        max_alumnos=a.numero_maximo_alumnos,
        cursoAcademico_id=a.cursoAcademico_id,
        lugar_id=a.lugar_id,
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
            cursoAcademico_id=dto.cursoAcademico_id,
            lugar_id=dto.lugar_id,
            precio_matricula=dto.precio_matricula,
            observaciones=dto.observaciones,
        )
        with SessionLocal() as db:
            db.add(nueva)
            db.commit()
            db.refresh(nueva)
            return nueva.id
    except IntegrityError as e:
        raise ValueError(f"Error al registrar actividad: {e.orig}")
    

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
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar actividad: {e.orig}")

def consultar_actividad(actividad_id: int) -> dict | None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        return _to_dto(act).model_dump() if act else None

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


# ────────────────── Consultas ──────────────────

def listar_actividades() -> list[dict]:
    """Devuelve todas las actividades como lista de dicts."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).order_by(Actividad.nombre).all()
            return [_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades: {e}")

def listar_incripciones_por_Actividad(actividad_id: int) -> list[dict]:
    """Devuelve inscripciones de una actividad."""
    try:
        with SessionLocal() as db:
            inscripciones = db.query(InscripcionSocio).filter(InscripcionSocio.actividad_id == actividad_id).all()
            return [i.model_dump() for i in inscripciones]
    except Exception as e:
        raise ValueError(f"Error al listar inscripciones por actividad: {e}")
    
def listar_clases_por_Actividad(actividad_id: int) -> list[dict] :
    """Devuelve clases de una actividad."""
    try:
        with SessionLocal() as db:
            clases = db.query(Clase).filter(Clase.actividad_id == actividad_id).all()
            return [c.model_dump() for c in clases] if clases else None
    except Exception as e:
        raise ValueError(f"Error al listar clases por actividad: {e}")
    
def listar_actividadPersonal_por_Actividad(actividad_id: int) -> dict | None:
    """Devuelve datos de una actividad específica."""
    try:
        with SessionLocal() as db:
            act = db.query(ActividadPersonal).filter(ActividadPersonal.actividad_id == actividad_id).first()
            return [ap.model_dump() for ap in act] if act else None
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")
    
def consultar_lugar_Actividad(actividad_id: int) -> dict | None:
    """Consulta el lugar de una actividad."""
    try:
        with SessionLocal() as db:
            lugar = db.get(Lugar, actividad_id)
            return _to_dto(lugar).model_dump() if lugar else None
    except Exception as e:
        raise ValueError(f"Error al consultar lugar: {e}")
    
def consultar_cursoA_Actividad(actividad_id: int) -> dict | None:
    """Consulta el curso académico de una actividad."""
    try:
        with SessionLocal() as db:
            cursoA = db.get(CursoAcademico, actividad_id)
            return _to_dto(cursoA).model_dump() if cursoA else None
    except Exception as e:
        raise ValueError(f"Error al consultar curso académico: {e}")

