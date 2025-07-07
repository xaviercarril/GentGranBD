import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from database import engine
from models import Base

def main():
    Base.metadata.create_all(bind=engine)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()