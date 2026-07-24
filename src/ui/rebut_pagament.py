"""Impressió de justificants de donatius en impressores tèrmiques POS."""

from __future__ import annotations

import ctypes
from ctypes.util import find_library
from datetime import date, datetime
from html import escape
import math
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QMarginsF, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter


NOM_ENTITAT = "Associació Gent Gran de Castelldefels"
# El controlador POS-80 reserva 72 mm imprimibles dins del rotlle físic de 80 mm.
AMPLADA_PAPER_MM = 72
MARGE_MM = 3
MARGE_SUPERIOR_POS80_MM = 1.5
MARGE_INFERIOR_EXTRA_MM = 4
PUNTS_PER_MM = 72 / 25.4
RESOLUCIO_POS80_DPI = 203
AMPLADA_POS80_PX = 576
ALCADA_BLOC_ESCPOS = 24
LINIES_AVANCE_ABANS_TALL = 4
POS80_USB_VID = 0x0416
POS80_USB_PID = 0x5011
POS80_USB_INTERFACE = 0
POS80_USB_ENDPOINT_OUT = 0x01
MIDA_BLOC_USB = 4096
TIMEOUT_USB_MS = 5000


class _DOC_INFO_1W(ctypes.Structure):
    """Estructura que Windows necessita per crear un treball d'impressió RAW."""

    _fields_ = [
        ("pDocName", ctypes.c_wchar_p),
        ("pOutputFile", ctypes.c_wchar_p),
        ("pDatatype", ctypes.c_wchar_p),
    ]


def _text(value) -> str:
    return escape(str(value or "").strip())


def _data(value) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    return _text(value)


def _import(value) -> str:
    try:
        return f"{float(value):.2f} €".replace(".", ",")
    except (TypeError, ValueError):
        return _text(value)


def _icono_bn_data_uri() -> str:
    """Retorna l'icona integrada en blanc i negre, preparada per a impressió."""
    icono_path = Path(__file__).resolve().parents[1] / "extra" / "icon.png"
    icono = QImage(str(icono_path))
    if icono.isNull():
        return ""

    # El fons blanc evita que la transparència original es torni negra.
    fondo = QImage(icono.size(), QImage.Format_RGB32)
    fondo.fill(Qt.white)
    painter = QPainter(fondo)
    painter.drawImage(0, 0, icono)
    painter.end()
    icono_bn = fondo.convertToFormat(QImage.Format_Mono)

    contenido = QByteArray()
    buffer = QBuffer(contenido)
    buffer.open(QIODevice.WriteOnly)
    icono_bn.save(buffer, "PNG")
    buffer.close()
    return "data:image/png;base64," + bytes(contenido.toBase64()).decode("ascii")


def construir_rebut_html(
    pago: dict,
    socio: dict,
    actividad: dict,
    *,
    nombre_entidad: str = NOM_ENTITAT,
    fecha_hora_impresion: datetime | None = None,
) -> str:
    """Construeix un justificant de donatiu compacte per a paper tèrmic de 80 mm."""
    nombre_socio = " ".join(
        str(socio.get(campo) or "").strip()
        for campo in ("nombre", "apellido1", "apellido2")
    ).strip()
    fecha_hora_impresion = fecha_hora_impresion or datetime.now()
    icono_uri = _icono_bn_data_uri()
    icono_html = f'<img src="{icono_uri}" width="42" height="42">' if icono_uri else ""
    descripcion = str(actividad.get("descripcion") or "").strip()
    descripcion_html = ""
    if descripcion:
        descripcion_html = (
            '<div class="row description">'
            f'<span class="label">Descripció:</span> {_text(descripcion)}'
            "</div>"
        )
    observaciones = str(pago.get("observaciones") or "").strip()
    observaciones_html = ""
    if observaciones:
        observaciones_html = (
            '<div class="separator"></div>'
            f'<div class="label">Observacions</div><div>{_text(observaciones)}</div>'
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: 72mm auto; margin: 3mm; }}
body {{ font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 9pt; color: #000; margin: 0; }}
.center {{ text-align: center; }}
.title {{ font-size: 12pt; font-weight: 700; }}
.subtitle {{ font-size: 10pt; font-weight: 700; margin-top: 2mm; }}
.header {{ line-height: 1.25; margin-bottom: 3mm; }}
.header-table {{ width: 100%; border-collapse: collapse; }}
.header-icon {{ width: 18%; text-align: left; vertical-align: top; }}
.header-text {{ width: 64%; text-align: center; vertical-align: middle; }}
.header-spacer {{ width: 18%; }}
.details {{ line-height: 1.2; margin: 3mm 0; }}
.summary {{ line-height: 1.25; margin: 3mm 0; }}
.separator {{ border-top: 1px dashed #000; margin: 2mm 0; }}
.row {{ width: 100%; margin: 1.5mm 0; }}
.description {{ font-size: 8.5pt; }}
.label {{ font-weight: 700; }}
.amount {{ font-size: 14pt; font-weight: 700; text-align: center; }}
.footer {{ text-align: center; margin-top: 3mm; font-size: 8pt; }}
</style></head><body>
<div class="header">
<table class="header-table" cellspacing="0" cellpadding="0"><tr>
<td class="header-icon">{icono_html}</td>
<td class="header-text"><div class="title">{_text(nombre_entidad)}</div><div class="subtitle">DONATIU</div></td>
<td class="header-spacer"></td>
</tr></table>
</div>
<div class="separator"></div>
<div class="details">
<div class="row"><span class="label">Data:</span> {_data(pago.get('fecha_pago'))}</div>
<div class="row"><span class="label">Hora:</span> {fecha_hora_impresion.strftime('%H:%M')}</div>
<div class="row"><span class="label">Soci/a:</span> {_text(nombre_socio)}</div>
<div class="row"><span class="label">Núm. soci:</span> {_text(socio.get('id'))}</div>
<div class="row"><span class="label">Concepte:</span> {_text(actividad.get('nombre'))}</div>
{descripcion_html}
</div>
<div class="separator"></div>
<div class="summary">
<div class="amount">{_import(pago.get('importe'))}</div>
</div>
{observaciones_html}
<div class="separator"></div>
<div class="footer">Conserveu aquest document com a justificant.</div>
</body></html>"""


def _es_cua_pos80_zywell(nombre: str) -> bool:
    """Detecta les denominacions habituals de la POS-8360/POS-80."""
    compacto = "".join(caracter for caracter in nombre.casefold() if caracter.isalnum())
    return "pos8360" in compacto or "pos80" in compacto


def _renderizar_rebut_pos80(document: QTextDocument) -> QImage:
    """Renderitza només l'alçada real del contingut, sense pàgina PDF."""
    escala = RESOLUCIO_POS80_DPI / 72
    marge_px = round(MARGE_MM * RESOLUCIO_POS80_DPI / 25.4)
    marge_inferior_extra_px = round(
        MARGE_INFERIOR_EXTRA_MM * RESOLUCIO_POS80_DPI / 25.4
    )
    document.setTextWidth((AMPLADA_PAPER_MM - 2 * MARGE_MM) * PUNTS_PER_MM)
    altura_contingut_px = math.ceil(document.size().height() * escala)
    altura_total_px = altura_contingut_px + marge_px + marge_inferior_extra_px

    imagen = QImage(AMPLADA_POS80_PX, max(1, altura_total_px), QImage.Format_Grayscale8)
    imagen.fill(Qt.white)
    painter = QPainter(imagen)
    painter.translate(marge_px, 0)
    painter.scale(escala, escala)
    document.drawContents(painter)
    painter.end()
    return imagen


def _imagen_a_escpos_segmentado(imagen: QImage, *, umbral: int = 180) -> bytes:
    """Codifica en blocs curts ``GS v 0`` compatibles amb la POS-8360."""
    imagen = imagen.convertToFormat(QImage.Format_Grayscale8)
    ancho_bytes = (imagen.width() + 7) // 8
    avance_superior = round(
        MARGE_SUPERIOR_POS80_MM * RESOLUCIO_POS80_DPI / 25.4
    )
    # Mateixa entrada estable que el driver: reinici, posició i un avanç curt.
    # L'avanç substitueix el marge superior que abans formava part de la imatge.
    datos = bytearray(b"\x1b@\x1b$\x01\x00\x1bJ")
    datos.append(avance_superior)

    for inicio_y in range(0, imagen.height(), ALCADA_BLOC_ESCPOS):
        alto_bloque = min(ALCADA_BLOC_ESCPOS, imagen.height() - inicio_y)
        datos.extend(
            (
                0x1D,
                0x76,
                0x30,
                0x00,
                ancho_bytes & 0xFF,
                (ancho_bytes >> 8) & 0xFF,
                alto_bloque & 0xFF,
                (alto_bloque >> 8) & 0xFF,
            )
        )
        for y in range(inicio_y, inicio_y + alto_bloque):
            for byte_x in range(ancho_bytes):
                fila = 0
                for bit in range(8):
                    x = byte_x * 8 + bit
                    if x < imagen.width() and QColor(imagen.pixel(x, y)).value() < umbral:
                        fila |= 0x80 >> bit
                datos.append(fila)

    # La fulla és uns mil·límetres més endavant que el capçal. Avancem quatre
    # línies abans del tall parcial perquè no arribi a tocar el text del peu.
    datos.extend((0x1B, 0x64, LINIES_AVANCE_ABANS_TALL, 0x1D, 0x56, 0x01))
    return bytes(datos)


def _configurar_libusb(libusb) -> None:
    """Defineix les signatures de libusb per evitar conversions de punters."""
    libusb.libusb_init.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    libusb.libusb_init.restype = ctypes.c_int
    libusb.libusb_exit.argtypes = [ctypes.c_void_p]
    libusb.libusb_exit.restype = None
    libusb.libusb_open_device_with_vid_pid.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint16,
        ctypes.c_uint16,
    ]
    libusb.libusb_open_device_with_vid_pid.restype = ctypes.c_void_p
    libusb.libusb_claim_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
    libusb.libusb_claim_interface.restype = ctypes.c_int
    libusb.libusb_release_interface.argtypes = [ctypes.c_void_p, ctypes.c_int]
    libusb.libusb_release_interface.restype = ctypes.c_int
    libusb.libusb_bulk_transfer.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ubyte,
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_int),
        ctypes.c_uint,
    ]
    libusb.libusb_bulk_transfer.restype = ctypes.c_int
    libusb.libusb_close.argtypes = [ctypes.c_void_p]
    libusb.libusb_close.restype = None


def _cargar_libusb():
    """Carrega libusb del paquet de l'aplicació o de la instal·lació local."""
    candidatos: list[Path | str] = []
    carpeta_empaquetada = getattr(sys, "_MEIPASS", None)
    if carpeta_empaquetada:
        raiz_empaquetada = Path(carpeta_empaquetada)
        carpetas_empaquetadas = (
            raiz_empaquetada,
            raiz_empaquetada / "_internal",
            raiz_empaquetada.parent / "Frameworks",
        )
        for carpeta in carpetas_empaquetadas:
            candidatos.extend(sorted(carpeta.glob("libusb-1.0*.dylib")))

    carpeta_ejecutable = Path(sys.executable).resolve().parent
    carpetas_locales = (
        carpeta_ejecutable,
        carpeta_ejecutable / "_internal",
        carpeta_ejecutable.parent / "Frameworks",
        Path("/opt/homebrew/lib"),
        Path("/usr/local/lib"),
    )
    for carpeta in carpetas_locales:
        candidatos.extend(sorted(carpeta.glob("libusb-1.0*.dylib")))
    encontrada = find_library("usb-1.0")
    if encontrada:
        candidatos.append(encontrada)

    intentados: set[str] = set()
    for candidato in candidatos:
        ruta = str(candidato)
        if ruta in intentados:
            continue
        intentados.add(ruta)
        if isinstance(candidato, Path) and not candidato.exists():
            continue
        try:
            libusb = ctypes.CDLL(ruta)
        except OSError:
            continue
        _configurar_libusb(libusb)
        return libusb

    raise RuntimeError(
        "No s'ha trobat el component USB necessari per imprimir amb la POS-8360"
    )


def _enviar_usb_pos80(datos: bytes, *, libusb=None) -> None:
    """Envia ESC/POS directament a la POS-8360, sense passar per CUPS."""
    libusb = libusb or _cargar_libusb()
    contexto = ctypes.c_void_p()
    resultado = libusb.libusb_init(ctypes.byref(contexto))
    if resultado != 0:
        raise RuntimeError(f"No s'ha pogut iniciar la connexió USB ({resultado})")

    dispositivo = None
    interfaz_reclamada = False
    try:
        dispositivo = libusb.libusb_open_device_with_vid_pid(
            contexto, POS80_USB_VID, POS80_USB_PID
        )
        if not dispositivo:
            raise RuntimeError(
                "No s'ha trobat la impressora POS-8360 connectada per USB"
            )

        resultado = libusb.libusb_claim_interface(
            dispositivo, POS80_USB_INTERFACE
        )
        if resultado != 0:
            raise RuntimeError(
                "La impressora POS-8360 està ocupada o no es pot obrir "
                f"({resultado})"
            )
        interfaz_reclamada = True

        posicion = 0
        while posicion < len(datos):
            bloque = datos[posicion : posicion + MIDA_BLOC_USB]
            enviados_bloque = 0
            while enviados_bloque < len(bloque):
                pendiente = bloque[enviados_bloque:]
                buffer = (ctypes.c_ubyte * len(pendiente)).from_buffer_copy(pendiente)
                transferidos = ctypes.c_int()
                resultado = libusb.libusb_bulk_transfer(
                    dispositivo,
                    POS80_USB_ENDPOINT_OUT,
                    buffer,
                    len(pendiente),
                    ctypes.byref(transferidos),
                    TIMEOUT_USB_MS,
                )
                if resultado != 0:
                    raise RuntimeError(
                        "S'ha interromput l'enviament a la POS-8360 "
                        f"({resultado})"
                    )
                if transferidos.value <= 0:
                    raise RuntimeError(
                        "La POS-8360 no ha acceptat les dades d'impressió"
                    )
                enviados_bloque += transferidos.value
            posicion += len(bloque)
    finally:
        if dispositivo and interfaz_reclamada:
            libusb.libusb_release_interface(dispositivo, POS80_USB_INTERFACE)
        if dispositivo:
            libusb.libusb_close(dispositivo)
        libusb.libusb_exit(contexto)


def _configurar_winspool(winspool) -> None:
    """Defineix les signatures del servei d'impressió natiu de Windows."""
    winspool.OpenPrinterW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]
    winspool.OpenPrinterW.restype = ctypes.c_int
    winspool.StartDocPrinterW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    winspool.StartDocPrinterW.restype = ctypes.c_uint32
    winspool.StartPagePrinter.argtypes = [ctypes.c_void_p]
    winspool.StartPagePrinter.restype = ctypes.c_int
    winspool.WritePrinter.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.POINTER(ctypes.c_uint32),
    ]
    winspool.WritePrinter.restype = ctypes.c_int
    winspool.EndPagePrinter.argtypes = [ctypes.c_void_p]
    winspool.EndPagePrinter.restype = ctypes.c_int
    winspool.EndDocPrinter.argtypes = [ctypes.c_void_p]
    winspool.EndDocPrinter.restype = ctypes.c_int
    winspool.AbortPrinter.argtypes = [ctypes.c_void_p]
    winspool.AbortPrinter.restype = ctypes.c_int
    winspool.ClosePrinter.argtypes = [ctypes.c_void_p]
    winspool.ClosePrinter.restype = ctypes.c_int


def _error_winspool(mensaje: str) -> RuntimeError:
    codigo = ctypes.get_last_error()
    detalle = f" (error de Windows {codigo})" if codigo else ""
    return RuntimeError(mensaje + detalle)


def _enviar_raw_windows(
    nombre_impresora: str, datos: bytes, *, winspool=None
) -> None:
    """Envia ESC/POS a una cua de Windows amb el tipus de dades RAW."""
    if winspool is None:
        winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
        _configurar_winspool(winspool)

    impresora = ctypes.c_void_p()
    if not winspool.OpenPrinterW(nombre_impresora, ctypes.byref(impresora), None):
        raise _error_winspool(
            f"No s'ha pogut obrir la impressora «{nombre_impresora}»"
        )

    documento_iniciado = False
    try:
        informacion = _DOC_INFO_1W("Donatiu Gent Gran", None, "RAW")
        if not winspool.StartDocPrinterW(
            impresora, 1, ctypes.byref(informacion)
        ):
            raise _error_winspool("No s'ha pogut crear el treball d'impressió")
        documento_iniciado = True

        if not winspool.StartPagePrinter(impresora):
            raise _error_winspool("No s'ha pogut iniciar la impressió del donatiu")

        posicion = 0
        while posicion < len(datos):
            bloque = datos[posicion : posicion + MIDA_BLOC_USB]
            enviados_bloque = 0
            while enviados_bloque < len(bloque):
                pendiente = bloque[enviados_bloque:]
                buffer = (ctypes.c_ubyte * len(pendiente)).from_buffer_copy(pendiente)
                escritos = ctypes.c_uint32()
                if not winspool.WritePrinter(
                    impresora,
                    ctypes.cast(buffer, ctypes.c_void_p),
                    len(pendiente),
                    ctypes.byref(escritos),
                ):
                    raise _error_winspool(
                        "S'ha interromput l'enviament a la POS-8360"
                    )
                if escritos.value <= 0:
                    raise RuntimeError(
                        "La POS-8360 no ha acceptat les dades d'impressió"
                    )
                enviados_bloque += escritos.value
            posicion += len(bloque)

        if not winspool.EndPagePrinter(impresora):
            raise _error_winspool("No s'ha pogut finalitzar la pàgina")
        if not winspool.EndDocPrinter(impresora):
            raise _error_winspool("No s'ha pogut finalitzar el donatiu")
        documento_iniciado = False
    finally:
        if documento_iniciado:
            winspool.AbortPrinter(impresora)
        winspool.ClosePrinter(impresora)


def _imprimir_pos80_escpos(nombre_impresora: str, document: QTextDocument) -> None:
    """Envia ESC/POS directament per USB; CUPS només identifica la impressora."""
    del nombre_impresora
    datos = _imagen_a_escpos_segmentado(_renderizar_rebut_pos80(document))
    _enviar_usb_pos80(datos)


def _imprimir_pos80_escpos_windows(
    nombre_impresora: str, document: QTextDocument
) -> None:
    """Envia el mateix ESC/POS a la cua RAW seleccionada a Windows."""
    datos = _imagen_a_escpos_segmentado(_renderizar_rebut_pos80(document))
    _enviar_raw_windows(nombre_impresora, datos)


def imprimir_rebut(parent, pago: dict, socio: dict, actividad: dict) -> bool:
    """Mostra les impressores del sistema i envia el donatiu a la seleccionada."""
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setHtml(construir_rebut_html(pago, socio, actividad))
    document.setTextWidth((AMPLADA_PAPER_MM - 2 * MARGE_MM) * PUNTS_PER_MM)
    altura_contingut_mm = document.size().height() / PUNTS_PER_MM
    altura_paper_mm = max(
        60,
        altura_contingut_mm + 2 * MARGE_MM + MARGE_INFERIOR_EXTRA_MM,
    )

    printer = QPrinter(QPrinter.HighResolution)
    printer.setResolution(203)
    page_size = QPageSize(
        QSizeF(AMPLADA_PAPER_MM, altura_paper_mm),
        QPageSize.Millimeter,
        "Donatiu POS-8360 (72 mm)",
        QPageSize.ExactMatch,
    )
    printer.setPageSize(page_size)
    printer.setPageMargins(
        QMarginsF(MARGE_MM, MARGE_MM, MARGE_MM, MARGE_MM),
        QPageLayout.Millimeter,
    )
    printer.setFullPage(False)

    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Imprimir donatiu")
    if dialog.exec() != QPrintDialog.Accepted:
        return False

    nombre_impresora = printer.printerName()
    if _es_cua_pos80_zywell(nombre_impresora):
        if sys.platform == "darwin":
            _imprimir_pos80_escpos(nombre_impresora, document)
            return True
        if sys.platform == "win32":
            _imprimir_pos80_escpos_windows(nombre_impresora, document)
            return True

    # El diàleg natiu pot substituir la mida personalitzada per la mida
    # predeterminada del controlador (72 × 210 mm). La restaurem per evitar
    # que la impressora avanci tota la zona blanca abans del contingut.
    printer.setResolution(203)
    printer.setPageSize(page_size)
    printer.setPageMargins(
        QMarginsF(MARGE_MM, MARGE_MM, MARGE_MM, MARGE_MM),
        QPageLayout.Millimeter,
    )
    printer.setFullPage(False)
    document.setPageSize(printer.pageRect(QPrinter.Point).size())
    document.print_(printer)
    return True
