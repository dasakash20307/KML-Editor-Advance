import sys
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPushButton

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
        close_button.clicked.connect(self.accept) # Or self.reject or self.close depending on desired behavior
        layout.addWidget(close_button)

        self.setLayout(layout)

if __name__ == '__main__':
    # Check if a QApplication instance already exists, if not create one
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    dialog = HistoricalMapBuilderDialog()
    dialog.show() # Use show() for modeless dialog for testing, or exec() for modal

    # Ensure the application event loop runs if we created the app instance here
    if not QApplication.instance(): # This check might be redundant if app was created above
        sys.exit(app.exec())
    elif app is QApplication.instance() and sys.argv[0] in __file__:
        # If we are running this script directly and created the app, start the event loop.
        # This is a common pattern for testing dialogs.
        sys.exit(app.exec())
