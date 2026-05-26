from datetime import date

from exportador.pdf_ficha_carnet import generar_hoja_ficha_carnet_socio
from models import Socio


def test_generar_hoja_ficha_carnet(tmp_path, session):
    socio = Socio(
        dniNie="12345678Z",
        nombre="Maria",
        apellido1="Garcia",
        apellido2="Lopez",
        direccion="Carrer Major, 1",
        telefonoMovil="600123456",
        email="maria@example.com",
        fechaAlta=date.today(),
        observaciones="Sense incidencies",
    )
    session.add(socio)
    session.commit()

    outfile = tmp_path / "fitxa_carnet.pdf"
    generar_hoja_ficha_carnet_socio(session, socio.id, str(outfile))

    assert outfile.stat().st_size > 0
