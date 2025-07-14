from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import date
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from models import CursoAcademico


@dataclass(slots=True)
class CursoAcademicoDTO:
  id: int
  nombre: str
  fecha_inicio: date
  fecha_fin: date


def consultar_curso_academico(curso_id: int) -> dict | None:
  with SessionLocal() as db:
    curso = db.get(CursoAcademico, curso_id)
    if curso:
      return asdict(CursoAcademicoDTO(
        id=curso.id,
        nombre=curso.nombre,
        fecha_inicio=curso.fecha_inicio,
        fecha_fin=curso.fecha_fin
      ))
    return None
  
# ───────────────── CRUD ─────────────────
def registrar_curso_academico(datos: dict) -> int:
  """Crea un nuevo curso académico; devuelve su ID."""
  try:
    nuevo_curso = CursoAcademico(
      nombre=datos['nombre'],
      fecha_inicio=datos['fecha_inicio'],
      fecha_fin=datos['fecha_fin']
    )
    with SessionLocal() as db:
      db.add(nuevo_curso)
      db.commit()
      db.refresh(nuevo_curso)
      return nuevo_curso.id
  except IntegrityError as e:
    raise ValueError(f"Error al registrar curso académico: {e.orig}")


def listar_cursos() -> list[dict]:
  """Devuelve todos los cursos académicos"""
  with SessionLocal() as db:
    cursos = db.query(CursoAcademico).order_by(CursoAcademico.fecha_inicio).all()
    return [
      asdict(
        CursoAcademicoDTO(
          id=c.id,
          nombre=c.nombre,
          fecha_inicio=c.fecha_inicio,
          fecha_fin=c.fecha_fin,
        )
      ) for c in cursos
    ]


def modificar_curso(curso_id: int, cambios: dict) -> None:
  with SessionLocal() as db:
    curso = db.get(CursoAcademico, curso_id)
    if not curso:
      raise ValueError("Curso inexistent")
    for k, v in cambios.items():
      setattr(curso, k, v)
    db.commit()


def eliminar_curso(curso_id: int) -> None:
  with SessionLocal() as db:
    curso = db.get(CursoAcademico, curso_id)
    if not curso:
      raise ValueError("Curso inexistent")
    db.delete(curso)
    db.commit()