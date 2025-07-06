from datetime import date, timedelta
from sqlalchemy.orm import Session
from models import Actividad, Curso, Fecha, Taller, Trimestre, TrimestreEnum
from enum import Enum

def registrar_actividad(session: Session, datos: dict):
    tipo = datos.get('tipo')
    if tipo == 'curso':
        actividad = Curso(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            lugar=datos.get('lugar'),
            observaciones=datos.get('observaciones'),
            personal_id=datos.get('personal_id'),
            curso_academico=datos.get('curso_academico'),
            precio_matricula=datos.get('precio_matricula', 0.0),
            descripcion_fecha=datos.get('descripcion_fecha')
        )
    elif tipo == 'taller':
        actividad = Taller(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            lugar=datos.get('lugar'),
            observaciones=datos.get('observaciones'),
            personal_id=datos.get('personal_id'),
            precio_matricula=datos.get('precio_matricula', 0.0),
        )
    else:
        actividad = Actividad(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            lugar=datos.get('lugar'),
            observaciones=datos.get('observaciones'),
            precio_matricula=datos.get('precio_matricula', 0.0),
            personal_id=datos.get('personal_id')
        )
    session.add(actividad)
    session.commit()
    return actividad.id

def modificar_actividad(session: Session, actividad_id: int, nuevos_datos: dict):
    actividad = session.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(actividad, clave, valor)
    session.commit()
    return True

def eliminar_actividad(session: Session, actividad_id: int):
    try:
        actividad = session.query(Actividad).filter(Actividad.id == actividad_id).first()
        if not actividad:
            return False
        session.delete(actividad)
        session.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar actividad: {e}")
        return False

def consultar_actividad(session: Session, actividad_id: int):
    return session.query(Actividad).filter(Actividad.id == actividad_id).first()

def crear_trimestre(session: Session, curso_id: int, nombre: TrimestreEnum, fecha_inicio: date, fecha_fin: date):
    curso = session.get(Curso,curso_id)
    if not curso:
        raise ValueError("Curso no encontrado.")
    trimestre = Trimestre(
        nombre=nombre,
        curso_id=curso_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        curso=curso
    )
    session.add(trimestre)
    session.commit()
    return trimestre.id

def consultar_trimestres(session: Session, curso_id: int, TrimestreEnum: TrimestreEnum):
    tri = session.query(Trimestre).filter(
        Trimestre.curso_id == curso_id,
        Trimestre.nombre == TrimestreEnum
    ).first()

    return tri if tri else None

def consultar_curso_academico(session: Session, curso_id: int):
    curso = session.query(Curso).filter(Curso.id == curso_id).first()
    if not curso:
        return None
    return curso.curso_academico