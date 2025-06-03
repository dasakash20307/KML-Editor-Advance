# File: dasakash20307/kml-editor-advance/KML-Editor-Advance-5-PH4-Enhanced_Features_UI_Refinements/ui/widgets/kml_editor_view_widget.py
# ----------------------------------------------------------------------
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QFormLayout, QLabel
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage # Make sure QWebEngineSettings is imported
from PySide6.QtCore import QUrl, Slot, QObject, Signal
from PySide6.QtWebChannel import QWebChannel

# Helper class for Python-JavaScript communication
class KMLJSBridge(QObject):
    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self._parent_widget = parent_widget

    @Slot(str)
    def jsLogMessage(self, message: str):
        if hasattr(self._parent_widget, 'log_message_callback') and callable(self._parent_widget.log_message_callback):
            self._parent_widget.log_message_callback(f"JS Log: {message}", "info_js")
        else:
            print(f"JS Log (via Bridge): {message}")


class KMLEditorViewWidget(QWidget):
    save_triggered_signal = Signal()

    def __init__(self, parent=None, log_message_callback=None):
        super().__init__(parent)

        self.log_message_callback = log_message_callback if log_message_callback else self._default_log

        self.web_view = QWebEngineView()
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # --- ADD THIS LINE ---
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        # --- For further debugging, you might also try (with caution): ---
        # settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True) # If there were mixed content issues (less likely for Esri HTTPS)
        # settings.setAttribute(QWebEngineSettings.WebAttribute.AutoLoadImages, True) # Should be true by default

        # UI Elements for KML Editing
        self.placemark_name_edit = QLineEdit()
        self.placemark_name_edit.setPlaceholderText("Placemark Name (UUID or custom)")
        self.placemark_name_edit.setReadOnly(True)

        self.placemark_description_edit = QTextEdit()
        self.placemark_description_edit.setPlaceholderText("Placemark Description")
        self.placemark_description_edit.setReadOnly(True)
        self.placemark_description_edit.setFixedHeight(100)

        self.edit_kml_button = QPushButton("Edit KML Geometry")
        self.save_changes_button = QPushButton("Save Changes")
        self.cancel_edit_button = QPushButton("Cancel Edit")

        self.save_changes_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.addWidget(self.web_view, 1)

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Name:"), self.placemark_name_edit)
        form_layout.addRow(QLabel("Description:"), self.placemark_description_edit)
        main_layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.edit_kml_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_changes_button)
        button_layout.addWidget(self.cancel_edit_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        self.py_bridge = KMLJSBridge(self)
        self.web_channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("kml_editor_bridge", self.py_bridge)

        base_path = os.path.dirname(os.path.abspath(__file__))
        html_file_path = os.path.join(base_path, "..", "web_content", "kml_editor", "kml_editor.html")

        if not os.path.exists(html_file_path):
            self.log_message_callback(f"CRITICAL: HTML file for KML Editor not found at: {html_file_path}", "error")
            self.web_view.setHtml("<html><body><h1>Error: KML Editor HTML not found.</h1><p>Please check installation.</p></body></html>")
        else:
            self.web_view.setUrl(QUrl.fromLocalFile(html_file_path))

        self.original_kml_content = None
        self.current_placemark_name_original = ""
        self.current_placemark_description_original = ""

        self.edit_kml_button.clicked.connect(self.enter_edit_mode)
        self.save_changes_button.clicked.connect(self._handle_save_changes)
        self.cancel_edit_button.clicked.connect(self._handle_cancel_edit)

        self.placemark_name_edit.setText("N/A")
        self.placemark_description_edit.setText("No KML loaded. Load a KML file to see details and map.")

    def _default_log(self, message, level="info"):
        print(f"KMLEditorViewWidget_LOG [{level.upper()}]: {message}")

    def load_kml_to_map_via_js(self, kml_content: str):
        if not kml_content:
            self.log_message_callback("load_kml_to_map_via_js: KML content is empty.", "warning")
            return
        try:
            js_command = f"loadKmlToMap({json.dumps(kml_content)});"
            self.web_view.page().runJavaScript(js_command)
            self.log_message_callback(f"Sent KML content to JS for loading. Length: {len(kml_content)}", "debug")
        except Exception as e:
            self.log_message_callback(f"Error sending KML to JS: {e}", "error")

    def enable_editing_via_js(self):
        self.web_view.page().runJavaScript("enableMapEditing();")
        self.log_message_callback("Sent command to JS: enableMapEditing()", "debug")

    def disable_editing_via_js(self):
        self.web_view.page().runJavaScript("disableMapEditing();")
        self.log_message_callback("Sent command to JS: disableMapEditing()", "debug")

    def get_edited_data_from_js(self, result_callback: callable):
        self.log_message_callback("Requesting edited geometry from JS...", "debug")
        self.web_view.page().runJavaScript("getEditedGeometry();", result_callback)

    def enter_edit_mode(self):
        if self.original_kml_content is None:
            self.log_message_callback("Cannot enter edit mode: No KML loaded.", "warning")
            return

        self.enable_editing_via_js()
        self.edit_kml_button.setVisible(False)
        self.save_changes_button.setVisible(True)
        self.cancel_edit_button.setVisible(True)
        self.placemark_name_edit.setReadOnly(False)
        self.placemark_description_edit.setReadOnly(False)
        self.log_message_callback("Entered KML edit mode.", "info")

    def exit_edit_mode(self, reload_original_kml: bool = False):
        self.disable_editing_via_js()
        self.edit_kml_button.setVisible(True)
        self.save_changes_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        self.placemark_name_edit.setReadOnly(True)
        self.placemark_description_edit.setReadOnly(True)

        if reload_original_kml and self.original_kml_content is not None:
            self.placemark_name_edit.setText(self.current_placemark_name_original)
            self.placemark_description_edit.setText(self.current_placemark_description_original)
            self.load_kml_to_map_via_js(self.original_kml_content)
            self.log_message_callback("Exited edit mode, original KML reloaded.", "info")
        else:
            self.log_message_callback("Exited edit mode.", "info")

    def _handle_save_changes(self):
        self.log_message_callback("KMLEditorViewWidget: Save Changes button clicked. Emitting signal.", "info")
        self.save_triggered_signal.emit()

    def _handle_cancel_edit(self):
        self.log_message_callback("Cancel Edit clicked.", "info")
        self.exit_edit_mode(reload_original_kml=True)

    def display_kml(self, kml_file_content: str, placemark_name: str, placemark_description: str):
        if not kml_file_content:
            self.log_message_callback("display_kml: KML content is empty. Clearing map.", "warning")
            self.clear_map()
            return

        self.original_kml_content = kml_file_content
        self.current_placemark_name_original = placemark_name
        self.current_placemark_description_original = placemark_description

        self.placemark_name_edit.setText(placemark_name)
        self.placemark_description_edit.setText(placemark_description)

        self.load_kml_to_map_via_js(kml_file_content)
        self.exit_edit_mode()
        self.log_message_callback(f"Displayed KML for placemark: {placemark_name}", "info")
        self.edit_kml_button.setEnabled(True)

    def clear_map(self):
        self.original_kml_content = None
        self.current_placemark_name_original = ""
        self.current_placemark_description_original = ""

        self.placemark_name_edit.clear()
        self.placemark_name_edit.setText("N/A")
        self.placemark_description_edit.clear()
        self.placemark_description_edit.setText("Map cleared. No KML loaded.")

        self.web_view.page().runJavaScript("if (typeof clearMap === 'function') { clearMap(); } else { console.warn('JS function clearMap not defined.'); }")

        self.exit_edit_mode()
        self.edit_kml_button.setEnabled(False)
        self.log_message_callback("Map and KML data cleared.", "info")

    def cleanup(self):
        self.log_message_callback("KMLEditorViewWidget cleanup initiated.", "debug")
        if self.web_view and self.web_view.page():
            self.web_view.stop()

# (Rest of the file, including the if __name__ == '__main__': block, remains the same)
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    def test_logger(message, level="info"):
        print(f"TEST_APP_LOG [{level.upper()}]: {message}")

    editor_widget = KMLEditorViewWidget(log_message_callback=test_logger)
    editor_widget.setWindowTitle("KML Editor View - Standalone Test")
    editor_widget.setGeometry(100, 100, 800, 700)
    editor_widget.show()

    dummy_kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>Test Placemark from Python</name>
    <description>This is a test description loaded from Python code.</description>
    <Polygon>
      <outerBoundaryIs>
        <LinearRing>
          <coordinates>
            -77.05678,38.87191,100 -77.05265,38.87000,100 -77.05231,38.87073,100 -77.05704,38.87211,100 -77.05678,38.87191,100
          </coordinates>
        </LinearRing>
      </outerBoundaryIs>
    </Polygon>
  </Placemark>
</kml>"""
    placemark_name_test = "Test Placemark from Python"
    placemark_desc_test = "This is a test description loaded from Python code. It might contain special characters like < & > and \"quotes\"."

    def on_load_finished(success):
        if success:
            test_logger("Web view page loaded successfully.", "info")
            editor_widget.display_kml(dummy_kml_content, placemark_name_test, placemark_desc_test)
        else:
            test_logger("Web view page failed to load.", "error")

    if editor_widget.web_view.page():
        editor_widget.web_view.page().loadFinished.connect(on_load_finished)
    else:
        test_logger("Web view page is None, cannot connect loadFinished signal.", "error")

    sys.exit(app.exec())