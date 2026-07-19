import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ui.lopd_dialog as lopd_dialog


class _WidgetState:
    def __init__(self) -> None:
        self.text = ""
        self.enabled = None

    def setText(self, text: str) -> None:
        self.text = text

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = enabled


def test_document_button_stays_available_without_signature(monkeypatch):
    monkeypatch.setattr(lopd_dialog, "consultar_firma_LOPD", lambda _socio_id: None)
    status = _WidgetState()
    view_button = _WidgetState()
    delete_button = _WidgetState()
    dialog = SimpleNamespace(
        _socio_id=7,
        _status_label=status,
        _btn_view=view_button,
        _btn_delete=delete_button,
    )

    lopd_dialog.LOPDFirmaDialog._load_signature_status(dialog)

    assert status.text == "No hi ha cap document signat."
    assert view_button.enabled is True
    assert delete_button.enabled is False


def test_opening_unsigned_document_generates_a_temporary_pdf(monkeypatch, tmp_path):
    pdf_path = tmp_path / "lopd.pdf"
    opened = []
    monkeypatch.setattr(lopd_dialog, "consultar_firma_LOPD", lambda _socio_id: None)

    def fail_if_signed_document_is_requested(_socio_id):
        raise AssertionError("No s'ha de consultar un document signat")

    monkeypatch.setattr(lopd_dialog, "obtener_documento_firma_LOPD", fail_if_signed_document_is_requested)
    dialog = SimpleNamespace(
        _socio_id=7,
        _temp_view_files=[],
        _generar_pdf_temporal=lambda: str(pdf_path),
        _open_file=opened.append,
    )

    lopd_dialog.LOPDFirmaDialog._abrir_documento_guardado(dialog)

    assert dialog._temp_view_files == [Path(pdf_path)]
    assert opened == [Path(pdf_path)]


def test_signed_status_indicator_is_unchanged(monkeypatch):
    monkeypatch.setattr(
        lopd_dialog,
        "consultar_firma_LOPD",
        lambda _socio_id: {"fechaFirma": date(2026, 7, 19), "tieneDocumento": True},
    )
    status = _WidgetState()
    view_button = _WidgetState()
    delete_button = _WidgetState()
    dialog = SimpleNamespace(
        _socio_id=7,
        _status_label=status,
        _btn_view=view_button,
        _btn_delete=delete_button,
    )

    lopd_dialog.LOPDFirmaDialog._load_signature_status(dialog)

    assert status.text == "Document signat el 19/07/2026."
    assert view_button.enabled is True
    assert delete_button.enabled is True
