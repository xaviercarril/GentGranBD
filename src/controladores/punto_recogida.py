"""CRUD del catálogo reutilizable de puntos de recogida para viajes."""

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from controladores.dtos_models import PuntoRecogidaDTO, PuntoRecogidaUpdateDTO
from database import SessionLocal
from models import InscripcionSocio, PuntoRecogida


def _nombre_limpio(nombre: str | None) -> str:
    nombre = (nombre or "").strip()
    if not nombre:
        raise ValueError("El nom del lloc de recollida és obligatori.")
    return nombre


def registrar_punto_recogida(data: dict) -> int:
    try:
        dto = PuntoRecogidaDTO(**data)
    except ValidationError as exc:
        raise ValueError(f"Dades d'entrada invàlides: {exc}") from exc

    nombre = _nombre_limpio(dto.nombre)
    direccion = (dto.direccion or "").strip() or None
    with SessionLocal() as db:
        existente = (
            db.query(PuntoRecogida)
            .filter(func.lower(PuntoRecogida.nombre) == nombre.lower())
            .first()
        )
        if existente:
            raise ValueError("Ja existeix un lloc de recollida amb aquest nom.")
        punto = PuntoRecogida(nombre=nombre, direccion=direccion)
        db.add(punto)
        try:
            db.commit()
            db.refresh(punto)
            return punto.id
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ja existeix un lloc de recollida amb aquest nom.") from exc


def modificar_punto_recogida(punto_id: int, cambios: dict) -> None:
    try:
        dto = PuntoRecogidaUpdateDTO(**cambios)
    except ValidationError as exc:
        raise ValueError(f"Dades invàlides: {exc}") from exc

    valores = dto.model_dump(exclude_unset=True)
    if "nombre" in valores:
        valores["nombre"] = _nombre_limpio(valores["nombre"])
    if "direccion" in valores:
        valores["direccion"] = (valores["direccion"] or "").strip() or None

    with SessionLocal() as db:
        punto = db.get(PuntoRecogida, punto_id)
        if not punto:
            raise ValueError("Lloc de recollida inexistent.")
        nombre_anterior = punto.nombre
        if "nombre" in valores:
            duplicado = (
                db.query(PuntoRecogida)
                .filter(
                    PuntoRecogida.id != punto_id,
                    func.lower(PuntoRecogida.nombre) == valores["nombre"].lower(),
                )
                .first()
            )
            if duplicado:
                raise ValueError("Ja existeix un lloc de recollida amb aquest nom.")
        for campo, valor in valores.items():
            setattr(punto, campo, valor)
        if "nombre" in valores and valores["nombre"] != nombre_anterior:
            db.query(InscripcionSocio).filter(
                func.lower(InscripcionSocio.lugarRecogida) == nombre_anterior.lower()
            ).update(
                {InscripcionSocio.lugarRecogida: valores["nombre"]},
                synchronize_session=False,
            )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Ja existeix un lloc de recollida amb aquest nom.") from exc


def eliminar_punto_recogida(punto_id: int) -> None:
    with SessionLocal() as db:
        punto = db.get(PuntoRecogida, punto_id)
        if not punto:
            raise ValueError("Lloc de recollida inexistent.")
        db.delete(punto)
        db.commit()


def consultar_puntos_recogida() -> list[dict]:
    with SessionLocal() as db:
        puntos = db.query(PuntoRecogida).order_by(PuntoRecogida.nombre).all()
        return [
            {"id": punto.id, "nombre": punto.nombre, "direccion": punto.direccion}
            for punto in puntos
        ]
