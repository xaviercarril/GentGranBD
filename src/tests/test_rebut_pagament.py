import ctypes
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from ui.rebut_pagament import (
    MIDA_BLOC_USB,
    _enviar_raw_windows,
    _enviar_usb_pos80,
    _es_cua_pos80_zywell,
    _imagen_a_escpos_segmentado,
    construir_rebut_html,
)


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
        {
            "nombre": "Taller de memòria",
            "descripcion": "Exercicis d'atenció i record",
        },
        fecha_hora_impresion=datetime(2026, 7, 13, 16, 42),
    )

    assert "13/07/2026" in html
    assert "16:42" in html
    assert "Maria Roca Soler" in html
    assert "Taller de memòria" in html
    assert "Descripció:" in html
    assert "Exercicis d&#x27;atenció i record" in html
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
    assert "Descripció:" not in html
    assert "<Maria>" not in html


def test_detecta_la_cua_pos80_amb_driver_zywell():
    assert _es_cua_pos80_zywell("PrinterCMD_ESCPO_POS80_Printer_USB")
    assert _es_cua_pos80_zywell("POS-8360")
    assert _es_cua_pos80_zywell("POS-80 Printer")
    assert not _es_cua_pos80_zywell("POS Label-80")
    assert not _es_cua_pos80_zywell("EPSON_ET_2850_Series")


def test_codifica_escpos_en_blocs_curts_sense_pdf_ni_avance_inicial():
    imagen = QImage(8, 25, QImage.Format_Grayscale8)
    imagen.fill(Qt.white)
    imagen.setPixelColor(0, 0, Qt.black)
    imagen.setPixelColor(7, 24, Qt.black)

    datos = _imagen_a_escpos_segmentado(imagen)

    assert datos.startswith(b"\x1b@\x1b$\x01\x00\x1bJ\x0c\x1dv0\x00\x01\x00\x18\x00\x80")
    assert datos.count(b"\x1dv0") == 2
    assert b"%PDF" not in datos
    assert datos.count(b"\x1bJ") == 1
    assert datos.endswith(b"\x1bd\x04\x1dV\x01")


class _LibUSBFalsa:
    def __init__(self):
        self.bloques = []
        self.liberada = False
        self.cerrada = False
        self.finalizada = False

    def libusb_init(self, contexto):
        contexto._obj.value = 1
        return 0

    def libusb_open_device_with_vid_pid(self, contexto, vid, pid):
        assert contexto.value == 1
        assert (vid, pid) == (0x0416, 0x5011)
        return 2

    def libusb_claim_interface(self, dispositivo, interfaz):
        assert (dispositivo, interfaz) == (2, 0)
        return 0

    def libusb_bulk_transfer(
        self, dispositivo, endpoint, buffer, longitud, transferidos, timeout
    ):
        assert dispositivo == 2
        assert endpoint == 0x01
        assert timeout == 5000
        self.bloques.append(bytes(buffer[:longitud]))
        transferidos._obj.value = longitud
        return 0

    def libusb_release_interface(self, dispositivo, interfaz):
        self.liberada = True
        return 0

    def libusb_close(self, dispositivo):
        self.cerrada = True

    def libusb_exit(self, contexto):
        self.finalizada = True


def test_envia_escpos_directamente_por_usb_en_bloques():
    datos = bytes(range(256)) * 40
    libusb = _LibUSBFalsa()

    _enviar_usb_pos80(datos, libusb=libusb)

    assert b"".join(libusb.bloques) == datos
    assert all(len(bloque) <= MIDA_BLOC_USB for bloque in libusb.bloques)
    assert libusb.liberada
    assert libusb.cerrada
    assert libusb.finalizada


class _WinspoolFalso:
    def __init__(self):
        self.bloques = []
        self.nombre = None
        self.documento = None
        self.pagina_iniciada = False
        self.pagina_finalizada = False
        self.documento_finalizado = False
        self.abortado = False
        self.cerrado = False

    def OpenPrinterW(self, nombre, impresora, opciones):
        assert opciones is None
        self.nombre = nombre
        impresora._obj.value = 7
        return True

    def StartDocPrinterW(self, impresora, nivel, informacion):
        assert impresora.value == 7
        assert nivel == 1
        self.documento = informacion._obj
        return 23

    def StartPagePrinter(self, impresora):
        self.pagina_iniciada = True
        return True

    def WritePrinter(self, impresora, buffer, longitud, escritos):
        self.bloques.append(ctypes.string_at(buffer, longitud))
        escritos._obj.value = longitud
        return True

    def EndPagePrinter(self, impresora):
        self.pagina_finalizada = True
        return True

    def EndDocPrinter(self, impresora):
        self.documento_finalizado = True
        return True

    def AbortPrinter(self, impresora):
        self.abortado = True
        return True

    def ClosePrinter(self, impresora):
        self.cerrado = True
        return True


def test_envia_escpos_raw_a_la_cua_de_windows():
    datos = bytes(range(256)) * 40
    winspool = _WinspoolFalso()

    _enviar_raw_windows("POS-8360 Recepció", datos, winspool=winspool)

    assert winspool.nombre == "POS-8360 Recepció"
    assert winspool.documento.pDocName == "Donatiu Gent Gran"
    assert winspool.documento.pDatatype == "RAW"
    assert b"".join(winspool.bloques) == datos
    assert all(len(bloque) <= MIDA_BLOC_USB for bloque in winspool.bloques)
    assert winspool.pagina_iniciada
    assert winspool.pagina_finalizada
    assert winspool.documento_finalizado
    assert not winspool.abortado
    assert winspool.cerrado
