import os
from exportador.pdf_carnet import generar_carnet_socio
from controladores.socios import registrar_socio, adjuntar_foto_socio
from datetime import date

def test_generar_carnet(tmp_path, session):
    socioID = registrar_socio(session, {
        "dniNie": "XYZ001",
        "nombre": "Maria",
        "apellido1": "García",
        "apellido2": "López",
        "fechaAlta": date.today()
    })
    adjuntar_foto_socio(session, socioID, "./tests/foto_socio3.jpg")
    outfile = "./carnet.pdf"
    generar_carnet_socio(session, socioID, str(outfile), "./extra/logo.png")
    assert os.stat(outfile).st_size > 0