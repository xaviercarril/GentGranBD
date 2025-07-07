"""
Controlador de ACTIVIDADES – capa de negocio
No expone objetos SQLAlchemy a la UI; devuelve y recibe dicts/DTOs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Actividad, Curso, Taller,
    Trimestre, TrimestreEnum
)

# ───────────────────── DTO ─────────────────────
@dataclass(slots=True)
class ActividadDTO:
    id: int
    nombre: str
    tipo: str
    max_alumnos: int | None


def _to_dto(a: Actividad) -> ActividadDTO:
    return ActividadDTO(
        id=a.id,
        nombre=a.nombre,
        tipo=a.tipo,
        max_alumnos=a.numero_maximo_alumnos,
    )


# ───────────────── API pública ─────────────────
def listar_actividades() -> list[dict]:
    """Devuelve todas las actividades como lista de dicts."""
    with SessionLocal() as db:
        acts = db.query(Actividad).order_by(Actividad.nombre).all()
        return [asdict(_to_dto(a)) for a in acts]


def registrar_actividad(datos: dict) -> int:
    """Crea curso, taller o actividad genérica; devuelve ID."""
    tipo = datos.get("tipo")
    clase = {"curso": Curso, "taller": Taller}.get(tipo, Actividad)

    nueva = clase(
        nombre=datos["nombre"],
        numero_maximo_alumnos=datos.get("numero_maximo_alumnos"),
        lugar=datos.get("lugar"),
        observaciones=datos.get("observaciones"),
        personal_id=datos.get("personal_id"),
        precio_matricula=datos.get("precio_matricula", 0.0),
        descripcion_fecha=datos.get("descripcion_fecha"),
        curso_academico=datos.get("curso_academico"),
        tipo=tipo
    )
    with SessionLocal() as db:
        db.add(nueva)
        db.commit()
        db.refresh(nueva)
        return nueva.id


def modificar_actividad(actividad_id: int, cambios: dict) -> None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        if not act:
            raise ValueError("Actividad no encontrada")
        for k, v in cambios.items():
            setattr(act, k, v)
        db.commit()


def eliminar_actividad(actividad_id: int) -> None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        if not act:
            raise ValueError("Actividad no encontrada")
        db.delete(act)
        db.commit()


def consultar_actividad(actividad_id: int) -> dict | None:
    with SessionLocal() as db:
        act = db.get(Actividad, actividad_id)
        return asdict(_to_dto(act)) if act else None


# ───────────────── Trimestres (sólo para Curso) ─────────────────
@dataclass(slots=True)
class TrimestreDTO:
    id: int
    nombre: TrimestreEnum
    fecha_inicio: date
    fecha_fin: date


def crear_trimestre(
    curso_id: int,
    nombre: TrimestreEnum,
    fecha_inicio: date,
    fecha_fin: date
) -> int:
    with SessionLocal() as db:
        curso = db.get(Curso, curso_id)
        if not curso:
            raise ValueError("Curso no encontrado")

        tri = Trimestre(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            curso_id=curso_id
        )
        db.add(tri)
        db.commit()
        db.refresh(tri)
        return tri.id


def consultar_trimestres(
    curso_id: int,
    nombre: TrimestreEnum | None = None
) -> list[dict]:
    with SessionLocal() as db:
        q = db.query(Trimestre).filter(Trimestre.curso_id == curso_id)
        if nombre:
            q = q.filter(Trimestre.nombre == nombre)
        trs = q.all()
        return [
            asdict(
                TrimestreDTO(
                    id=t.id,
                    nombre=t.nombre,
                    fecha_inicio=t.fecha_inicio,
                    fecha_fin=t.fecha_fin
                )
            ) for t in trs
        ]


def consultar_curso_academico(curso_id: int) -> str | None:
    with SessionLocal() as db:
        curso = db.get(Curso, curso_id)
        return curso.curso_academico if curso else None