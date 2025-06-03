# File: DilasaKMLTool_v4/ui/widgets/google_earth_webview_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QApplication, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings # Corrected import
from PySide6.QtCore import QUrl, Slot, Qt # Added Qt import here
from PySide6.QtGui import QGuiApplication # Added for clipboard
import os
import shutil
import tempfile

class GoogleEarthWebViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()
        self.temp_dir = tempfile.mkdtemp(prefix="kml_editor_ge_")
        self.current_temp_file = None

        # Configure WebEngineSettings if necessary
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        self.setLayout(layout)

        # Load Google Earth Web
        self.web_view.setUrl(QUrl("https://earth.google.com/web/"))

    def display_kml_and_show_instructions(self, kml_file_path: str, kml_file_name: str):
        """
        Copies the KML file to a temporary location and copies its path to clipboard.
        Returns True if successful, False otherwise.
        """
        if not kml_file_path or not kml_file_name:
            QMessageBox.warning(self, "KML Error", "Cannot process KML: File path or name is missing.")
            return False

        try:
            # Create temp file path
            temp_kml_path = os.path.join(self.temp_dir, kml_file_name)
            
            # Clean up previous temp file if it exists
            if self.current_temp_file and os.path.exists(self.current_temp_file):
                try:
                    os.remove(self.current_temp_file)
                except Exception:
                    pass  # Ignore cleanup errors
            
            # Copy the file to temp location
            shutil.copy2(kml_file_path, temp_kml_path)
            self.current_temp_file = temp_kml_path
            
            # Convert to Windows path format
            windows_path = temp_kml_path.replace('/', '\\')
            
            # Copy to clipboard
            QGuiApplication.clipboard().setText(windows_path)
            return True

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not copy KML to temporary location: {e}")
            return False

    def set_focus_on_webview(self):
        self.web_view.setFocus(Qt.FocusReason.OtherFocusReason)

    def get_web_view(self):
        return self.web_view

    def clear_view(self):
        self.web_view.setUrl(QUrl("https://earth.google.com/web/"))

    def cleanup(self):
        """Clean up temporary files and directory"""
        try:
            if self.current_temp_file and os.path.exists(self.current_temp_file):
                os.remove(self.current_temp_file)
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

class GoogleEarthViewWidget(QWidget):
    def __init__(self, parent=None, log_message_callback=None):
        super().__init__(parent)
        self.log_message_callback = log_message_callback if log_message_callback else print
        self.temp_dir = tempfile.mkdtemp(prefix="kml_editor_ge_")
        self.current_temp_file = None
        
        # Setup UI
        layout = QVBoxLayout()
        self.info_label = QLabel("Select a KML file to copy its path for Google Earth Pro.")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        self.setLayout(layout)

    def process_kml_for_google_earth(self, original_kml_path):
        """Process KML file for Google Earth viewing"""
        try:
            # Create a copy in temp directory
            kml_filename = os.path.basename(original_kml_path)
            temp_kml_path = os.path.join(self.temp_dir, kml_filename)
            
            # Copy the file
            shutil.copy2(original_kml_path, temp_kml_path)
            self.current_temp_file = temp_kml_path
            
            # Convert path to Windows format
            windows_path = temp_kml_path.replace('/', '\\')
            
            # Copy to clipboard
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(windows_path)
            
            # Update info label
            self.info_label.setText(
                f"KML file path copied to clipboard.\n"
                f"Open Google Earth Pro and use 'File > Open' to view the KML.\n"
                f"Path: {windows_path}"
            )
            
            self.log_message_callback(f"KML prepared for Google Earth: {windows_path}", "info")
            return True
            
        except Exception as e:
            self.log_message_callback(f"Error preparing KML for Google Earth: {str(e)}", "error")
            self.info_label.setText("Error preparing KML file. Please try again.")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if self.current_temp_file and os.path.exists(self.current_temp_file):
                os.remove(self.current_temp_file)
            if os.path.exists(self.temp_dir):
                os.rmdir(self.temp_dir)
        except Exception as e:
            self.log_message_callback(f"Error cleaning up temp files: {str(e)}", "warning")

if __name__ == '__main__':
    # This part is for basic testing if you run this file directly
    # It won't be used when MainWindow imports the widget
    import sys
    from PySide6.QtWidgets import QApplication
    # Qt is already imported at the top level, so no need for a separate import here for the test.
    # from PySide6.QtCore import Qt 

    app = QApplication(sys.argv) # QApplication instance needed for QWebEngineView
    widget = GoogleEarthWebViewWidget()
    widget.setWindowTitle("Google Earth Web View Test")
    widget.setGeometry(100, 100, 800, 600)
    widget.show()
    
    # Example of calling set_focus_on_webview (though focus might be immediate on show)
    # from PySide6.QtCore import QTimer # Requires QTimer import
    # QTimer.singleShot(1000, widget.set_focus_on_webview) 

    sys.exit(app.exec())
