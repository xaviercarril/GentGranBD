import os
from exportador.pdf_carnet import generar_carnet_socio
from controladores.socios import registrar_socio, adjuntar_foto_socio
from datetime import date

def test_generar_carnet(tmp_path, session):
    socio_id = registrar_socio(session, {
        "dni_nie": "XYZ001",
        "nombre": "Maria",
        "apellido1": "García",
        "apellido2": "López",
        "fecha_alta": date.today()
    })
    adjuntar_foto_socio(session, socio_id, "./src/tests/foto_socio3.jpg")
    outfile = "./carnet.pdf"
    generar_carnet_socio(session, socio_id, str(outfile), "./extra/logo.png")
    assert os.stat(outfile).st_size > 0