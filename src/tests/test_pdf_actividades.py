from exportador.pdf_actividades import generar_pdf_actividades_curso


def test_generar_pdf_actividades_curso(tmp_path):
    output = tmp_path / "activitats.pdf"
    generar_pdf_actividades_curso(
        "2025-2026",
        [
            {
                "nombre": "Anglès",
                "personal_nombre": "Ricardo Vidal",
                "precio_matricula": "20.00 €",
                "inscritos": 12,
                "numMaxAlumnos": 18,
                "descripcion": "Dimecres tarda",
            }
        ],
        str(output),
    )

    assert output.stat().st_size > 0
