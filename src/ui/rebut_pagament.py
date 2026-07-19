"""Impressió de justificants de donatius en impressores tèrmiques POS."""

from __future__ import annotations

from datetime import date, datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QMarginsF, QSizeF, Qt
from PySide6.QtGui import QImage, QPageLayout, QPageSize, QPainter, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter


NOM_ENTITAT = "Associació Gent Gran de Castelldefels"
AMPLADA_PAPER_MM = 80
MARGE_MM = 3
PUNTS_PER_MM = 72 / 25.4


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
    observaciones = str(pago.get("observaciones") or "").strip()
    observaciones_html = ""
    if observaciones:
        observaciones_html = (
            '<div class="separator"></div>'
            f'<div class="label">Observacions</div><div>{_text(observaciones)}</div>'
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
@page {{ size: 80mm auto; margin: 3mm; }}
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
</div>
<div class="separator"></div>
<div class="summary">
<div class="amount">{_import(pago.get('importe'))}</div>
</div>
{observaciones_html}
<div class="separator"></div>
<div class="footer">Conserveu aquest document com a justificant.</div>
</body></html>"""


def imprimir_rebut(parent, pago: dict, socio: dict, actividad: dict) -> bool:
    """Mostra les impressores del sistema i envia el donatiu a la seleccionada."""
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setHtml(construir_rebut_html(pago, socio, actividad))
    document.setTextWidth((AMPLADA_PAPER_MM - 2 * MARGE_MM) * PUNTS_PER_MM)
    altura_contingut_mm = document.size().height() / PUNTS_PER_MM
    altura_paper_mm = max(60, altura_contingut_mm + 2 * MARGE_MM)

    printer = QPrinter(QPrinter.HighResolution)
    page_size = QPageSize(
        QSizeF(AMPLADA_PAPER_MM, altura_paper_mm),
        QPageSize.Millimeter,
        "Donatiu POS 80 mm",
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

    document.setPageSize(printer.pageRect(QPrinter.Point).size())
    document.print_(printer)
    return True
