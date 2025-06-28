
from controladores.socios import registrar_socio, modificar_socio, eliminar_socio, consultar_socio
from datetime import date

def test_cu01_registrar_socio(session):
    datos = {
        'dni_nie': '12345678X',
        'nombre': 'Pere',
        'fecha_alta': date.today()
    }
    socio_id = registrar_socio(session, datos)
    socio = consultar_socio(session, socio_id)
    assert socio is not None
    assert socio.nombre == 'Pere'

def test_cu02_modificar_socio(session):
    datos = {
        'dni_nie': '1111A',
        'nombre': 'Maria',
        'fecha_alta': date.today()
    }
    socio_id = registrar_socio(session, datos)
    modificar_socio(session, socio_id, {'nombre': 'Maria Teresa'})
    socio = consultar_socio(session, socio_id)
    assert socio.nombre == 'Maria Teresa'

def test_cu03_eliminar_socio(session):
    datos = {
        'dni_nie': '2222B',
        'nombre': 'Joan',
        'fecha_alta': date.today()
    }
    socio_id = registrar_socio(session, datos)
    resultado = eliminar_socio(session, socio_id)
    assert resultado is True
    assert consultar_socio(session, socio_id) is None

def test_cu04_consultar_socio(session):
    datos = {
        'dni_nie': '3333C',
        'nombre': 'Laia',
        'fecha_alta': date.today()
    }
    socio_id = registrar_socio(session, datos)
    socio = consultar_socio(session, socio_id)
    assert socio.dni_nie == '3333C'
    assert socio.nombre == 'Laia'
