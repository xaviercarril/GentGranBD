
from sqlalchemy.orm import Session
from models import Voluntario

def registrar_voluntario(session: Session, datos: dict):
    voluntario = Voluntario(
        dni_nie=datos['dni_nie'],
        nombre=datos['nombre'],
        apellido1=datos.get('apellido1'),
        apellido2=datos.get('apellido2')
    )
    session.add(voluntario)
    session.commit()
    return voluntario.id

def modificar_voluntario(session: Session, voluntario_id: int, nuevos_datos: dict):
    voluntario = session.query(Voluntario).filter(Voluntario.id == voluntario_id).first()
    if not voluntario:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(voluntario, clave, valor)
    session.commit()
    return True

def eliminar_voluntario(session: Session, voluntario_id: int):
    voluntario = session.query(Voluntario).filter(Voluntario.id == voluntario_id).first()
    if not voluntario:
        return False
    session.delete(voluntario)
    session.commit()
    return True

def consultar_voluntario(session: Session, voluntario_id: int):
    return session.query(Voluntario).filter(Voluntario.id == voluntario_id).first()
