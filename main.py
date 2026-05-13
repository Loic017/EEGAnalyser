import sys
from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg
from src.ui.main_window import MainWindow

# Global performance optimizations for pyqtgraph
pg.setConfigOptions(antialias=False)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()