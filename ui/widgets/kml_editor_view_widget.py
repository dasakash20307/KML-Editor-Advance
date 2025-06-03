# File: DilasaKMLTool_v4/ui/widgets/kml_editor_view_widget.py
# ----------------------------------------------------------------------
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QPushButton,
    QFormLayout, QLabel
)
from PySide6.QtWebEngineWidgets import QWebEngineView
# At the top of the file
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PySide6.QtCore import QUrl, Slot, QObject, Signal # Added QObject, Signal
from PySide6.QtWebChannel import QWebChannel

# Helper class for Python-JavaScript communication
class KMLJSBridge(QObject):
    # Define signals that can be emitted from Python and listened to in JS if needed
    # For now, direct JS calls are made, so signals might not be immediately necessary.
    # Example: kmlDataLoaded = Signal(str)

    def __init__(self, parent_widget): # parent_widget is KMLEditorViewWidget
        super().__init__(parent_widget) # Pass parent_widget to QObject constructor
        self._parent_widget = parent_widget

    @Slot(str) # Add this decorator
    def jsLogMessage(self, message: str): # Add this method
        print(f"JS Log (via Bridge): {message}") # Add a direct print for ensured visibility in sandbox
        if hasattr(self._parent_widget, 'log_message_callback') and callable(self._parent_widget.log_message_callback):
            self._parent_widget.log_message_callback(f"JS Log: {message}", "info_js") # Use a distinct level if desired
        # else:
            # The print above handles the case where the callback might not be set or callable.
            # print(f"JS Log (via Bridge fallback): {message}")


class KMLEditorViewWidget(QWidget):
    save_triggered_signal = Signal() # Signal to notify MainWindow to handle save

    def __init__(self, parent=None, log_message_callback=None):
        super().__init__(parent)

        self.log_message_callback = log_message_callback if log_message_callback else self._default_log

        self.web_view = QWebEngineView()

        # Set a custom User-Agent
        # Get the default profile of the page
        profile = self.web_view.page().profile()
        # If no specific profile is set on the page, QWebEngineProfile.defaultProfile() could also be used
        # but page().profile() is more direct if a page already exists.
        # If there's a concern about shared profiles, a new QWebEngineProfile could be created and set.

        custom_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
        profile.setHttpUserAgent(custom_user_agent)
        self.log_message_callback(f"Set custom User-Agent to: {custom_user_agent}", "debug")

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        # For development, enabling remote debugging can be helpful:
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9223" # Choose an unused port
        # settings.setAttribute(QWebEngineSettings.WebAttribute.DevToolsEnabled, True) # Not a standard attribute

        # UI Elements for KML Editing
        self.placemark_name_edit = QLineEdit()
        self.placemark_name_edit.setPlaceholderText("Placemark Name (UUID or custom)")
        self.placemark_name_edit.setReadOnly(True)

        self.placemark_description_edit = QTextEdit() # Renamed from self.description_edit
        self.placemark_description_edit.setPlaceholderText("Placemark Description")
        self.placemark_description_edit.setReadOnly(True)
        self.placemark_description_edit.setFixedHeight(100) # Keep fixed height or make dynamic

        self.edit_kml_button = QPushButton("Edit KML Geometry")
        self.save_changes_button = QPushButton("Save Changes")
        self.cancel_edit_button = QPushButton("Cancel Edit")

        self.save_changes_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)

        # Layout Setup
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5) # Adjusted margins

        # Web View takes most space
        main_layout.addWidget(self.web_view, 1) # Add stretch factor

        # Form for Name and Description
        form_layout = QFormLayout()
        form_layout.addRow(QLabel("Name:"), self.placemark_name_edit)
        form_layout.addRow(QLabel("Description:"), self.placemark_description_edit)
        main_layout.addLayout(form_layout)

        # Horizontal layout for buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.edit_kml_button)
        button_layout.addStretch() # Pushes buttons apart or to sides if more are added
        button_layout.addWidget(self.save_changes_button)
        button_layout.addWidget(self.cancel_edit_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

        # QWebChannel Setup
        self.py_bridge = KMLJSBridge(self) # Pass self (KMLEditorViewWidget instance)
        self.web_channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.web_channel)
        self.web_channel.registerObject("kml_editor_bridge", self.py_bridge)

        # Load the KML editor HTML page
        # Construct absolute path to HTML file
        base_path = os.path.dirname(os.path.abspath(__file__))
        # Path relative to this file: ../web_content/kml_editor/kml_editor.html
        html_file_path = os.path.join(base_path, "..", "web_content", "kml_editor", "kml_editor.html")

        if not os.path.exists(html_file_path):
            self.log_message_callback(f"CRITICAL: HTML file for KML Editor not found at: {html_file_path}", "error")
            self.web_view.setHtml("<html><body><h1>Error: KML Editor HTML not found.</h1><p>Please check installation.</p></body></html>")
        else:
            self.web_view.setUrl(QUrl.fromLocalFile(html_file_path))

        # Internal state for KML data
        self.original_kml_content = None
        self.current_placemark_name_original = ""
        self.current_placemark_description_original = ""

        # Connect button signals
        self.edit_kml_button.clicked.connect(self.enter_edit_mode)
        self.save_changes_button.clicked.connect(self._handle_save_changes)
        self.cancel_edit_button.clicked.connect(self._handle_cancel_edit)

        # Initial state
        self.placemark_name_edit.setText("N/A")
        self.placemark_description_edit.setText("No KML loaded. Load a KML file to see details and map.")


    def _default_log(self, message, level="info"):
        # This ensures messages are printed to stdout, which is crucial for sandbox environments
        print(f"KMLEditorViewWidget_LOG [{level.upper()}]: {message}")

    # --- Methods to Interact with JavaScript ---
    def load_kml_to_map_via_js(self, kml_content: str):
        """Sends KML content to JavaScript to be loaded on the map."""
        if not kml_content:
            self.log_message_callback("load_kml_to_map_via_js: KML content is empty.", "warning")
            return
        try:
            # Ensure kml_content is properly escaped for JS string
            js_command = f"loadKmlToMap({json.dumps(kml_content)});"
            self.web_view.page().runJavaScript(js_command)
            self.log_message_callback(f"Sent KML content to JS for loading. Length: {len(kml_content)}", "debug")
        except Exception as e:
            self.log_message_callback(f"Error sending KML to JS: {e}", "error")

    def enable_editing_via_js(self):
        """Instructs the JavaScript map to enable editing tools."""
        self.web_view.page().runJavaScript("enableMapEditing();")
        self.log_message_callback("Sent command to JS: enableMapEditing()", "debug")

    def disable_editing_via_js(self):
        """Instructs the JavaScript map to disable editing tools."""
        self.web_view.page().runJavaScript("disableMapEditing();")
        self.log_message_callback("Sent command to JS: disableMapEditing()", "debug")

    def get_edited_data_from_js(self, result_callback: callable):
        """
        Requests the edited geometry from JavaScript.
        The result_callback will be called with the JSON string from JS.
        """
        self.log_message_callback("Requesting edited geometry from JS...", "debug")
        self.web_view.page().runJavaScript("getEditedGeometry();", result_callback)

    # --- Manage Edit Mode and UI State ---
    def enter_edit_mode(self):
        if self.original_kml_content is None:
            self.log_message_callback("Cannot enter edit mode: No KML loaded.", "warning")
            # Optionally show a QMessageBox to the user
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
            # If not reloading, the current edits in text fields remain, but map editing is off.

    def _handle_save_changes(self):
        self.log_message_callback("KMLEditorViewWidget: Save Changes button clicked. Emitting signal.", "info")
        # Emit a signal to MainWindow to handle the actual save logic.
        # MainWindow will then call get_edited_data_from_js, then call KMLHandler.
        self.save_triggered_signal.emit()
        # Do not call exit_edit_mode() here. MainWindow will manage it after save attempt.

    def _handle_cancel_edit(self):
        self.log_message_callback("Cancel Edit clicked.", "info")
        self.exit_edit_mode(reload_original_kml=True)

    # --- KML Data Display and Clearing ---
    def display_kml(self, kml_file_content: str, placemark_name: str, placemark_description: str):
        """
        Loads and displays KML content on the map and in the info fields.
        """
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
        self.exit_edit_mode() # Ensure it starts/resets to non-edit mode
        self.log_message_callback(f"Displayed KML for placemark: {placemark_name}", "info")
        self.edit_kml_button.setEnabled(True)


    def clear_map(self):
        """Clears the map and resets KML data fields."""
        self.original_kml_content = None
        self.current_placemark_name_original = ""
        self.current_placemark_description_original = ""

        self.placemark_name_edit.clear()
        self.placemark_name_edit.setText("N/A")
        self.placemark_description_edit.clear()
        self.placemark_description_edit.setText("Map cleared. No KML loaded.")

        # Call JS function to clear map features
        self.web_view.page().runJavaScript("if (typeof clearMap === 'function') { clearMap(); } else { console.warn('JS function clearMap not defined.'); }")

        self.exit_edit_mode() # Ensure UI is in non-edit state
        self.edit_kml_button.setEnabled(False) # Disable edit until KML is loaded
        self.log_message_callback("Map and KML data cleared.", "info")

    def cleanup(self):
        """Clean up resources, like stopping the web page if necessary."""
        self.log_message_callback("KMLEditorViewWidget cleanup initiated.", "debug")
        # QWebEngineView's page might hold resources. Clearing or stopping might be good.
        if self.web_view and self.web_view.page():
            # self.web_view.page().setWebChannel(None) # Deregister channel
            # self.web_channel.deregisterObject("kml_editor_bridge") # Not strictly needed if page is destroyed
            self.web_view.stop() # Stop any loading
            # self.web_view.setHtml("") # Clear content - might be too aggressive if widget is reused
        # Note: QWebChannel and KMLJSBridge are QObjects with this widget as parent,
        # so they should be cleaned up by Qt's parent-child mechanism.

# Example usage (if testing this widget standalone)
if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Dummy log function for standalone testing
    def test_logger(message, level="info"):
        print(f"TEST_APP_LOG [{level.upper()}]: {message}")

    editor_widget = KMLEditorViewWidget(log_message_callback=test_logger)
    editor_widget.setWindowTitle("KML Editor View - Standalone Test")
    editor_widget.setGeometry(100, 100, 800, 700) # x, y, width, height
    editor_widget.show()

    # --- Test Scenarios ---
    # 1. Initial state (should show "No KML loaded")
    editor_widget.clear_map() # Call to ensure initial state is clean

    # 2. Load some dummy KML data after a delay (to simulate async loading or user action)
    #    (Requires a running web server or correctly pathed local file for OpenLayers to fully init)
    #    For now, we assume kml_editor.html itself initializes the map structure.

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

    # Simulate loading KML after web view is ready (e.g., via a button in a real app)
    # For QWebEngineView, page().loadFinished signal can be used.
    def on_load_finished(success):
        if success:
            test_logger("Web view page loaded successfully.", "info")
            editor_widget.display_kml(dummy_kml_content, placemark_name_test, placemark_desc_test)

            # Test entering edit mode
            # editor_widget.enter_edit_mode() # This would typically be user-triggered
        else:
            test_logger("Web view page failed to load.", "error")

    if editor_widget.web_view.page(): # page() might return None if init failed badly
        editor_widget.web_view.page().loadFinished.connect(on_load_finished)
    else:
        test_logger("Web view page is None, cannot connect loadFinished signal.", "error")


    sys.exit(app.exec())
