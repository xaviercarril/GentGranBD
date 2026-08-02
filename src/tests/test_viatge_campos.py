from datetime import date

import pytest
from openpyxl import load_workbook
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

import controladores.actividades as actividades
import controladores.inscripcion_socio as inscripciones
import controladores.punto_recogida as puntos_recogida
import database
import ui.actividad_detail as actividad_detail
from exportador.excel_participantes import generar_excel_participantes_viaje_session
from exportador.pdf_inscripciones import TRIP_HEADERS, _build_table
from models import Actividad, Base, EstadoInscripcion, InscripcionSocio, TipoActividadEnum
from ui.actividad_detail import InscripcionesActividadTableModel, PuntoRecogidaDelegate


def test_campos_del_viaje_se_guardan_y_se_pueden_modificar(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(actividades, "SessionLocal", Session)
    monkeypatch.setattr(inscripciones, "SessionLocal", Session)

    with Session() as session:
        viaje = Actividad(nombre="Viatge", tipo=TipoActividadEnum.VIATGE)
        session.add(viaje)
        session.commit()
        viaje_id = viaje.id

    inscripcion = inscripciones.registrar_inscripcion(
        {
            "actividadID": viaje_id,
            "noSocioNombre": "Maria",
            "fechaInscripcion": date.today(),
            "estado": EstadoInscripcion.INSCRIT.value,
            "asiento": "12A",
            "lugarRecogida": "Plaça de l'Església",
        }
    )

    guardada = inscripciones.consultar_inscripcion(inscripcion.id)
    assert guardada["asiento"] == "12A"
    assert guardada["lugarRecogida"] == "Plaça de l'Església"

    inscripciones.modificar_inscripcion(
        inscripcion.id,
        {"asiento": "8", "lugarRecogida": "Ajuntament"},
    )

    modificada = inscripciones.consultar_inscripcion(inscripcion.id)
    assert modificada["asiento"] == "8"
    assert modificada["lugarRecogida"] == "Ajuntament"
    engine.dispose()


def test_campos_del_viaje_son_editables_en_la_tabla():
    assert {"asiento", "lugarRecogida"} <= InscripcionesActividadTableModel.EDITABLE_KEYS


def test_catalogo_puntos_recogida_permite_reutilizar_y_evitar_duplicados(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(puntos_recogida, "SessionLocal", Session)

    punto_id = puntos_recogida.registrar_punto_recogida(
        {"nombre": "  Ajuntament  ", "direccion": "Plaça Major, 1"}
    )
    assert puntos_recogida.consultar_puntos_recogida() == [
        {"id": punto_id, "nombre": "Ajuntament", "direccion": "Plaça Major, 1"}
    ]

    with pytest.raises(ValueError, match="Ja existeix"):
        puntos_recogida.registrar_punto_recogida({"nombre": "ajuntament"})

    with Session() as session:
        session.add(
            InscripcionSocio(
                lugarRecogida="Ajuntament",
                fechaInscripcion=date.today(),
                estado=EstadoInscripcion.INSCRIT,
            )
        )
        session.commit()

    puntos_recogida.modificar_punto_recogida(
        punto_id, {"nombre": "Estació", "direccion": ""}
    )
    assert puntos_recogida.consultar_puntos_recogida()[0]["nombre"] == "Estació"
    with Session() as session:
        assert session.query(InscripcionSocio).one().lugarRecogida == "Estació"

    puntos_recogida.eliminar_punto_recogida(punto_id)
    assert puntos_recogida.consultar_puntos_recogida() == []
    engine.dispose()


def test_delegate_ofrece_los_puntos_guardados():
    app = QApplication.instance() or QApplication([])
    delegate = PuntoRecogidaDelegate(["Ajuntament", "Estació"])
    editor = delegate.createEditor(None, None, None)

    assert [editor.itemText(i) for i in range(editor.count())] == [
        "Sense assignar",
        "Altres (Observacions)",
        "Ajuntament",
        "Estació",
    ]
    editor.close()


def test_lugar_recogida_se_puede_desasignar_desde_el_desplegable():
    cambios = []
    model = InscripcionesActividadTableModel(
        [{"id": 7, "lugarRecogida": "Ajuntament"}],
        [("Lloc de recollida", "lugarRecogida")],
        lambda *args: cambios.append(args),
    )

    assert model.setData(model.index(0, 0), None)
    assert cambios == [(7, "lugarRecogida", None)]
    assert model.rows[0]["lugarRecogida"] is None


def test_gestion_de_puntos_guarda_directamente_desde_la_tabla(monkeypatch):
    app = QApplication.instance() or QApplication([])
    modificaciones = []
    altas = []
    monkeypatch.setattr(
        actividad_detail,
        "consultar_puntos_recogida",
        lambda: [{"id": 1, "nombre": "Ajuntament", "direccion": "Plaça Major"}],
    )
    monkeypatch.setattr(
        actividad_detail,
        "modificar_punto_recogida",
        lambda punto_id, cambios: modificaciones.append((punto_id, cambios)),
    )
    monkeypatch.setattr(
        actividad_detail,
        "registrar_punto_recogida",
        lambda data: altas.append(data) or 2,
    )

    dialog = actividad_detail.PuntosRecogidaDialog()
    assert not hasattr(dialog, "btn_guardar")

    dialog.table.item(0, 1).setText("Nova indicació")
    assert modificaciones == [(1, {"direccion": "Nova indicació"})]

    dialog._new()
    nueva_fila = dialog.table.rowCount() - 1
    dialog.table.item(nueva_fila, 0).setText("Estació")
    assert altas == [{"nombre": "Estació", "direccion": ""}]
    assert dialog.table.item(nueva_fila, 0).data(Qt.UserRole) == 2
    dialog.close()


def test_excel_del_viaje_incluye_asiento_y_lugar_de_recogida(session, tmp_path):
    viaje = Actividad(nombre="Viatge", tipo=TipoActividadEnum.VIATGE)
    session.add(viaje)
    session.commit()
    session.add(
        InscripcionSocio(
            actividadID=viaje.id,
            noSocioNombre="Joan",
            fechaInscripcion=date.today(),
            estado=EstadoInscripcion.INSCRIT,
            asiento="5B",
            lugarRecogida="Estació",
        )
    )
    session.commit()

    output = tmp_path / "participants.xlsx"
    generar_excel_participantes_viaje_session(session, viaje.id, str(output))

    ws = load_workbook(output)["Participants"]
    headers = [cell.value for cell in ws[3]]
    assert headers[9:11] == ["Seient", "Lloc de recollida"]
    assert ws["J4"].value == "5B"
    assert ws["K4"].value == "Estació"


def test_pdf_del_viaje_incluye_asiento_y_lugar_de_recogida():
    inscripcion = InscripcionSocio(
        fechaInscripcion=date.today(),
        estado=EstadoInscripcion.INSCRIT,
        asiento="3C",
        lugarRecogida="Centre cívic",
    )

    table = _build_table([inscripcion], include_dni=True)
    row = [cell.getPlainText() for cell in table._cellvalues[1]]

    assert row[TRIP_HEADERS.index("Seient")] == "3C"
    assert row[TRIP_HEADERS.index("Lloc de recollida")] == "Centre cívic"


def test_migracion_anade_campos_del_viaje_a_bases_existentes(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE socios (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE inscripciones (id INTEGER PRIMARY KEY)"))

    monkeypatch.setattr(database, "engine", engine)
    database.ensure_schema_updates()

    columns = {column["name"] for column in inspect(engine).get_columns("inscripciones")}
    assert {"asiento", "lugarRecogida"} <= columns
    engine.dispose()


def test_migracion_crea_catalogo_desde_lugares_ya_asignados(monkeypatch):
    engine = create_engine("sqlite:///:memory:", echo=False)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE socios (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text(
                'CREATE TABLE inscripciones '
                '(id INTEGER PRIMARY KEY, "lugarRecogida" VARCHAR(255))'
            )
        )
        connection.execute(
            text(
                'INSERT INTO inscripciones (id, "lugarRecogida") VALUES '
                "(1, ' Estació '), (2, 'estació'), (3, ''), (4, NULL)"
            )
        )

    monkeypatch.setattr(database, "engine", engine)
    database.ensure_schema_updates()

    with engine.connect() as connection:
        nombres = connection.execute(
            text("SELECT nombre FROM puntos_recogida ORDER BY nombre")
        ).scalars().all()
    assert nombres == ["Estació"]

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM puntos_recogida"))
    database.ensure_schema_updates()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT nombre FROM puntos_recogida")).all() == []
    engine.dispose()
