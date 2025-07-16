from dataclasses import dataclass
from datetime import date, timedelta
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from database import SessionLocal
from models import AsistenciaSocio, Clase, Actividad, Trimestre

@dataclass(slots=True)
class ClaseDTO(BaseModel):
    id: int | None = None
    actividad_id: int
    trimestre_id: int
    fecha: date | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    duracion: timedelta | None = None
    observaciones: str | None = None

class ClaseUpdateDTO(BaseModel):
    fecha: date | None = None
    hora_inicio: str | None = None
    hora_fin: str | None = None
    duracion: timedelta | None = None
    observaciones: str | None = None
    trimestre_id: int | None = None

def _to_dto(clase: Clase) -> ClaseDTO:
    return ClaseDTO(
        id=clase.id,
        actividad_id=clase.actividad_id,
        trimestre_id=clase.trimestre_id,
        fecha=clase.fecha,
        hora_inicio=clase.hora_inicio,
        hora_fin=clase.hora_fin,
        duracion=clase.duracion,
        observaciones=clase.observaciones
    )
    
# ──────────────────────── CRUD ────────────────────────
def registrar_clase(data: dict) -> int:
    """Crea una nueva clase; recibe dict, valida con DTO y devuelve ID."""
    try:
        dto = ClaseDTO(**data)
    except ValidationError as e:
        raise ValueError(f"Datos de entrada inválidos: {e}")
    
    if dto.hora_inicio and dto.hora_fin:
        hora_inicio = timedelta(hours=int(dto.hora_inicio.split(':')[0]), minutes=int(dto.hora_inicio.split(':')[1]))
        hora_fin = timedelta(hours=int(dto.hora_fin.split(':')[0]), minutes=int(dto.hora_fin.split(':')[1]))
        duracion = hora_fin - hora_inicio
    else:
        duracion = None

    nueva_clase = Clase(
        actividad_id=dto.actividad_id,
        trimestre_id=dto.trimestre_id,
        fecha=dto.fecha,
        hora_inicio=dto.hora_inicio,
        hora_fin=dto.hora_fin,
        duracion=duracion,
        observaciones=dto.observaciones
    )
    with SessionLocal() as db:
        db.add(nueva_clase)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al registrar clase: {e.orig}")
        except Exception as e:
            db.rollback()
            raise ValueError(f"Error inesperado al registrar clase: {e}")
        db.refresh(nueva_clase)
        return nueva_clase.id

def modificar_clase(clase_id: int, cambios: dict) -> None:
    """Modifica los datos de una clase existente con validación DTO."""
    try:
        dto = ClaseUpdateDTO(**cambios)
    except ValidationError as e:
        raise ValueError(f"Datos inválidos al modificar clase: {e}")

    with SessionLocal() as db:
        clase = db.get(Clase, clase_id)
        if not clase:
            raise ValueError("Clase inexistent")
        
        try:
            for k, v in dto.model_dump(exclude_unset=True).items():
                setattr(clase, k, v)
            if dto.hora_inicio and dto.hora_fin:
                hora_inicio = timedelta(hours=int(dto.hora_inicio.split(':')[0]), minutes=int(dto.hora_inicio.split(':')[1]))
                hora_fin = timedelta(hours=int(dto.hora_fin.split(':')[0]), minutes=int(dto.hora_fin.split(':')[1]))
                clase.duracion = hora_fin - hora_inicio
            db.commit()
        except AttributeError as e:
            db.rollback()
            raise ValueError(f"Campo desconocido: {e}")
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error al modificar clase: {e.orig}")

def consultar_clase(clase_id: int) -> dict | None:
    """Consulta una clase por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            clase = db.get(Clase, clase_id)
            if clase:
                return _to_dto(clase).model_dump()
            return None
    except Exception as e:
        raise ValueError(f"Error al consultar clase: {e}")

def eliminar_clase(clase_id: int) -> None:
    """Elimina una clase por su ID."""
    try:
        with SessionLocal() as db:
            clase = db.get(Clase, clase_id)
            if not clase:
                raise ValueError("Clase inexistent")
            db.delete(clase)
            db.commit()
    except IntegrityError as e:
        raise ValueError(f"Error al eliminar clase: {e.orig}")


    
# ────────────────── Consultas ──────────────────
def listar_asistencia_por_Clase(clase_id: int) -> list[dict]:
    """Consulta todas las asistencias a una clase específica."""
    try:
        with SessionLocal() as session:
            asistencias = session.query(AsistenciaSocio).filter_by(clase_id=clase_id).all()
            return [asistencia.model_dump() for asistencia in asistencias]
    except Exception as e:
        raise ValueError(f"Error al consultar asistencias: {e}")

def consultar_trimestre_Clase(clase_id: int) -> dict | None:
    """Consulta un trimestre por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            trimestre = db.get(Trimestre, clase_id)
            if not trimestre:
                return None
            return trimestre.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar trimestre: {e}")
    
def consultar_actividad_Clase(clase_id: int) -> dict | None:
    """Consulta una actividad por su ID y devuelve sus datos como dict."""
    try:
        with SessionLocal() as db:
            actividad = db.get(Actividad, clase_id)
            if not actividad:
                return None
            return actividad.model_dump()
    except Exception as e:
        raise ValueError(f"Error al consultar actividad: {e}")
    
# ────────────────── Generadores ──────────────────
def generar_clases_semana(
    session: Session,
    actividad_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    dias_semana: list[int],
    cada_n_semanas: int = 1,
    observaciones: str = None
) -> list[int]:
    """
    Genera clases de una actividad:
    - Si dias_semana se define: crea clases cíclicas según días seleccionados.
    - Si fechas_personalizadas se define: crea solo esas fechas.
    """
    actividad = session.get(Actividad, actividad_id)
    if not actividad:
        raise ValueError("Actividad no encontrada.")

    clases_creadas = []

    fecha = fecha_inicio
    while fecha <= fecha_fin:
        for dia in dias_semana:
            dia_fecha = fecha + timedelta(days=(dia - fecha.weekday()) % 7)
            if fecha_inicio <= dia_fecha <= fecha_fin:
                existe = session.query(Clase).filter_by(actividad_id=actividad.id, fecha=dia_fecha).first()
                if not existe:
                    try:
                        nueva_clase = registrar_clase(
                            {
                                "actividad_id": actividad.id,
                                "fecha": dia_fecha,
                                "observaciones": observaciones
                            }
                        )
                        session.add(nueva_clase)
                        clases_creadas.append(nueva_clase)
                    except ValueError as e:
                        print(f"Error al registrar clase: {e}")
        fecha += timedelta(weeks=cada_n_semanas)

    session.commit()
    return [clase.id for clase in clases_creadas]

def generar_clases_custom(
    session: Session,
    actividad_id: int,
    fechas_personalizadas: list[date] | None = None,
    observaciones: str = None
) -> list[int] | None:
    """
    Genera clases de una actividad:
    - Si dias_semana se define: crea clases cíclicas según días seleccionados.
    - Si fechas_personalizadas se define: crea solo esas fechas.
    """
    actividad = session.get(Actividad, actividad_id)
    if not actividad:
        raise ValueError("Actividad no encontrada.")

    clases_creadas = []

    for fecha in fechas_personalizadas:
        existe = session.query(Clase).filter_by(actividad_id=actividad.id, fecha=fecha).first()
        if not existe:
            try:
                nueva_clase = registrar_clase(
                    {
                        "actividad_id": actividad.id,
                        "fecha": fecha,
                        "observaciones": observaciones
                    }
                )
                session.add(nueva_clase)
                clases_creadas.append(nueva_clase)
            except ValueError as e:
                print(f"Error al registrar clase: {e}")

    session.commit()
    return [clase.id for clase in clases_creadas]

