from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QRect, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import QPropertyAnimation
from PySide6.QtWidgets import QApplication, QAbstractItemView, QLabel, QGraphicsOpacityEffect, QTableView, QTableWidget


class TableCopyFilter(QObject):
    def __init__(self, table: QAbstractItemView):
        super().__init__(table)
        self._table = table

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.Copy):
            copied = copy_selected_table_text(self._table)
            if copied:
                show_copy_feedback(self._table)
                return True
        if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
            copied = copy_table_cell_text_at(self._table, event.pos())
            if copied:
                show_copy_feedback(self._table, event.pos())
                return True
        return super().eventFilter(obj, event)


def enable_table_copy(table: QAbstractItemView) -> None:
    if table.selectionMode() == QAbstractItemView.NoSelection:
        table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setFocusPolicy(Qt.StrongFocus)
    table.viewport().setFocusPolicy(Qt.StrongFocus)
    copy_filter = TableCopyFilter(table)
    table.installEventFilter(copy_filter)
    table.viewport().installEventFilter(copy_filter)
    table._table_copy_filter = copy_filter


def copy_selected_table_text(table: QAbstractItemView) -> bool:
    indexes = [
        index
        for index in table.selectedIndexes()
        if index.isValid() and not table.isRowHidden(index.row()) and not table.isColumnHidden(index.column())
    ]
    if not indexes:
        current = table.currentIndex()
        if current.isValid() and not table.isRowHidden(current.row()) and not table.isColumnHidden(current.column()):
            indexes = [current]
    if not indexes:
        return False

    rows = sorted({index.row() for index in indexes})
    columns = sorted({index.column() for index in indexes})
    selected = {(index.row(), index.column()) for index in indexes}
    lines = []
    for row in rows:
        values = []
        for column in columns:
            if (row, column) in selected:
                values.append(_cell_text(table, row, column))
            else:
                values.append("")
        lines.append("\t".join(values))

    QApplication.clipboard().setText("\n".join(lines))
    return True


def copy_table_cell_text_at(table: QAbstractItemView, pos) -> bool:
    index = table.indexAt(pos)
    if not index.isValid() or table.isRowHidden(index.row()) or table.isColumnHidden(index.column()):
        return False

    table.setCurrentIndex(index)
    QApplication.clipboard().setText(_cell_text(table, index.row(), index.column()))
    return True


def show_copy_feedback(table: QAbstractItemView, pos=None) -> None:
    rect = _feedback_rect(table, pos)
    if rect.isNull():
        return

    label = getattr(table, "_copy_feedback_label", None)
    if label is None:
        label = QLabel(table.viewport())
        label.setObjectName("copyFeedback")
        label.setStyleSheet(
            """
            QLabel#copyFeedback {
                background: rgba(200, 218, 169, 190);
                border: 2px solid #5f7f3f;
                border-radius: 3px;
            }
            """
        )
        effect = QGraphicsOpacityEffect(label)
        label.setGraphicsEffect(effect)
        label._copy_feedback_effect = effect
        table._copy_feedback_label = label
    else:
        effect = label._copy_feedback_effect

    animation = getattr(label, "_copy_feedback_animation", None)
    if animation is not None:
        animation.stop()

    label.setText("")
    label.setGeometry(rect.adjusted(1, 1, -1, -1))
    effect.setOpacity(0.85)
    label.show()
    label.raise_()

    animation = QPropertyAnimation(effect, b"opacity", label)
    animation.setDuration(500)
    animation.setStartValue(0.85)
    animation.setEndValue(0.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    animation.finished.connect(label.hide)
    label._copy_feedback_animation = animation
    animation.start()


def _feedback_rect(table: QAbstractItemView, pos=None) -> QRect:
    if pos is not None:
        index = table.indexAt(pos)
        return table.visualRect(index) if index.isValid() else QRect()

    indexes = [
        index
        for index in table.selectedIndexes()
        if index.isValid() and not table.isRowHidden(index.row()) and not table.isColumnHidden(index.column())
    ]
    if not indexes and table.currentIndex().isValid():
        indexes = [table.currentIndex()]
    if not indexes:
        return QRect()

    rect = QRect()
    for index in indexes:
        cell_rect = table.visualRect(index)
        rect = cell_rect if rect.isNull() else rect.united(cell_rect)
    return rect.intersected(table.viewport().rect())


def _cell_text(table: QAbstractItemView, row: int, column: int) -> str:
    if isinstance(table, QTableWidget):
        item = table.item(row, column)
        if item is None:
            return ""
        if item.data(Qt.CheckStateRole) is not None:
            return "Sí" if item.checkState() == Qt.Checked else "No"
        return item.text()

    if isinstance(table, QTableView):
        model = table.model()
        if model is None:
            return ""
        index = model.index(row, column)
        value = model.data(index, Qt.DisplayRole)
        return "" if value is None else str(value)

    return ""
