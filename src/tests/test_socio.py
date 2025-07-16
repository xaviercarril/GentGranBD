
from controladores.socios import registrar_socio, modificar_socio, eliminar_socio, consultar_socio
from datetime import date

def test_cu01_registrar_socio(session):
    datos = {
        'dniNie': '12345678X',
        'nombre': 'Pere',
        'fechaAlta': date.today()
    }
    socioID = registrar_socio(session, datos)
    socio = consultar_socio(session, socioID)
    assert socio is not None
    assert socio.nombre == 'Pere'

def test_cu02_modificar_socio(session):
    datos = {
        'dniNie': '1111A',
        'nombre': 'Maria',
        'fechaAlta': date.today()
    }
    socioID = registrar_socio(session, datos)
    modificar_socio(session, socioID, {'nombre': 'Maria Teresa'})
    socio = consultar_socio(session, socioID)
    assert socio.nombre == 'Maria Teresa'

def test_cu03_eliminar_socio(session):
    datos = {
        'dniNie': '2222B',
        'nombre': 'Joan',
        'fechaAlta': date.today()
    }
    socioID = registrar_socio(session, datos)
    resultado = eliminar_socio(session, socioID)
    assert resultado is True
    assert consultar_socio(session, socioID) is None

def test_cu04_consultar_socio(session):
    datos = {
        'dniNie': '3333C',
        'nombre': 'Laia',
        'fechaAlta': date.today()
    }
    socioID = registrar_socio(session, datos)
    socio = consultar_socio(session, socioID)
    assert socio.dniNie == '3333C'
    assert socio.nombre == 'Laia'
