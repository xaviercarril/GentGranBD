
from sqlalchemy.orm import Session
from models import Socio
from datetime import date

def registrar_socio(session: Session, datos: dict):
    socio = Socio(
        dni_nie=datos.get('dni_nie'),
        nombre=datos.get('nombre'),
        apellido1=datos.get('apellido1'),
        apellido2=datos.get('apellido2'),
        direccion=datos.get('direccion'),
        telefonoFijo=datos.get('telefonoFijo'),
        telefonoMovil=datos.get('telefonoMovil'),
        email=datos.get('email'),
        grupoDifusion=datos.get('grupoDifusion'),
        fechaAlta=datos.get('fechaAlta', date.today()),
        fechaBaja=datos.get('fechaBaja'),
        observaciones=datos.get('observaciones'),
        foto=datos.get('foto')
    )
    session.add(socio)
    session.commit()
    return socio.id

def modificar_socio(session: Session, socio_id: int, nuevos_datos: dict):
    socio = session.query(Socio).filter(Socio.id == socio_id).first()
    if not socio:
        return False
    for clave, valor in nuevos_datos.items():
        setattr(socio, clave, valor)
    session.commit()
    return True

def eliminar_socio(session: Session, socio_id: int):
    socio = session.query(Socio).filter(Socio.id == socio_id).first()
    if not socio:
        return False
    session.delete(socio)
    session.commit()
    return True

def consultar_socio(session: Session, socio_id: int):
    return session.query(Socio).filter(Socio.id == socio_id).first()

def adjuntar_foto_socio(session: Session, socio_id: int, filename: str):
    with open(filename, 'rb') as file:
        foto = file.read()
    if not foto:
        return False
    socio = session.query(Socio).filter(Socio.id == socio_id).first()
    if not socio:
        return False
    socio.foto = foto
    session.commit()
    return True
