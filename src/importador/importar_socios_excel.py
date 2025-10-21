import os
import pandas as pd  # lazy import
from pandas.errors import EmptyDataError, ParserError
from datetime import datetime
from typing import Callable, Optional
from sqlalchemy.exc import IntegrityError
from database import SessionLocal
from controladores.socios import construir_socio_modelo


ProgressCb = Optional[Callable[[int, int], None]]  # (procesadas, total)
WarnCb = Optional[Callable[[int, str], None]]      # (fila_index, mensaje)
ErrorCb = Optional[Callable[[int, str], None]]     # (fila_index, mensaje)


def _normalize_header(name: str) -> str:
    """Normaliza cabeceras para poder mapear alias fácilmente."""
    if name is None:
        return ""
    return "".join(ch for ch in str(name).strip().lower() if ch.isalnum())


def _build_column_lookup(columns) -> dict[str, str]:
    """
    Crea un diccionario que mapea cabeceras normalizadas a su nombre original.
    Si hay colisiones conserva la primera aparición (se asume que las columnas son únicas).
    """
    lookup: dict[str, str] = {}
    for col in columns:
        norm = _normalize_header(col)
        if norm and norm not in lookup:
            lookup[norm] = col
    return lookup


def _clean_str(value) -> str | None:
    """Convierte a str, limpia espacios y normaliza nulos (NaN/None)."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"nan", "none", "null"}:
        return None
    return text


def _is_row_empty(row) -> bool:
    """
    Detecta files sense informació útil per evitar validar-les.
    Es considera buida si tots els valors són nuls/descriptors en blanc.
    """
    return all(_clean_str(value) is None for _, value in row.items())


def _get_cell(row, lookup: dict[str, str], *aliases: str):
    """Recupera el valor de la primera cabecera disponible entre los alias proporcionados."""
    for alias in aliases:
        norm = _normalize_header(alias)
        if norm in lookup:
            original = lookup[norm]
            val = row.get(original, "")
            if val is not None:
                return val
    return ""


def importar_socios_desde_excel(
    ruta_archivo: str,
    on_progress: ProgressCb = None,
    on_warning: WarnCb = None,
    on_error: ErrorCb = None,
) -> int:
    """
    Importa socios desde un archivo Excel o CSV con verbosidad y rollback en error.
    - Muestra progreso por callback (procesadas/total).
    - Emite warnings por campos faltantes no críticos (p.ej. email vacío).
    - Si ocurre un error duro (validación/duplicado), aborta y hace rollback total.

    Retorna el número de socios importados (commit único) si todo va bien.
    """

    # Lectura robusta del archivo con mensajes claros para el usuario
    try:
        if not ruta_archivo or not isinstance(ruta_archivo, str):
            raise ValueError("No se ha proporcionado una ruta de archivo válida.")

        if not os.path.exists(ruta_archivo):
            raise FileNotFoundError(f"El archivo no se encontró: {ruta_archivo}")

        ext = os.path.splitext(ruta_archivo)[1].lower()
        if ext in {".xls", ".xlsx"}:
            df = pd.read_excel(ruta_archivo)
        elif ext == ".csv":
            # Permite detectar automáticamente delimitadores como ';' muy comunes en exports de Excel
            read_opts = {"sep": None, "engine": "python"}
            try:
                df = pd.read_csv(ruta_archivo, **read_opts)
            except UnicodeDecodeError:
                # Intento con una codificación común alternativa
                read_opts["encoding"] = "latin-1"
                df = pd.read_csv(ruta_archivo, **read_opts)
        else:
            raise ValueError("Formato de archivo no soportado. Usa .xlsx, .xls o .csv")

        if df.empty:
            raise EmptyDataError("El archivo no contiene datos.")

    except EmptyDataError:
        raise ValueError("El archivo está vacío o no contiene filas válidas.")
    except ParserError:
        raise ValueError("El archivo tiene un formato inválido. Revisa separadores y cabeceras.")
    except Exception as e:
        # Mensaje genérico para cualquier otro error de lectura, incluyendo detalles originales
        raise ValueError(f"No se pudo leer el archivo. Verifica que el formato sea válido y que el archivo no esté dañado. Detalles: {str(e)}")

    df = df.fillna("")  # Reemplaza NaN por cadenas vacías
    column_lookup = _build_column_lookup(df.columns)

    total = len(df)
    procesadas = 0
    creados = 0

    with SessionLocal() as db:
        try:
            # Desactivar autoflush para performance en lote
            db.autoflush = False
            for idx, row in df.iterrows():
                try:
                    if _is_row_empty(row):
                        continue

                    dni_raw = _get_cell(
                        row,
                        column_lookup,
                        "D.N.I.",
                        "D.N.I",
                        "DNI",
                        "DNI/NIE",
                        "NIF",
                        "DOCUMENT",
                        "DOCUMENTO",
                        "NUM. DOCUMENT",
                        "NUM DOCUMENT",
                        "NUMERO DOCUMENT",
                        "NUM DOC",
                    )
                    fecha_alta_raw = _get_cell(row, column_lookup, "DATA D'ALTA", "DATA ALTA", "FECHA ALTA", "F. ALTA")
                    fecha_baja_raw = _get_cell(row, column_lookup, "BAIXAS", "DATA BAIXA", "FECHA BAJA", "F. BAJA")

                    datos = {
                        "id": row.get("Nº SOCI", None) or row.get("NUM SOCI", None),
                        "nombre": _clean_str(_get_cell(row, column_lookup, "NOM", "NOMBRE", "NOMBRE SOCI")) or "",
                        "apellido1": _clean_str(_get_cell(row, column_lookup, "1r COGNOM", "COGNOM1", "PRIMER COGNOM", "APELLIDO1", "APELLIDO 1")) or "",
                        "apellido2": _clean_str(_get_cell(row, column_lookup, "2n COGNOM", "COGNOM2", "SEGON COGNOM", "APELLIDO2", "APELLIDO 2")),
                        "dniNie": _clean_str(dni_raw),
                        "direccion": _clean_str(_get_cell(row, column_lookup, "ADREÇA", "DIRECCION", "ADREÇA 1", "DIRECCIÓ", "ADRECA")),
                        "telefonoFijo": _clean_str(_get_cell(row, column_lookup, "TELÈFON", "TELEFON", "TELEFONO")),
                        "telefonoMovil": _clean_str(_get_cell(row, column_lookup, "MÒBIL", "MOBIL", "TELÈFON MÒBIL", "MOVIL", "TELEFONO MOVIL")),
                        "email": _clean_str(_get_cell(row, column_lookup, "E-MAIL", "EMAIL", "CORREU", "CORREO")),
                        "grupoDifusion": _clean_str(_get_cell(row, column_lookup, "E", "GRUP DIFUSIO", "GRUPO DIFUSION")),
                        "fechaAlta": _parse_fecha(fecha_alta_raw),
                        "fechaBaja": _parse_fecha(fecha_baja_raw, optional=True),
                        "observaciones": _clean_str(_get_cell(row, column_lookup, "OBSERVACIONES", "OBSERVACIONS", "OBSERVACIONS 1")),
                    }

                    if not datos["dniNie"]:
                        raise ValueError("DNI/NIE: és obligatori")

                    # Warnings no críticos
                    if not datos["email"] and on_warning:
                        on_warning(idx, "Email vacío")

                    socio = construir_socio_modelo(datos)
                    db.add(socio)
                    # Forçar flush per detectar duplicats en aquesta fila dins de la transacció
                    db.flush()
                    creados += 1
                except IntegrityError as e:
                    db.rollback()
                    if on_error:
                        dni = datos.get("dniNie")
                        num = datos.get("id")
                        if num:
                            on_error(idx, f"Soci duplicat (Nº soci {num}). Ja existeix. Corregeix el fitxer i torna-ho a provar.")
                        elif dni:
                            on_error(idx, f"Soci duplicat (DNI/NIE {dni}). Ja existeix. Corregeix el fitxer i torna-ho a provar.")
                        else:
                            on_error(idx, "Registre duplicat. Ja existeix. Corregeix el fitxer i torna-ho a provar.")
                    raise
                except Exception as e:
                    db.rollback()
                    if on_error:
                        # Mensajes más claros para usuario final
                        msg = str(e)
                        if "DNI" in msg or "dniNie" in msg:
                            msg = "El DNI/NIE falta o no té un format vàlid."
                        elif "nombre" in msg or "Nom" in msg:
                            msg = "El nom és obligatori."
                        on_error(idx, msg)
                    raise
                finally:
                    procesadas += 1
                    if on_progress:
                        on_progress(procesadas, total)

            # Si llegó aquí, confirmar en bloque
            db.commit()
            return creados
        except Exception:
            # rollback global por seguridad
            db.rollback()
            raise

def _parse_fecha(fecha_raw, optional=False):
    if not fecha_raw:
        return None if optional else datetime.today().date()

    if isinstance(fecha_raw, datetime):
        return fecha_raw.date()

    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(fecha_raw).strip(), fmt).date()
        except ValueError:
            continue

    if optional:
        return None
    raise ValueError(f"Formato de fecha no reconocido: {fecha_raw}")
