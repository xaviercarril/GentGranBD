
from controladores.socios import registrar_socio, consultar_socio
from datetime import date

def test_cu05_ver_ficha_socio(session):
    datos = {
        'dniNie': '4444D',
        'nombre': 'Carlos',
        'apellido1': 'Roca',
        'apellido2': 'Blanc',
        'direccion': 'Carrer de la Pau, 10',
        'telefonoFijo': '931234567',
        'telefonoMovil': '600123456',
        'email': 'carlos@example.com',
        'grupoDifusion': 'Noticies',
        'fechaAlta': date(2024, 9, 1),
        'observaciones': 'Sense incidències',
        'foto': None
    }
    socioID = registrar_socio(session, datos)
    socio = consultar_socio(session, socioID)

    assert socio is not None
    assert socio.nombre == 'Carlos'
    assert socio.apellido1 == 'Roca'
    assert socio.email == 'carlos@example.com'
    assert socio.observaciones == 'Sense incidències'
