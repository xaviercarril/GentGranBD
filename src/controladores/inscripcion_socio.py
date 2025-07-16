
from pydantic import ValidationError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import InscripcionSocio, Actividad, EstadoInscripcion, MatriculaPago, EstadoPago, Pago, Socio
from controladores.pagos import registrar_pago
from sqlalchemy.exc import IntegrityError
from datetime import date

# ────────────────────── DTO ──────────────────────
class InscripcionSocioDTO(BaseModel):
    socio_id: int
    actividad_id: int
    fecha_inscripcion: date
    estado: EstadoInscripcion = EstadoInscripcion.RESERVA
    observaciones: str | None = None
    fecha_baja: date | None = None

class InscripcionSocioUpdateDTO(BaseModel):
    estado: EstadoInscripcion | None = None
    observaciones: str | None = None
    fecha_baja: date | None = None

def _to_dto(inscripcion: InscripcionSocio) -> InscripcionSocioDTO:
    return InscripcionSocioDTO(
        socio_id=inscripcion.socio_id,
        actividad_id=inscripcion.actividad_id,
        fecha_inscripcion=inscripcion.fecha_inscripcion,
        estado=inscripcion.estado,
        observaciones=inscripcion.observaciones,
        fecha_baja=inscripcion.fecha_baja
    )

# ───────────────── CRUD ─────────────────
def registrar_inscripcion(data: dict) -> int:
    """Registra inscripción de un socio a una actividad; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = InscripcionSocioDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    nueva_inscripcion = InscripcionSocio(
        socio_id=dto.socio_id,
        actividad_id=dto.actividad_id,
        fecha_inscripcion=dto.fecha_inscripcion,
        estado=dto.estado,
        observaciones=dto.observaciones,
        fecha_baja=dto.fecha_baja
    )

    with SessionLocal() as db:
        db.add(nueva_inscripcion)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al registrar inscripción: {e.orig}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al registrar inscripción: {e}")
        db.refresh(nueva_inscripcion)
        return nueva_inscripcion.id

def modificar_inscripcion(inscripcion_id: int, cambios: dict) -> None:
    """Modifica inscripción de un socio a una actividad; recibe ID y dict con cambios."""
    try:
        dto = InscripcionSocioUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos: {e}")

    with SessionLocal() as db:
        inscripcion = db.get(InscripcionSocio, inscripcion_id)
        if not inscripcion:
            raise ValueError("Inscripción no encontrada")

        try:
            for key, value in dto.dict(exclude_unset=True).items():
                setattr(inscripcion, key, value)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar inscripción: {e.orig}")

def consultar_inscripcion(inscripcion_id: int) -> dict | None:
    """Consulta una inscripción por su ID."""
    try:
        with SessionLocal() as db:
            inscripcion = db.get(InscripcionSocio, inscripcion_id)
            if not inscripcion:
                return None
            return _to_dto(inscripcion).model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar inscripción: {e}")

def eliminar_inscripcion(inscripcion_id: int) -> None:
    """Elimina inscripción de un socio a una actividad."""
    with SessionLocal() as db:
        inscripcion = db.get(InscripcionSocio, inscripcion_id)
        if not inscripcion:
            raise ValueError("Inscripción no encontrada")
        
        try:
            db.delete(inscripcion)
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al eliminar inscripción: {e.orig}")

# ────────────────── Consultas ──────────────────
def consultar_actividad_InscripcionSocio(inscripcion_id: int) -> dict | None:
    """Consulta una actividad por la inscripción de un socio."""
    try:
        with SessionLocal() as db:
            act = db.get(Actividad, inscripcion_id)
            if not act:
                return None
            return act.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")

def consultar_socio_InscripcionSocio(inscripcion_id: int) -> dict | None:
    """Consulta un socio por la inscripción a una actividad."""
    try:
        with SessionLocal() as db:
            socio = db.get(Socio, inscripcion_id)
            if not socio:
                return None
            return socio.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar socio: {e}")
    
def listar_pagos_por_InscripcionSocio(inscripcion_id: int) -> list[dict]:
    """Lista los pagos asociados a una inscripción de socio."""
    try:
        with SessionLocal() as db:
            pagos = db.query(Pago).filter(Pago.inscripcion.id == inscripcion_id).all()
            return [pago.model_dump() for pago in pagos]
    except Exception as e:
        raise ValueError(f"Error al listar pagos: {e}")
    
# ────────────────── Generadores ──────────────────
def generar_matricula(session: Session, socio_id: int, actividad_id: int, fecha_matricula: date, estado: EstadoPago):
    inscripcion = session.get(InscripcionSocio, {'socio_id': socio_id, 'actividad_id': actividad_id})
    actividad = session.get(Actividad, actividad_id)
    if not inscripcion:
        print("Inscripción no encontrada.")
        return None
    if consultar_matricula(session, socio_id, actividad_id):
        print("Ya existe una matrícula para esta inscripción.")
        return None

    print(f"Generando matrícula para la inscripción socio:{socio_id} act:{actividad_id}, fecha: {fecha_matricula}, estado: {estado.value}")
    # Registrar el pago de matrícula
    matricula_id = registrar_pago(session, {
        'socio_id': socio_id,
        'actividad_id': actividad_id,
        'fecha': fecha_matricula,
        'importe': actividad.precio_matricula,
        'estado': estado
    }, tipo='matricula')
    
    return matricula_id

def consultar_matricula(session: Session, socio_id: int, actividad_id: int):
    return session.query(MatriculaPago).filter(
        MatriculaPago.socio_id == socio_id,
        MatriculaPago.actividad_id == actividad_id
    ).first()



def actualizar_estado_inscripciones(session: Session, actividad_id: int):
    actividad = session.query(Actividad).filter_by(id=actividad_id).first()
    if not actividad:
        print("Actividad no encontrada.")
        return False

    inscripciones = session.query(InscripcionSocio).filter_by(actividad_id=actividad.id).order_by(InscripcionSocio.fecha_inscripcion).all()

    for i, inscripcion in enumerate(inscripciones, start=1):
        if actividad.numero_maximo_alumnos is not None and i > actividad.numero_maximo_alumnos:
            inscripcion.estado = EstadoInscripcion.RESERVA
        else:
            inscripcion.estado = EstadoInscripcion.INSCRIT
        session.add(inscripcion)

    try:
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False