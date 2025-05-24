import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton
import os # Required for the new __main__ check

class HistoricalMapBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historical Imagery Cache Builder")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Placeholder label
        label = QLabel("Historical imagery builder UI will go here")
        layout.addWidget(label)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept) # Or self.reject or self.close
        layout.addWidget(close_button)

        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    dialog = HistoricalMapBuilderDialog()
    dialog.show() 

    # Ensure the application event loop runs if we created the app instance here
    # and this script is being run directly.
    if app is QApplication.instance() and (not hasattr(sys, 'frozen') and sys.argv[0] == __file__ or hasattr(sys, 'frozen') and os.path.basename(sys.executable) == os.path.basename(__file__)):
        sys.exit(app.exec())
