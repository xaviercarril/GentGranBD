import pandas as pd
from datetime import datetime
from controladores.socios import registrar_socio

def importar_socios_desde_excel(ruta_archivo: str) -> int:
    """
    Importa socios desde un archivo Excel o CSV.
    Retorna el número de socios importados.
    """
    df = pd.read_excel(ruta_archivo) if ruta_archivo.endswith(('.xls', '.xlsx')) else pd.read_csv(ruta_archivo)

    df = df.fillna("")  # Reemplaza NaN por cadenas vacías

    contador = 0
    for _, row in df.iterrows():
        try:
            datos = {
              "id": row.get("Nº SOCI", None),  # Asume que el ID puede ser opcional
              "nombre": row.get("NOM", "").strip(),
              "apellido1": row.get("1r COGNOM", "").strip(),
              "apellido2": row.get("2n COGNOM", "").strip() or None,
              "dniNie": row.get("D.N.I.", "").strip() or None,
              "direccion": row.get("ADREÇA", "").strip() or None,
              "telefonoFijo": str(row.get("TELÈFON", "")).strip() or None,
              "telefonoMovil": str(row.get("MÒBIL", "")).strip() or None,
              "email": str(row.get("E-MAIL", "")).strip() or None,
              "grupoDifusion": str(row.get("E", "")).strip() or None,
              "fechaAlta": _parse_fecha(row.get("DATA D'ALTA", "")),
              "fechaBaja": _parse_fecha(row.get("BAIXAS", ""), optional=True),
              "observaciones": str(row.get("OBSERVACIONES", "")).strip() or None,
            }

            registrar_socio(datos)
            contador += 1
        except Exception as e:
            print(f"Error al importar fila: {e}")
            continue

    return contador

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