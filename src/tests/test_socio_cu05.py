
from controladores.socios import registrar_socio, consultar_socio
from datetime import date

def test_cu05_ver_ficha_socio(session):
    datos = {
        'dni_nie': '4444D',
        'nombre': 'Carlos',
        'apellido1': 'Roca',
        'apellido2': 'Blanc',
        'direccion': 'Carrer de la Pau, 10',
        'telefono_fijo': '931234567',
        'telefono_movil': '600123456',
        'email': 'carlos@example.com',
        'grupo_difusion': 'Noticies',
        'fecha_alta': date(2024, 9, 1),
        'observaciones': 'Sense incidències',
        'foto': None
    }
    socio_id = registrar_socio(session, datos)
    socio = consultar_socio(session, socio_id)

    assert socio is not None
    assert socio.nombre == 'Carlos'
    assert socio.apellido1 == 'Roca'
    assert socio.email == 'carlos@example.com'
    assert socio.observaciones == 'Sense incidències'
