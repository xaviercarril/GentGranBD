
from controladores.voluntarios import (
    registrar_voluntario,
    modificar_voluntario,
    eliminar_voluntario,
    consultar_voluntario
)

def test_cu11_registrar_voluntario(session):
    datos = {
        'dniNie': 'V1234567X',
        'nombre': 'Laura',
        'apellido1': 'Prats'
    }
    voluntario_id = registrar_voluntario(session, datos)
    voluntario = consultar_voluntario(session, voluntario_id)
    assert voluntario is not None
    assert voluntario.nombre == 'Laura'

def test_cu12_modificar_voluntario(session):
    datos = {
        'dniNie': 'V7654321Y',
        'nombre': 'Oriol',
        'apellido1': 'Mir'
    }
    voluntario_id = registrar_voluntario(session, datos)
    modificar_voluntario(session, voluntario_id, {'nombre': 'Oriol Xavier'})
    voluntario = consultar_voluntario(session, voluntario_id)
    assert voluntario.nombre == 'Oriol Xavier'

def test_cu13_eliminar_voluntario(session):
    datos = {
        'dniNie': 'V000111Z',
        'nombre': 'Marta',
        'apellido1': 'Soler'
    }
    voluntario_id = registrar_voluntario(session, datos)
    resultado = eliminar_voluntario(session, voluntario_id)
    assert resultado is True
    assert consultar_voluntario(session, voluntario_id) is None

def test_cu14_consultar_voluntario(session):
    datos = {
        'dniNie': 'V999888W',
        'nombre': 'Albert',
        'apellido1': 'Costa'
    }
    voluntario_id = registrar_voluntario(session, datos)
    voluntario = consultar_voluntario(session, voluntario_id)
    assert voluntario.dniNie == 'V999888W'
    assert voluntario.nombre == 'Albert'
