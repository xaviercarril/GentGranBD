from __future__ import annotations
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from controladores.trimestre import registrar_trimestre, _to_dto as trimestre_to_dto
from controladores.actividades import _to_dto as actividad_to_dto
from database import SessionLocal
from models import Actividad, CursoAcademico, Trimestre, TrimestreEnum

# ───────────────────── DTO ─────────────────────
class CursoAcademicoDTO(BaseModel):
  id: int | None = None
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
      id=dto.id,
      nombre=dto.nombre,
      fechaInicio=dto.fechaInicio,
      fechaFin=dto.fechaFin
    )

    with SessionLocal() as db:
      db.add(nuevo_curso)
      db.commit()
      db.refresh(nuevo_curso)
  except IntegrityError as e:
    raise ValueError(f"Error al registrar curso académico: {e.orig}")
  
  try:
    inicio = dto.fechaInicio
    t1_inicio = inicio
    t1_fin = (inicio + relativedelta(months=3)).replace(day=1) - timedelta(days=1)

    t2_inicio = t1_fin + timedelta(days=1)
    t2_fin = (t2_inicio + relativedelta(months=3)).replace(day=1) - timedelta(days=1)

    t3_inicio = t2_fin + timedelta(days=1)
    t3_fin = (t3_inicio + relativedelta(months=3)).replace(day=1) - timedelta(days=1)

    t4_inicio = t3_fin + timedelta(days=1)
    t4_fin = (t4_inicio + relativedelta(months=3)).replace(day=1) - timedelta(days=1)

    generar_T1(nuevo_curso.id, t1_inicio, t1_fin)
    generar_T2(nuevo_curso.id, t2_inicio, t2_fin)
    generar_T3(nuevo_curso.id, t3_inicio, t3_fin)
    generar_T4(nuevo_curso.id, t4_inicio, t4_fin)
  except Exception as e:
    raise ValueError(f"Error al generar trimestres: {e}")
    
  except Exception as e:
    raise ValueError(f"Error al generar trimestres: {e}")
  
  return nuevo_curso.id
  

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
    trimestres = db.query(Trimestre).filter(Trimestre.cursoAcademicoID == cursoAcademicoID).all()
    return [trimestre_to_dto(t).model_dump() for t in trimestres]
  
def listar_actividades_por_CursoAcademico(cursoAcademicoID: int) -> list[dict]:
    """Devuelve actividades de un curso académico."""
    try:
        with SessionLocal() as db:
            acts = db.query(Actividad).filter(Actividad.cursoAcademicoID == cursoAcademicoID).all()
            return [actividad_to_dto(a).model_dump() for a in acts]
    except Exception as e:
        raise ValueError(f"Error al listar actividades por curso: {e}")
  
# ────────────────── Generadores ──────────────────
def generar_T1(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 1 para el curso académico."""
    nuevoTrimID = registrar_trimestre({
      "nombre": TrimestreEnum.T1,
      "fechaInicio": data_inicio,
      "fechaFin": data_fin,
      "cursoAcademicoID": cursoAcademicoID
    })
    return nuevoTrimID

def generar_T2(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 2 para el curso académico."""
    nuevoTrimID = registrar_trimestre({
      "nombre": TrimestreEnum.T2,
      "fechaInicio": data_inicio,
      "fechaFin": data_fin,
      "cursoAcademicoID": cursoAcademicoID
    })
    return nuevoTrimID

def generar_T3(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
    """Genera un trimestre 3 para el curso académico."""
    nuevoTrimID = registrar_trimestre({
      "nombre": TrimestreEnum.T3,
      "fechaInicio": data_inicio,
      "fechaFin": data_fin,
      "cursoAcademicoID": cursoAcademicoID
    })
    return nuevoTrimID

def generar_T4(cursoAcademicoID: int, data_inicio: date, data_fin: date) -> int:
  """Genera un trimestre 4 para el curso académico."""
  nuevoTrimID = registrar_trimestre({
    "nombre": TrimestreEnum.T4,
    "fechaInicio": data_inicio,
    "fechaFin": data_fin,
    "cursoAcademicoID": cursoAcademicoID
  })
  return nuevoTrimID