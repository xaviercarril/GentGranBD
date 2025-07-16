
from controladores.personal import registrar_personal, modificar_personal, eliminar_personal, consultar_personal

def test_registrar_profesor(session):
    datos = {'nombre': 'Eva', 'apellido1': 'Torres', 'dniNie': 'P1234567X'}
    personalID = registrar_personal(session, datos, tipo='profesor')
    persona = consultar_personal(session, personalID)
    assert persona.nombre == 'Eva'
    assert persona.tipo == 'profesor'

def test_registrar_voluntario(session):
    datos = {'nombre': 'Marc', 'apellido1': 'Serra', 'dniNie': 'V7654321Y'}
    personalID = registrar_personal(session, datos, tipo='voluntario')
    persona = consultar_personal(session, personalID)
    assert persona.tipo == 'voluntario'

def test_modificar_personal(session):
    datos = {'nombre': 'Anna', 'apellido1': 'Casas', 'dniNie': 'P000111Z'}
    personalID = registrar_personal(session, datos, tipo='profesor')
    modificar_personal(session, personalID, {'nombre': 'Anna Maria'})
    persona = consultar_personal(session, personalID)
    assert persona.nombre == 'Anna Maria'

def test_eliminar_personal(session):
    datos = {'nombre': 'Pau', 'apellido1': 'Vila', 'dniNie': 'P999888W'}
    personalID = registrar_personal(session, datos, tipo='profesor')
    assert eliminar_personal(session, personalID) is True
