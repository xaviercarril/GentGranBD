from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from controladores.trimestre import TrimestreDTO, registrar_trimestre
from database import SessionLocal
from models import Actividad, CursoAcademico

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class CursoAcademicoDTO:
  id: int
  nombre: str
  fechaInicio: date
  fechaFin: date

class CursoAcademicoUpdateDTO(BaseModel):
  nombre: str | None = None
  fechaInicio: date | None = None
  fechaFin: date | None = None

def _to_dto(curso: CursoAcademico) -> CursoAcademicoDTO:
  return CursoAcademicoDTO(
    id=curso.id,
    nombre=curso.nombre,
    fechaInicio=curso.fechaInicio,
    fechaFin=curso.fechaFin
  )
  
# ───────────────── CRUD ─────────────────
def registrar_cursoA(datos: dict) -> int:
  """Crea un nuevo curso académico; devuelve su ID."""
  try:
    dto = CursoAcademicoDTO(**datos)
  except ValueError as e:
    raise ValueError(f"Datos inválidos: {e}")
  
  try:
    nuevo_curso = CursoAcademico(
      nombre=dto.nombre,
      fechaInicio=dto.fechaInicio,
      fechaFin=dto.fechaFin
    )
    with SessionLocal() as db:
      db.add(nuevo_curso)
      db.commit()
      db.refresh(nuevo_curso)
      return nuevo_curso.id
  except IntegrityError as e:
    raise ValueError(f"Error al registrar curso académico: {e.orig}")
  

def modificar_cursoA(cursoAcademicoID: int, cambios: dict) -> None:
  try:
    dto = CursoAcademicoUpdateDTO(**cambios)
  except ValueError as e:
    raise ValueError(f"Datos inválidos: {e}")

  with SessionLocal() as db:
    curso = db.get(CursoAcademico, cursoAcademicoID)
    if not curso:
      raise ValueError("Curso inexistent")
    
    try:
      for k, v in dto.model_dump(exclude_unset=True).items():
        setattr(curso, k, v)
      db.commit()
    except AttributeError as e:
      db.rollback()
      raise ValueError(f"Campo no válido: {e}")
    except IntegrityError as e:
      db.rollback()
      raise ValueError(f"Error al modificar curso académico: {e.orig}")
    db.commit()

def consultar_cursoA(cursoAcademicoID: int) -> dict | None:
  try:
    with SessionLocal() as db:
      curso = db.get(CursoAcademico, cursoAcademicoID)
      if curso:
        return _to_dto(curso).model_dump()
      return None
  except Exception as e:
    raise ValueError(f"Error al consultar curso académico: {e}")
  
def eliminar_cursoA(cursoAcademicoID: int) -> None:
  """Elimina un curso académico por su ID."""
  try:
    with SessionLocal() as db:
      curso = db.get(CursoAcademico, cursoAcademicoID)
      if not curso:
        raise ValueError("Curso inexistent")
      db.delete(curso)
      db.commit()
  except Exception as e:
    raise ValueError(f"Error al eliminar curso académico: {e}")
  
# ────────────────── Consultas ──────────────────
def listar_cursosA() -> list[dict]:
  """Devuelve todos los cursos académicos"""
  with SessionLocal() as db:
    cursos = db.query(CursoAcademico).order_by(CursoAcademico.fechaInicio).all()
    return [_to_dto(c).model_dump() for c in cursos]

def listar_trimestres_por_cursoA(cursoAcademicoID: int) -> list[dict]:
  """Devuelve los trimestres de un curso académico."""
  with SessionLocal() as db:
    trimestres = db.query(TrimestreDTO).filter(TrimestreDTO.cursoAcademicoID == cursoAcademicoID).all()
    return [t.model_dump() for t in trimestres]
  
def listar_actividades_por_CursoAcademico(cursoAcademicoID: int) -> list[dict]:
    """Devuelve actividades de un curso académico."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).filter(Actividad.cursoAcademicoID == cursoAcademicoID).all()
            return [a.model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por curso: {e}")
  
# ────────────────── Generadores ──────────────────
def generar_T1(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 1 para el curso académico."""
    nuevoTrim = registrar_trimestre(
        nombre="T1",
        fechaInicio=data_inicio,
        fechaFin=data_fin,
        cursoAcademicoID=cursoAcademicoID
    )
    return nuevoTrim.id

def generar_T2(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 2 para el curso académico."""
    nuevoTrim = registrar_trimestre(
        nombre="T2",
        fechaInicio=data_inicio,
        fechaFin=data_fin,
        cursoAcademicoID=cursoAcademicoID
    )
    return nuevoTrim.id

def generar_T3(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 3 para el curso académico."""
    nuevoTrim = registrar_trimestre(
        nombre="T3",
        fechaInicio=data_inicio,
        fechaFin=data_fin,
        cursoAcademicoID=cursoAcademicoID
    )
    return nuevoTrim.id

def generar_T4(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 4 para el curso académico."""
    nuevoTrim = registrar_trimestre(
        nombre="T4",
        fechaInicio=data_inicio,
        fechaFin=data_fin,
        cursoAcademicoID=cursoAcademicoID
    )
    return nuevoTrim.id