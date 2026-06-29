from __future__ import annotations
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from controladores.dtos_models import CursoAcademicoDTO, CursoAcademicoUpdateDTO
from controladores.trimestre import registrar_trimestre
from controladores.dtos import actividad_to_dto, cursoA_to_dto, trimestre_to_dto
from database import SessionLocal
from models import Actividad, CursoAcademico, Trimestre, TrimestreEnum, TipoActividadEnum

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

    with SessionLocal() as db:
      curso = db.get(CursoAcademico, cursoAcademicoID)
      return cursoA_to_dto(curso).model_dump() if curso else None

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


def duplicar_cursoA(cursoAcademicoID: int, nuevo_nombre: str) -> int:
  """Duplica un curso académico con sus trimestres y actividades."""
  nombre = (nuevo_nombre or "").strip()
  if not nombre:
    raise ValueError("El nom del nou curs és obligatori.")

  with SessionLocal() as db:
    curso_origen = db.get(CursoAcademico, cursoAcademicoID)
    if not curso_origen:
      raise ValueError("Curso inexistent")

    if nombre == curso_origen.nombre:
      raise ValueError("El nou curs ha de tenir un nom diferent.")

    nombre_existente = (
      db.query(CursoAcademico)
      .filter(CursoAcademico.nombre == nombre)
      .first()
    )
    if nombre_existente:
      raise ValueError("Ja existeix un curs acadèmic amb aquest nom.")

    try:
      nuevo_curso = CursoAcademico(
        nombre=nombre,
        fechaInicio=curso_origen.fechaInicio,
        fechaFin=curso_origen.fechaFin,
      )
      db.add(nuevo_curso)
      db.flush()

      trimestres = (
        db.query(Trimestre)
        .filter(Trimestre.cursoAcademicoID == cursoAcademicoID)
        .order_by(Trimestre.id)
        .all()
      )
      for trimestre in trimestres:
        db.add(Trimestre(
          nombre=trimestre.nombre,
          fechaInicio=trimestre.fechaInicio,
          fechaFin=trimestre.fechaFin,
          cursoAcademicoID=nuevo_curso.id,
        ))

      actividades = (
        db.query(Actividad)
        .filter(Actividad.cursoAcademicoID == cursoAcademicoID)
        .order_by(Actividad.id)
        .all()
      )
      for actividad in actividades:
        db.add(Actividad(
          nombre=actividad.nombre,
          tipo=actividad.tipo,
          descripcion=actividad.descripcion,
          numMaxAlumnos=actividad.numMaxAlumnos,
          cursoAcademicoID=nuevo_curso.id,
          lugarID=actividad.lugarID,
          personalID=actividad.personalID,
          precio_matricula=actividad.precio_matricula,
        ))

      db.commit()
      return nuevo_curso.id
    except IntegrityError as e:
      db.rollback()
      raise ValueError(f"Error al duplicar curso académico: {e.orig}")
    except Exception as e:
      db.rollback()
      raise ValueError(f"Error al duplicar curso académico: {e}") from e

# ────────────────── Consultas ──────────────────
def listar_cursosA() -> list[dict]:
  """Devuelve todos los cursos académicos"""
  with SessionLocal() as db:
    cursos = db.query(CursoAcademico).order_by(CursoAcademico.fechaInicio).all()
    return [cursoA_to_dto(c).model_dump() for c in cursos]

def listar_trimestres_por_cursoA(cursoAcademicoID: int) -> list[dict]:
  """Devuelve los trimestres de un curso académico."""
  with SessionLocal() as db:
    trimestres = db.query(Trimestre).filter(Trimestre.cursoAcademicoID == cursoAcademicoID).all()
    return [trimestre_to_dto(t).model_dump() for t in trimestres]
  
def _normalizar_tipo_actividad(tipo) -> TipoActividadEnum | None:
    if tipo is None:
        return None
    if isinstance(tipo, TipoActividadEnum):
        return tipo
    text = str(tipo).strip().upper()
    aliases = {
        "CURSO": "CURS",
        "CURSOS": "CURS",
        "CURS": "CURS",
        "TALLER": "CURS",
        "TALLERS": "CURS",
        "TALLERES": "CURS",
        "VIAJE": "VIATGE",
        "VIAJES": "VIATGE",
        "VIATGE": "VIATGE",
        "VIATGES": "VIATGE",
    }
    return TipoActividadEnum(aliases.get(text, text))


def listar_actividades_por_CursoAcademico(cursoAcademicoID: int, tipo=None) -> list[dict]:
    """Devuelve actividades de un curso académico."""
    try:
        tipo_enum = _normalizar_tipo_actividad(tipo)
        with SessionLocal() as db:
            query = db.query(Actividad).filter(Actividad.cursoAcademicoID == cursoAcademicoID)
            if tipo_enum is not None:
                query = query.filter(Actividad.tipo == tipo_enum)
            acts = query.order_by(Actividad.nombre).all()
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
