from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import (
    Trimestre, TrimestreEnum, CursoAcademico
)

@dataclass(slots=True)
class TrimestreDTO:
    id: int
    nombre: TrimestreEnum
    fecha_inicio: date
    fecha_fin: date


def crear_trimestre(
    nombre: TrimestreEnum,
    fecha_inicio: date,
    fecha_fin: date
) -> int:
    with SessionLocal() as db:

        tri = Trimestre(
            nombre=nombre,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
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