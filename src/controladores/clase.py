from datetime import date, datetime, timedelta, time
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, ValidationError
from controladores.dtos import clase_to_dto
from controladores.dtos_models import ClaseDTO, ClaseUpdateDTO
from database import SessionLocal
from models import Clase, Actividad, Trimestre, AsistenciaSocio


# ──────────────────────── CRUD ────────────────────────
def registrar_clase(data: dict) -> int:
    """Crea una nueva clase; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = ClaseDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")

    horaInicio = datetime.combine(dto.fecha, dto.horaInicio)
    horaFin = datetime.combine(dto.fecha, dto.horaFin)

    try:
        nueva_clase = Clase(
            actividadID=dto.actividadID,
            trimestreID=dto.trimestreID,
            fecha=dto.fecha,
            horaInicio=horaInicio,
            horaFin=horaFin,
            duracion=dto.duracion
        )
        with SessionLocal() as db:
            db.add(nueva_clase)
            db.commit()
            db.refresh(nueva_clase)
            return nueva_clase.id
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Error al registrar clase: {e.orig}")
    except Exception as e:
        db.rollback()
        raise ValueError(f"Error inesperado al registrar clase: {e}")
            


def modificar_clase(claseID: int, cambios: dict) -> None:
    """Modifica los datos de una clase existente con validación DTO."""
    try:
        dto = ClaseUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos al modificar clase: {e}")

    with SessionLocal() as db:
        clase = db.get(Clase, claseID)
        if not clase:
            raise ValueError("Clase inexistent")

        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(clase, k, v)
            if dto.horaInicio and dto.horaFin:
                clase.duracion = datetime.combine(date.min, dto.horaFin) - datetime.combine(date.min, dto.horaInicio)
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar clase: {e.orig}")

def consultar_clase(claseID: int) -> dict | None:
    """Consulta una clase por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            clase = db.get(Clase, claseID)
            if clase:
                return clase_to_dto(clase).model_dump()
            return None
    except Exception as e:
        raise ValueError(f"Error al consultar clase: {e}")

def eliminar_clase(claseID: int) -> None:
    """Elimina una clase por su ID."""
    try:
        with SessionLocal() as db:
            clase = db.get(Clase, claseID)
            if not clase:
                raise ValueError("Clase inexistent")
            db.delete(clase)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar clase: {e.orig}")


# ────────────────── Consultas ──────────────────
def listar_asistencia_por_Clase(claseID: int) -> list[dict]:
    """Consulta todas las asistencias a una clase específica."""
    try:
        with SessionLocal() as session:
            asistencias = session.query(AsistenciaSocio).filter_by(claseID=claseID).all()
            return [asistencia.model_dump() for asistencia in asistencias]
    except Exception as e:
        raise ValueError(f"Error al consultar asistencias: {e}")

def consultar_trimestre_Clase(claseID: int) -> dict | None:
    """Consulta un trimestre por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            trimestre = db.get(Trimestre, claseID)
            if not trimestre:
                return None
            return trimestre.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar trimestre: {e}")

def consultar_actividad_Clase(claseID: int) -> dict | None:
    """Consulta una actividad por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            actividad = db.get(Actividad, claseID)
            if not actividad:
                return None
            return actividad.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")


# ────────────────── Generadores ──────────────────
def generar_clases_semana(
    actividadID: int,
    trimestreID: int,
    fechaInicio: date,
    fechaFin: date,
    horaInicio: time,
    horaFin: time,
    dias_semana: list[int],
    cada_n_semanas: int = 1
) -> list[int]:
    """Genera clases de una actividad en días específicos de la semana dentro de un rango de fechas."""
    try:
        with SessionLocal() as session:
            actividad = session.get(Actividad, actividadID)
            if not actividad:
                raise ValueError("Actividad no encontrada.")

            clases_creadas = []
            fecha = fechaInicio

            while fecha <= fechaFin:
                for dia in dias_semana:
                    dia_fecha = fecha + timedelta(days=(dia - fecha.weekday()) % 7)
                    if fechaInicio <= dia_fecha <= fechaFin:
                        existe = session.query(Clase).filter_by(actividadID=actividad.id, fecha=dia_fecha).first()
                        if not existe:
                            delta = datetime.combine(dia_fecha, horaFin) - datetime.combine(dia_fecha, horaInicio)
                            duracion = int(delta.total_seconds() // 60)
                            nueva_clase_id = registrar_clase({
                                "actividadID": actividadID,
                                "trimestreID": trimestreID,
                                "fecha": dia_fecha,
                                "horaInicio": horaInicio,
                                "horaFin": horaFin,
                                "duracion": duracion
                            })
                            clases_creadas.append(nueva_clase_id)
                fecha += timedelta(weeks=cada_n_semanas)

            return [id for id in clases_creadas]
    except Exception as e:
        raise ValueError(f"Error al generar clases: {e}")
