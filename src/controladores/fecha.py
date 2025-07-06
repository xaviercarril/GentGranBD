from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Fecha, Actividad

def generar_fechas(
    session: Session,
    actividad_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    dias_semana: list[int],
    cada_n_semanas: int = 1,
    observaciones: str = None
):
    actividad = session.get(Actividad,actividad_id)
    if not actividad:
        raise ValueError("Actividad no encontrada.")

    fecha = fecha_inicio
    while fecha <= fecha_fin:
        for dia in dias_semana:
            dia_fecha = fecha + timedelta(days=(dia - fecha.weekday()) % 7)
            if fecha_inicio <= dia_fecha <= fecha_fin:
                existe = session.query(Fecha).filter_by(actividad_id=actividad.id, fecha=dia_fecha).first()
                if not existe:
                    nueva_fecha = Fecha(
                        actividad_id=actividad.id,
                        fecha=dia_fecha,
                        observaciones=observaciones
                    )
                    session.add(nueva_fecha)
        fecha += timedelta(weeks=cada_n_semanas)
    session.commit()

def generar_fechas_custom(session: Session, actividad_id: int, lista_fechas: list[date], observaciones: str = None):
    actividad = session.get(Actividad,actividad_id)
    if not actividad:
        raise ValueError("Actividad no encontrada.")

    for fecha in lista_fechas:
        nueva_fecha = Fecha(
            actividad_id=actividad.id,
            fecha=fecha,
            observaciones=observaciones
        )
        session.add(nueva_fecha)
    session.commit()

def agregar_fecha(session: Session, actividad_id: int, fecha: date, observaciones: str = None):
    nueva_fecha = Fecha(
        actividad_id=actividad_id,
        fecha=fecha,
        observaciones=observaciones
    )
    session.add(nueva_fecha)
    session.commit()
    return nueva_fecha.id

def eliminar_fecha(session: Session, fecha_id: int):
    fecha_obj = session.query(Fecha).filter(Fecha.id == fecha_id).first()
    if not fecha_obj:
        print("Fecha no encontrada.")
        return False
    session.delete(fecha_obj)
    session.commit()
    return True

def consultar_fechas(session: Session, actividad_id: int):
    return session.query(Fecha).filter_by(actividad_id=actividad_id).order_by(Fecha.fecha).all()

def consultar_fecha(session: Session, fecha_id: int):
    return session.query(Fecha).filter(Fecha.id == fecha_id).first()