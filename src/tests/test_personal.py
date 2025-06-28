
from controladores.personal import registrar_personal, modificar_personal, eliminar_personal, consultar_personal

def test_registrar_profesor(session):
    datos = {'nombre': 'Eva', 'apellido1': 'Torres', 'dni_nie': 'P1234567X'}
    personal_id = registrar_personal(session, datos, tipo='profesor')
    persona = consultar_personal(session, personal_id)
    assert persona.nombre == 'Eva'
    assert persona.tipo == 'profesor'

def test_registrar_voluntario(session):
    datos = {'nombre': 'Marc', 'apellido1': 'Serra', 'dni_nie': 'V7654321Y'}
    personal_id = registrar_personal(session, datos, tipo='voluntario')
    persona = consultar_personal(session, personal_id)
    assert persona.tipo == 'voluntario'

def test_modificar_personal(session):
    datos = {'nombre': 'Anna', 'apellido1': 'Casas', 'dni_nie': 'P000111Z'}
    personal_id = registrar_personal(session, datos, tipo='profesor')
    modificar_personal(session, personal_id, {'nombre': 'Anna Maria'})
    persona = consultar_personal(session, personal_id)
    assert persona.nombre == 'Anna Maria'

def test_eliminar_personal(session):
    datos = {'nombre': 'Pau', 'apellido1': 'Vila', 'dni_nie': 'P999888W'}
    personal_id = registrar_personal(session, datos, tipo='profesor')
    assert eliminar_personal(session, personal_id) is True
