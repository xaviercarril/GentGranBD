from openpyxl import load_workbook

from exportador.excel_actividades import generar_excel_actividades_curso


def test_generar_excel_actividades_curso_crea_listado_formateado(tmp_path):
    output = tmp_path / "cursos.xlsx"
    generar_excel_actividades_curso(
        "2025-2026",
        [
            {
                "nombre": "Taller de memòria i estimulació cognitiva",
                "personal_nombre": "Montserrat García Fernández",
                "precio_matricula": "120.50 €",
                "inscritos": 28,
                "numMaxAlumnos": 30,
                "descripcion": "Descripció llarga que ha de quedar visible dins de la cel·la.",
            }
        ],
        str(output),
    )

    workbook = load_workbook(output)
    worksheet = workbook["Cursos"]

    assert worksheet["A1"].value == "LLISTAT DE CURSOS - 2025-2026"
    assert worksheet["A3"].value == "Activitat"
    assert worksheet["C4"].value == 120.5
    assert worksheet["D4"].value == 28
    assert worksheet["E4"].value == 30
    assert worksheet["F4"].alignment.wrap_text is True
    assert worksheet["F4"].alignment.indent == 1
    assert worksheet.freeze_panes == "A4"
    assert worksheet.auto_filter.ref == "A3:F4"
    assert worksheet.page_setup.orientation == "landscape"
    assert worksheet.column_dimensions["F"].width >= 50
