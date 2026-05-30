from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QComboBox, QPushButton, QWidget


class Palette:
    APP_BG = "#f4f7f0"
    SURFACE = "#ffffff"
    SURFACE_ALT = "#f9fbf6"
    BORDER = "#d6ddcc"
    BORDER_STRONG = "#b7c4a7"
    TEXT = "#263021"
    TEXT_MUTED = "#66705e"
    PRIMARY = "#5f7f3f"
    PRIMARY_HOVER = "#506e35"
    PRIMARY_PRESSED = "#40592a"
    PRIMARY_SOFT = "#dce8cf"
    SELECTION = "#c8daa9"
    DESTRUCTIVE = "#b6534f"
    DESTRUCTIVE_HOVER = "#9f4440"
    WARNING = "#fff3cb"


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {Palette.APP_BG};
        color: {Palette.TEXT};
        font-size: 13px;
    }}

    QMainWindow, QDialog {{
        background: {Palette.APP_BG};
    }}

    QMenuBar {{
        background: {Palette.SURFACE};
        border-bottom: 1px solid {Palette.BORDER};
        padding: 3px 6px;
    }}
    QMenuBar::item {{
        padding: 6px 10px;
        border-radius: 5px;
    }}
    QMenuBar::item:selected {{
        background: {Palette.PRIMARY_SOFT};
    }}
    QMenu {{
        background: {Palette.SURFACE};
        border: 1px solid {Palette.BORDER};
        padding: 5px;
    }}
    QMenu::item {{
        padding: 7px 28px 7px 10px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {Palette.PRIMARY_SOFT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {Palette.BORDER};
        margin: 5px 8px;
    }}

    QTabWidget::pane {{
        border: 1px solid {Palette.BORDER};
        border-radius: 7px;
        background: {Palette.SURFACE};
        top: -1px;
    }}
    QTabBar::tab {{
        background: #edf2e7;
        color: {Palette.TEXT_MUTED};
        border: 1px solid {Palette.BORDER};
        border-bottom: none;
        padding: 8px 16px;
        margin-right: 3px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
        min-width: 86px;
    }}
    QTabBar::tab:selected {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
        font-weight: 600;
        border-color: {Palette.BORDER_STRONG};
    }}
    QTabBar::tab:hover {{
        background: {Palette.PRIMARY_SOFT};
        color: {Palette.TEXT};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QTimeEdit {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
        border: 1px solid {Palette.BORDER_STRONG};
        border-radius: 5px;
        padding: 3px 7px;
        min-height: 24px;
        selection-background-color: {Palette.SELECTION};
        selection-color: {Palette.TEXT};
    }}
    QTextEdit, QPlainTextEdit {{
        padding: 5px 7px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
        border: 1px solid {Palette.PRIMARY};
    }}
    QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
        background: #eef1ea;
        color: #8b9583;
    }}
    QComboBox::drop-down {{
        width: 24px;
        border-left: 1px solid {Palette.BORDER};
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
        background: #f1f6ec;
    }}
    QComboBox::drop-down:hover {{
        background: {Palette.PRIMARY_SOFT};
    }}
    QComboBox::down-arrow {{
        image: url(ui/assets/chevron-down.svg);
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
        border: 1px solid {Palette.BORDER_STRONG};
        border-radius: 6px;
        padding: 4px;
        min-width: 220px;
        outline: 0;
        selection-background-color: {Palette.SELECTION};
        selection-color: {Palette.TEXT};
    }}
    QComboBox QAbstractItemView::indicator {{
        width: 0px;
        height: 0px;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 24px;
        padding: 4px 10px;
        border-radius: 4px;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {Palette.PRIMARY_SOFT};
        color: {Palette.TEXT};
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {Palette.BORDER};
        border-bottom: 1px solid {Palette.BORDER};
        border-top-right-radius: 5px;
        background: #f1f6ec;
    }}
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 24px;
        border-left: 1px solid {Palette.BORDER};
        border-bottom-right-radius: 5px;
        background: #f1f6ec;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background: {Palette.PRIMARY_SOFT};
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url(ui/assets/chevron-up.svg);
        width: 10px;
        height: 10px;
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url(ui/assets/chevron-down.svg);
        width: 10px;
        height: 10px;
    }}

    QDateEdit::drop-down, QTimeEdit::drop-down {{
        width: 24px;
        border-left: 1px solid {Palette.BORDER};
        border-top-right-radius: 5px;
        border-bottom-right-radius: 5px;
        background: #f1f6ec;
    }}
    QDateEdit::down-arrow, QTimeEdit::down-arrow {{
        image: url(ui/assets/chevron-down.svg);
        width: 12px;
        height: 12px;
    }}

    QCalendarWidget QWidget {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
    }}
    QCalendarWidget {{
        min-width: 390px;
        min-height: 265px;
    }}
    QCalendarWidget QToolButton {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
        border: 1px solid transparent;
        border-radius: 5px;
        padding: 4px 8px;
        font-weight: 600;
    }}
    QCalendarWidget QToolButton:hover {{
        background: {Palette.PRIMARY_SOFT};
        border-color: {Palette.BORDER_STRONG};
    }}
    QCalendarWidget QSpinBox {{
        min-width: 70px;
        min-height: 24px;
        padding: 2px 22px 2px 6px;
        border: 1px solid {Palette.BORDER_STRONG};
        border-radius: 5px;
        background: {Palette.SURFACE};
    }}
    QCalendarWidget QSpinBox::up-button {{
        width: 18px;
        border-left: 1px solid {Palette.BORDER};
        border-bottom: 1px solid {Palette.BORDER};
        background: #f1f6ec;
    }}
    QCalendarWidget QSpinBox::down-button {{
        width: 18px;
        border-left: 1px solid {Palette.BORDER};
        background: #f1f6ec;
    }}
    QCalendarWidget QSpinBox::up-arrow {{
        image: url(ui/assets/chevron-up.svg);
        width: 9px;
        height: 9px;
    }}
    QCalendarWidget QSpinBox::down-arrow {{
        image: url(ui/assets/chevron-down.svg);
        width: 9px;
        height: 9px;
    }}
    QCalendarWidget QAbstractItemView {{
        background: {Palette.SURFACE};
        alternate-background-color: {Palette.SURFACE_ALT};
        selection-background-color: {Palette.SELECTION};
        selection-color: {Palette.TEXT};
        outline: 0;
        border: 1px solid {Palette.BORDER};
        font-size: 12px;
    }}

    QPushButton {{
        background: {Palette.SURFACE};
        color: {Palette.TEXT};
        border: 1px solid {Palette.BORDER_STRONG};
        border-radius: 5px;
        padding: 5px 11px;
        min-height: 26px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: {Palette.SURFACE_ALT};
        border-color: {Palette.PRIMARY};
    }}
    QPushButton:pressed {{
        background: {Palette.PRIMARY_SOFT};
    }}
    QPushButton:disabled {{
        background: #eef1ea;
        color: #8b9583;
        border-color: {Palette.BORDER};
    }}
    QPushButton[variant="primary"] {{
        background: {Palette.PRIMARY};
        color: white;
        border-color: {Palette.PRIMARY};
    }}
    QPushButton[variant="primary"]:hover {{
        background: {Palette.PRIMARY_HOVER};
        border-color: {Palette.PRIMARY_HOVER};
    }}
    QPushButton[variant="primary"]:pressed {{
        background: {Palette.PRIMARY_PRESSED};
    }}
    QPushButton[variant="danger"] {{
        color: white;
        background: {Palette.DESTRUCTIVE};
        border-color: {Palette.DESTRUCTIVE};
    }}
    QPushButton[variant="danger"]:hover {{
        background: {Palette.DESTRUCTIVE_HOVER};
        border-color: {Palette.DESTRUCTIVE_HOVER};
    }}
    QPushButton[variant="secondary"] {{
        background: #f8faf5;
    }}

    QTableView, QTableWidget {{
        background: {Palette.SURFACE};
        alternate-background-color: {Palette.SURFACE_ALT};
        border: 1px solid {Palette.BORDER};
        border-radius: 6px;
        gridline-color: #e5eadf;
        selection-background-color: {Palette.SELECTION};
        selection-color: {Palette.TEXT};
    }}
    QTableView::item, QTableWidget::item {{
        padding: 6px;
        min-height: 26px;
    }}
    QTableView::item:selected, QTableWidget::item:selected {{
        background: {Palette.SELECTION};
        color: {Palette.TEXT};
    }}
    QHeaderView::section {{
        background: #edf2e7;
        color: {Palette.TEXT};
        border: none;
        border-right: 1px solid {Palette.BORDER};
        border-bottom: 1px solid {Palette.BORDER};
        padding: 7px 8px;
        font-weight: 600;
    }}

    QScrollBar:vertical {{
        background: #eef3e8;
        width: 12px;
        margin: 2px;
        border: none;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background: {Palette.BORDER_STRONG};
        min-height: 32px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {Palette.PRIMARY};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
        border: none;
        background: transparent;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: #eef3e8;
        height: 12px;
        margin: 2px;
        border: none;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background: {Palette.BORDER_STRONG};
        min-width: 32px;
        border-radius: 5px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {Palette.PRIMARY};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
        border: none;
        background: transparent;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    QSplitter::handle {{
        background: transparent;
    }}
    QSplitter::handle:horizontal {{
        width: 8px;
        margin: 0 2px;
    }}
    QSplitter::handle:vertical {{
        height: 8px;
        margin: 2px 0;
    }}
    QSplitter::handle:hover {{
        background: {Palette.PRIMARY_SOFT};
    }}

    QGroupBox {{
        background: {Palette.SURFACE};
        border: 1px solid {Palette.BORDER};
        border-radius: 7px;
        margin-top: 12px;
        padding: 12px 10px 10px 10px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {Palette.TEXT_MUTED};
    }}

    QStatusBar {{
        background: {Palette.SURFACE};
        border-top: 1px solid {Palette.BORDER};
        color: {Palette.TEXT_MUTED};
    }}
    QLabel[role="sectionTitle"] {{
        color: {Palette.TEXT};
        font-size: 15px;
        font-weight: 700;
    }}
    QLabel[role="muted"] {{
        color: {Palette.TEXT_MUTED};
    }}
    QWidget[role="panel"] {{
        background: {Palette.SURFACE};
        border: 1px solid {Palette.BORDER};
        border-radius: 7px;
    }}
    """


def apply_app_theme(app: QApplication) -> None:
    app.setStyleSheet(app_stylesheet())


def set_button_variant(button: QPushButton, variant: str = "secondary") -> QPushButton:
    button.setProperty("variant", variant)
    button.style().unpolish(button)
    button.style().polish(button)
    return button


def set_button_icon(button: QPushButton, icon_path: str, size: int = 16) -> QPushButton:
    button.setIcon(QIcon(icon_path))
    button.setIconSize(QSize(size, size))
    return button


def mark_panel(widget: QWidget) -> QWidget:
    widget.setProperty("role", "panel")
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


def fit_combo_popup_to_contents(combo: QComboBox, minimum: int = 260, maximum: int = 520) -> None:
    metrics = combo.fontMetrics()
    widest = minimum
    for index in range(combo.count()):
        widest = max(widest, metrics.horizontalAdvance(combo.itemText(index)) + 58)
    combo.view().setMinimumWidth(min(widest, maximum))
