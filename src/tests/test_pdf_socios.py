from datetime import date

from exportador.pdf_socios import generar_pdf_socios_tabla


def test_generar_pdf_socios_tabla(tmp_path):
    output = tmp_path / "socis.pdf"
    generar_pdf_socios_tabla(
        [
            {
                "id": 1,
                "apellido1": "Garcia",
                "apellido2": "Martinez",
                "nombre": "Maria",
                "dniNie": "12345678Z",
                "telefonoMovil": "600111222",
                "telefonoFijo": "936001122",
                "direccion": "Carrer Major 1",
                "fechaAlta": date(2025, 9, 1),
                "fechaNacimiento": date(1955, 5, 15),
                "grupoDifusion": "WhatsApp",
                "email": "maria@example.com",
            }
        ],
        str(output),
    )

    assert output.stat().st_size > 0
