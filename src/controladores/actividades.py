
from sqlalchemy.orm import Session
from models import Actividad, Curso, Taller

def registrar_actividad(session: Session, datos: dict):
    tipo = datos.get('tipo')
    clase = {'curso': Curso, 'taller': Taller}.get(tipo, Actividad)
    if tipo == 'curso':
        actividad = Curso(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            duracion=datos.get('duracion'),
            lugar=datos.get('lugar'),
            observaciones=datos.get('observaciones'),
            personal_id=datos.get('personal_id'),
            trimestre=datos.get('trimestre'),
            curso=datos.get('curso'),
            precio_matricula=datos.get('precio_matricula', 0.0),
            dias_semana=datos.get('dias_semana')
        )
    elif tipo == 'taller':
        actividad = Taller(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            duracion=datos.get('duracion'),
            lugar=datos.get('lugar'),
            observaciones=datos.get('observaciones'),
            personal_id=datos.get('personal_id'),
            fecha=datos.get('fecha'),
            precio_matricula=datos.get('precio_matricula', 0.0),
            hora_inicio=datos.get('hora_inicio')
        )
    else:
        actividad = Actividad(
            nombre=datos['nombre'],
            numero_maximo_alumnos=datos.get('numero_maximo_alumnos'),
            duracion=datos.get('duracion'),
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
    actividad = session.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not actividad:
        return False
    session.delete(actividad)
    session.commit()
    return True

def consultar_actividad(session: Session, actividad_id: int):
    return session.query(Actividad).filter(Actividad.id == actividad_id).first()
