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
            raise FileNotFoundError(ruta_archivo)

        ext = os.path.splitext(ruta_archivo)[1].lower()
        if ext in {".xls", ".xlsx"}:
            df = pd.read_excel(ruta_archivo)
        elif ext == ".csv":
            try:
                df = pd.read_csv(ruta_archivo)
            except UnicodeDecodeError:
                # Intento con una codificación común alternativa
                df = pd.read_csv(ruta_archivo, encoding="latin-1")
        else:
            raise ValueError("Formato de archivo no soportado. Usa .xlsx, .xls o .csv")

        if df is None or df.empty:
            raise EmptyDataError("El archivo no contiene datos.")

    except EmptyDataError:
        raise ValueError("El archivo está vacío o no contiene filas válidas.")
    except ParserError:
        raise ValueError("El archivo tiene un formato inválido. Revisa separadores y cabeceras.")
    except Exception as e:
        # Mensaje genérico para cualquier otro error de lectura
        raise ValueError(f"No se pudo leer el archivo. Verifica que no esté dañado y que el formato sea válido. Detalle: {e}")

    df = df.fillna("")  # Reemplaza NaN por cadenas vacías

    total = len(df)
    procesadas = 0
    creados = 0

    with SessionLocal() as db:
        try:
            # Desactivar autoflush para performance en lote
            db.autoflush = False
            for idx, row in df.iterrows():
                try:
                    datos = {
                        "id": row.get("Nº SOCI", None),
                        "nombre": str(row.get("NOM", "")).strip(),
                        "apellido1": str(row.get("1r COGNOM", "")).strip(),
                        "apellido2": str(row.get("2n COGNOM", "")).strip() or None,
                        "dniNie": str(row.get("D.N.I.", "")).strip() or None,
                        "direccion": str(row.get("ADREÇA", "")).strip() or None,
                        "telefonoFijo": str(row.get("TELÈFON", "")).strip() or None,
                        "telefonoMovil": str(row.get("MÒBIL", "")).strip() or None,
                        "email": str(row.get("E-MAIL", "")).strip() or None,
                        "grupoDifusion": str(row.get("E", "")).strip() or None,
                        "fechaAlta": _parse_fecha(row.get("DATA D'ALTA", "")),
                        "fechaBaja": _parse_fecha(row.get("BAIXAS", ""), optional=True),
                        "observaciones": str(row.get("OBSERVACIONES", "")).strip() or None,
                    }

                    # Warnings no críticos
                    if not datos["dniNie"] and on_warning:
                        on_warning(idx, "DNI/NIE vacío; se intentará continuar si el modelo lo permite")
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
