"""
PyXcel — AI-Powered Spreadsheet System
Entry point: launches the PySide6 desktop application.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

from gui.main_window import MainWindow


def main():
    
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PyXcel")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("KiTE Development Team")

    
    qss_path = os.path.join(
        os.path.dirname(__file__), "gui", "styles.qss"
    )
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())

    
    from core.ollama_client import is_ollama_running, is_model_available
    from PySide6.QtWidgets import QMessageBox

    if not is_ollama_running():
        msg = QMessageBox()
        msg.setWindowTitle("Ollama Not Running")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "Ollama is not running!\n\n"
            "Please start Ollama first:\n"
            "  • Double-click start_pyxcel.bat\n"
            "  • OR run: ollama serve\n\n"
            "PyXcel will open but AI features will be disabled."
        )
        msg.exec()

    elif not is_model_available("llama3.1"):
        msg = QMessageBox()
        msg.setWindowTitle("LLaMA Model Not Found")
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "LLaMA model not found!\n\n"
            "Please pull it first (one-time, needs internet):\n"
            "  ollama pull llama3.1\n\n"
            "PyXcel will open but AI features will be disabled."
        )
        msg.exec()

    # Launch main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()