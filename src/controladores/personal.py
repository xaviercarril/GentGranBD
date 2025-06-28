
from sqlalchemy.orm import Session
from models import Personal, Profesor, Voluntario

def registrar_personal(session: Session, datos: dict, tipo: str):
    clase = Profesor if tipo == 'profesor' else Voluntario
    persona = clase(
        nombre=datos['nombre'],
        apellido1=datos.get('apellido1'),
        apellido2=datos.get('apellido2'),
        dni_nie=datos['dni_nie']
    )
    session.add(persona)
    session.commit()
    return persona.id

def modificar_personal(session: Session, personal_id: int, nuevos_datos: dict):
    persona = session.query(Personal).filter(Personal.id == personal_id).first()
    if not persona:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(persona, clave, valor)
    session.commit()
    return True

def eliminar_personal(session: Session, personal_id: int):
    persona = session.query(Personal).filter(Personal.id == personal_id).first()
    if not persona:
        return False
    session.delete(persona)
    session.commit()
    return True

def consultar_personal(session: Session, personal_id: int):
    return session.query(Personal).filter(Personal.id == personal_id).first()
