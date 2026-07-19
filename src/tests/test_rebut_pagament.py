from datetime import date, datetime

from ui.rebut_pagament import construir_rebut_html


def test_construir_rebut_inclou_dades_del_pagament():
    html = construir_rebut_html(
        {
            "id": 27,
            "fecha_pago": date(2026, 7, 13),
            "importe": 42.5,
            "estado": "PAGAT",
            "observaciones": "Pagat en efectiu",
        },
        {"id": 8, "nombre": "Maria", "apellido1": "Roca", "apellido2": "Soler"},
        {"nombre": "Taller de memòria"},
        fecha_hora_impresion=datetime(2026, 7, 13, 16, 42),
    )

    assert "13/07/2026" in html
    assert "16:42" in html
    assert "Maria Roca Soler" in html
    assert "Taller de memòria" in html
    assert "42,50 €" in html
    assert "Pagat en efectiu" in html
    assert "DONATIU" in html
    assert 'data:image/png;base64,' in html
    assert 'class="header-icon"' in html
    assert "#27" not in html
    assert "Estat:" not in html
    assert "PAGAT" not in html
    assert "rebut" not in html.lower()


def test_construir_rebut_escapa_text_html():
    html = construir_rebut_html(
        {"id": 1, "fecha_pago": date.today(), "importe": 10, "estado": "PAGAT"},
        {"id": 2, "nombre": "<Maria>", "apellido1": "& Roca"},
        {"nombre": "Ball <avançat>"},
    )

    assert "&lt;Maria&gt;" in html
    assert "&amp; Roca" in html
    assert "Ball &lt;avançat&gt;" in html
    assert "<Maria>" not in html
