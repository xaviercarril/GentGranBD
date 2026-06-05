import os
from exportador.pdf_carnet import CARD_W, MARGE, _story, _styles, generar_carnet_socio
from datetime import date
from models import Socio

def test_generar_carnet(tmp_path, session):
    with open("./src/tests/foto_socio3.jpg", "rb") as fh:
        foto = fh.read()
    socio = Socio(
        dniNie="XYZ001",
        nombre="Maria",
        apellido1="García",
        apellido2="López",
        fechaAlta=date.today(),
        foto=foto,
    )
    session.add(socio)
    session.commit()

    outfile = tmp_path / "carnet.pdf"
    generar_carnet_socio(session, socio.id, str(outfile), "./extra/logo.png")
    assert os.stat(outfile).st_size > 0


def test_carnet_sin_foto_no_reserva_columna_de_foto():
    socio = Socio(
        id=7,
        dniNie="XYZ002",
        nombre="Maria",
        apellido1="Garcia",
        apellido2="Lopez",
        fechaAlta=date.today(),
    )

    story = _story(socio, _styles())
    table = story[1]

    assert len(table._colWidths) == 1
    assert table._colWidths[0] == CARD_W - 2 * MARGE
