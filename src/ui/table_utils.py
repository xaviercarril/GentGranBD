from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QItemSelectionModel, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import QPropertyAnimation
from PySide6.QtWidgets import QApplication, QAbstractItemView, QLabel, QGraphicsOpacityEffect, QMenu, QTableView, QTableWidget


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
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            QTimer.singleShot(0, lambda: show_current_cell_border(self._table))
        if event.type() == QEvent.ContextMenu and self._table.contextMenuPolicy() != Qt.CustomContextMenu:
            pos = event.pos()
            if obj is self._table:
                pos = self._table.viewport().mapFrom(self._table, pos)
            index = self._table.indexAt(pos)
            if index.isValid():
                self._table.setCurrentIndex(index)
                show_current_cell_border(self._table)
            menu = QMenu(self._table)
            add_table_copy_actions(menu, self._table, index)
            menu.exec(self._table.viewport().mapToGlobal(pos))
            return True
        if event.type() in {QEvent.Resize, QEvent.Wheel}:
            QTimer.singleShot(0, lambda: show_current_cell_border(self._table))
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


def copy_current_cell_text(table: QAbstractItemView) -> bool:
    index = table.currentIndex()
    if not index.isValid() or table.isRowHidden(index.row()) or table.isColumnHidden(index.column()):
        return False
    QApplication.clipboard().setText(_cell_text(table, index.row(), index.column()))
    show_copy_feedback(table, table.visualRect(index).center())
    return True


def copy_current_row_text(table: QAbstractItemView) -> bool:
    index = table.currentIndex()
    model = table.model()
    if model is None or not index.isValid() or table.isRowHidden(index.row()):
        return False
    values = []
    for column in range(model.columnCount()):
        if not table.isColumnHidden(column):
            values.append(_cell_text(table, index.row(), column))
    QApplication.clipboard().setText("\t".join(values))
    show_copy_feedback(table)
    return True


def add_table_copy_actions(menu: QMenu, table: QAbstractItemView, index=None) -> None:
    if index is not None and index.isValid():
        selection_model = table.selectionModel()
        if selection_model is not None:
            selection_model.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        else:
            table.setCurrentIndex(index)
    copy_cell = menu.addAction("Copiar camp")
    copy_cell.triggered.connect(lambda _checked=False: copy_current_cell_text(table))
    copy_selection = menu.addAction("Copiar selecció")
    copy_selection.triggered.connect(lambda _checked=False: copy_selected_table_text(table) and show_copy_feedback(table))


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


def show_current_cell_border(table: QAbstractItemView) -> None:
    index = table.currentIndex()
    border = getattr(table, "_current_cell_border", None)
    if border is None:
        border = QLabel(table.viewport())
        border.setObjectName("currentCellBorder")
        border.setAttribute(Qt.WA_TransparentForMouseEvents)
        border.setStyleSheet(
            """
            QLabel#currentCellBorder {
                background: transparent;
                border: 2px solid #5f7f3f;
                border-radius: 2px;
            }
            """
        )
        table._current_cell_border = border

    if not index.isValid() or table.isRowHidden(index.row()) or table.isColumnHidden(index.column()):
        border.hide()
        return

    rect = table.visualRect(index).intersected(table.viewport().rect())
    if rect.isNull():
        border.hide()
        return
    border.setGeometry(rect.adjusted(1, 1, -1, -1))
    border.show()
    border.raise_()


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
