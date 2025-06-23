# File: dasakash20307/kml-editor-advance/KML-Editor-Advance-5-PH4-Enhanced_Features_UI_Refinements/ui/widgets/kml_editor_view_widget.py
# ----------------------------------------------------------------------
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QFormLayout, QLabel, QComboBox, QGroupBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage # Make sure QWebEngineSettings is imported
from PySide6.QtCore import QUrl, Slot, QObject, Signal
from PySide6.QtWebChannel import QWebChannel
from core.utils import resource_path  # Add this import

# Helper class for Python-JavaScript communication
class KMLJSBridge(QObject):
    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self._parent_widget = parent_widget

    @Slot(str)
    def jsLogMessage(self, message: str):
        if "Map initialized successfully" in message:
            self._parent_widget.map_initialized = True
            if self._parent_widget.pending_kml_content:
                self._parent_widget.display_kml(
                    self._parent_widget.pending_kml_content,
                    self._parent_widget.pending_placemark_name,
                    self._parent_widget.pending_placemark_description
                )
                self._parent_widget.pending_kml_content = None
                self._parent_widget.pending_placemark_name = None
                self._parent_widget.pending_placemark_description = None
        if hasattr(self._parent_widget, 'log_message_callback') and callable(self._parent_widget.log_message_callback):
            self._parent_widget.log_message_callback(f"JS Log: {message}", "info_js")
        else:
            print(f"JS Log (via Bridge): {message}")


class KMLEditorViewWidget(QWidget):
    save_triggered_signal = Signal(dict)

    def __init__(self, parent=None, log_message_callback=None):
        super().__init__(parent)
        self.log_message_callback = log_message_callback if log_message_callback else self._default_log
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        
        # Initialize instance variables
        self.original_kml_content = None
        self.pending_kml_content = None
        self.current_placemark_name = None
        self.current_placemark_description = None
        self.credential_manager = None
        self.is_editing = False
        
        # Create UI elements
        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.edit_button = QPushButton("Edit KML")
        self.save_button = QPushButton("Save Changes")
        self.cancel_button = QPushButton("Cancel Edit")
        self.base_layer_combo = QComboBox()
        
        # Setup UI
        self._setup_ui()
        self._setup_connections()
        self._load_html()

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        
        # Map view
        main_layout.addWidget(self.web_view, stretch=1)
        
        # Controls panel
        controls_group = QGroupBox("KML Editor Controls")
        controls_layout = QFormLayout()
        
        # Base layer selection
        self.base_layer_combo.addItems(["Esri", "OpenStreetMap"])
        controls_layout.addRow("Base Layer:", self.base_layer_combo)
        
        # Name and description inputs
        controls_layout.addRow("Name:", self.name_input)
        controls_layout.addRow("Description:", self.description_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        controls_layout.addRow("Actions:", button_layout)
        
        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)
        
        # Initial button states
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        self.setLayout(main_layout)

    def _setup_connections(self):
        # Button connections
        self.edit_button.clicked.connect(self.enter_edit_mode)
        self.save_button.clicked.connect(self._handle_save_changes)
        self.cancel_button.clicked.connect(self._handle_cancel_edit)
        
        # Base layer selection
        self.base_layer_combo.currentTextChanged.connect(self._switch_base_map_layer_js)
        
        # Web view setup
        self.web_view.loadFinished.connect(self.on_load_finished)
        
        # Create channel
        self.channel = QWebChannel()
        self.js_bridge = KMLJSBridge(self)
        self.channel.registerObject("kml_editor_bridge", self.js_bridge)
        self.web_view.page().setWebChannel(self.channel)

    def _load_html(self):
        html_path = resource_path("ui/web_content/kml_editor/kml_editor.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))

    def display_kml(self, kml_file_content: str, placemark_name: str, placemark_description: str):
        """Display KML content and associated metadata"""
        self.original_kml_content = kml_file_content
        self.current_placemark_name = placemark_name
        self.current_placemark_description = placemark_description
        
        # Update UI
        self.name_input.setText(placemark_name)
        self.description_input.setText(placemark_description)
        self.name_input.setReadOnly(True)
        self.description_input.setReadOnly(True)
        
        # Load KML to map
        self.load_kml_to_map_via_js(kml_file_content)
        
        # Reset edit state
        self.is_editing = False
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.edit_button.setEnabled(True)

    def enter_edit_mode(self):
        """Enable editing mode"""
        if self.original_kml_content is None:
            self.log_message_callback("No KML content loaded to edit", "warning")
            return
        
        self.is_editing = True
        self.name_input.setReadOnly(False)
        self.description_input.setReadOnly(False)
        self.save_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.edit_button.setEnabled(False)
        
        # Enable map editing
        self.enable_editing_via_js()

    def exit_edit_mode(self, reload_original_kml: bool = False):
        """Disable editing mode"""
        self.is_editing = False
        self.name_input.setReadOnly(True)
        self.description_input.setReadOnly(True)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.edit_button.setEnabled(True)
        
        # Disable map editing
        self.disable_editing_via_js()
        
        if reload_original_kml and self.original_kml_content:
            self.load_kml_to_map_via_js(self.original_kml_content)

    def _handle_save_changes(self):
        """Handle save button click"""
        def handle_geometry_result(geometry_data):
            try:
                # Create the data dictionary
                save_data = {
                    'geometry': geometry_data,
                    'name': self.name_input.text(),
                    'description': self.description_input.toPlainText()
                }
                # Emit save signal with the data dictionary
                self.save_triggered_signal.emit(save_data)
                self.exit_edit_mode()
            except Exception as e:
                self.log_message_callback(f"Error saving changes: {str(e)}", "error")
        
        # Get edited geometry from JavaScript
        self.get_edited_data_from_js(handle_geometry_result)

    def _handle_cancel_edit(self):
        """Handle cancel button click"""
        self.name_input.setText(self.current_placemark_name)
        self.description_input.setText(self.current_placemark_description)
        self.exit_edit_mode(reload_original_kml=True)

    # JavaScript interface methods
    def load_kml_to_map_via_js(self, kml_content: str):
        """Load KML content to the map"""
        script = f'loadKmlToMap(`{kml_content}`);'
        self.web_view.page().runJavaScript(script)

    def enable_editing_via_js(self):
        """Enable map editing mode"""
        self.web_view.page().runJavaScript('enableMapEditing();')

    def disable_editing_via_js(self):
        """Disable map editing mode"""
        self.web_view.page().runJavaScript('disableMapEditing();')

    def get_edited_data_from_js(self, result_callback: callable):
        """Get edited geometry data from JavaScript"""
        self.web_view.page().runJavaScript('getEditedGeometry();', result_callback)

    def _switch_base_map_layer_js(self, layer_name: str):
        """Switch the base map layer"""
        self.web_view.page().runJavaScript(f'switchBaseLayer("{layer_name}");')

    def set_credential_manager(self, credential_manager):
        """Set the credential manager instance"""
        self.credential_manager = credential_manager
        self._apply_default_map_view_settings()

    def _apply_default_map_view_settings(self):
        """Apply default map view settings from credential manager"""
        if self.credential_manager:
            try:
                settings = {
                    'kmlFillColor': self.credential_manager.get_kml_fill_color(),
                    'kmlStrokeColor': self.credential_manager.get_kml_stroke_color(),
                    'kmlStrokeWidth': self.credential_manager.get_kml_stroke_width(),
                    'maxZoom': self.credential_manager.get_max_zoom(),
                    'initialZoom': self.credential_manager.get_initial_zoom()
                }
                script = f'setMapDisplaySettings({json.dumps(settings)});'
                self.web_view.page().runJavaScript(script)
            except Exception as e:
                self.log_message_callback(f"Error applying map settings: {str(e)}", "warning")

    def _default_log(self, message, level="info"):
        """Default logging function if none provided"""
        print(f"[{level.upper()}] KMLEditorView: {message}")

    def cleanup(self):
        """Cleanup resources"""
        if self.web_view:
            self.web_view.setUrl(QUrl('about:blank'))
            self.web_view.deleteLater()

    def on_load_finished(self, success):
        """Handle the web view load finished event."""
        if success:
            self.log_message_callback("Web view page loaded successfully.", "info")
            if hasattr(self, 'original_kml_content') and self.original_kml_content:
                self.load_kml_to_map_via_js(self.original_kml_content)
        else:
            self.log_message_callback("Web view page failed to load.", "error")

    def clear_map(self):
        """Clear the KML content from the map view"""
        self.original_kml_content = None
        self.current_placemark_name = None
        self.current_placemark_description = None
        
        # Clear UI elements
        self.name_input.clear()
        self.name_input.setReadOnly(True)
        self.description_input.clear()
        self.description_input.setReadOnly(True)
        
        # Reset buttons
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        
        # Clear map via JavaScript
        self.web_view.page().runJavaScript('clearMap();')
        
        # Reset edit state
        self.is_editing = False

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

    if editor_widget.web_view.page():
        editor_widget.web_view.page().loadFinished.connect(editor_widget.on_load_finished)
    else:
        test_logger("Web view page is None, cannot connect loadFinished signal.", "error")

    sys.exit(app.exec())
