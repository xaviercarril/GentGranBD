from datetime import date

from exportador.pdf_carnet import CARD_H, CARD_W
from exportador.pdf_ficha_carnet import (
    CUT_SIDES,
    PAGE_H,
    PAGE_W,
    SHEET_MARGIN,
    generar_hoja_ficha_carnet_socio,
)
from exportador.pdf_ficha_socio import FICHA_H, FICHA_W
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


def test_ficha_y_carnet_quedan_separados_de_los_bordes():
    ficha_x = SHEET_MARGIN
    ficha_y = PAGE_H - SHEET_MARGIN - FICHA_H
    carnet_x = PAGE_W - SHEET_MARGIN - CARD_W
    carnet_y = SHEET_MARGIN

    tolerance = 1e-9
    for x, y, width, height in (
        (ficha_x, ficha_y, FICHA_W, FICHA_H),
        (carnet_x, carnet_y, CARD_W, CARD_H),
    ):
        assert x >= SHEET_MARGIN - tolerance
        assert y >= SHEET_MARGIN - tolerance
        assert PAGE_W - (x + width) >= SHEET_MARGIN - tolerance
        assert PAGE_H - (y + height) >= SHEET_MARGIN - tolerance


def test_guias_de_corte_marcan_todos_los_bordes():
    assert set(CUT_SIDES) == {"left", "right", "bottom", "top"}
