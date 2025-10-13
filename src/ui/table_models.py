from decimal import Decimal

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class DictTableModel(QAbstractTableModel):
    """
    Model senzill (només lectura) que mostra una llista de dicts
    segons l'ordre de claus indicat a `headers`.
    """

    def __init__(self, rows, headers, parent=None):
        """
        headers pot ser:
          • ['id','nombre',...]                     (etiqueta = clau.capitalize())
          • [('ID', 'id'), ('Nom', 'nombre'), ...] (etiqueta, clau)
        """
        super().__init__(parent)
        self.rows = rows or []

        # Normalitzem: guardem llistes paral·leles
        if headers and isinstance(headers[0], (list, tuple)):
            self.labels, self.keys = zip(*headers)
        else:
            self.keys = headers
            self.labels = [h.capitalize() for h in headers]

    # ── obligatoris ──────────────────────────────────────────
    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.keys)

    def data(self, idx, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        key = self.keys[idx.column()]
        value = self.rows[idx.row()].get(key, "")

        # Mostra cel·la buida quan el valor és None
        if value is None:
            return "----"

        if isinstance(value, Decimal):
            # Manté números enters sense decimals (ex. telèfons emmagatzemats com a decimals)
            text = format(value, "f")
            return text.rstrip("0").rstrip(".") or "0"

        if isinstance(value, float):
            if value.is_integer():
                return str(int(value))
            text = f"{value}"
            return text.rstrip("0").rstrip(".") or "0"

        return str(value)

    def headerData(self, sec, orient, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orient == Qt.Horizontal:
            return self.labels[sec]
        return super().headerData(sec, orient, role)
