import os
from exportador.pdf_carnet import FOTO_H, FOTO_W, _story, _styles, generar_carnet_socio
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


def test_carnet_sin_foto_reserva_el_hueco_de_la_foto():
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

    assert len(table._colWidths) == 2
    foto_placeholder = table._cellvalues[0][0]
    assert foto_placeholder.width == FOTO_W
    assert foto_placeholder.height == FOTO_H
