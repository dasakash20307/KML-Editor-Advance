# File: DilasaKMLTool_v4/ui/dialogs/default_view_settings_dialog.py
# ----------------------------------------------------------------------

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QPushButton, QColorDialog,
    QSlider, QSpinBox, QComboBox, QDialogButtonBox, QHBoxLayout, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

from core.credential_manager import CredentialManager

class DefaultViewSettingsDialog(QDialog):
    def __init__(self, credential_manager: CredentialManager, parent=None):
        super().__init__(parent)
        self.credential_manager = credential_manager
        self.setWindowTitle("Default KML View Settings")
        self.setModal(True)
        self.setMinimumWidth(400)

        # Internal state for colors
        self._fill_color_hex = CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_color_hex"]
        self._line_color_hex = CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_color_hex"]

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # 1. Fill Color
        self.fill_color_button = QPushButton()
        self.fill_color_button.setToolTip("Click to choose a fill color")
        self.fill_color_button.clicked.connect(self.open_fill_color_dialog)
        form_layout.addRow(QLabel("Fill Color:"), self.fill_color_button)

        # 2. Fill Opacity
        opacity_layout = QHBoxLayout()
        self.fill_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.fill_opacity_slider.setRange(0, 100)
        self.fill_opacity_slider.setToolTip("Set fill opacity (0% to 100%)")
        opacity_layout.addWidget(self.fill_opacity_slider)
        self.fill_opacity_spinbox = QSpinBox()
        self.fill_opacity_spinbox.setRange(0, 100)
        self.fill_opacity_spinbox.setSuffix("%")
        opacity_layout.addWidget(self.fill_opacity_spinbox)
        self.fill_opacity_slider.valueChanged.connect(self.fill_opacity_spinbox.setValue)
        self.fill_opacity_spinbox.valueChanged.connect(self.fill_opacity_slider.setValue)
        form_layout.addRow(QLabel("Fill Opacity:"), opacity_layout)

        # 3. Line Color
        self.line_color_button = QPushButton()
        self.line_color_button.setToolTip("Click to choose a line color")
        self.line_color_button.clicked.connect(self.open_line_color_dialog)
        form_layout.addRow(QLabel("Line Color:"), self.line_color_button)

        # 4. Line Width
        self.line_width_spinbox = QSpinBox()
        self.line_width_spinbox.setRange(1, 10) # Min 1px, Max 10px
        self.line_width_spinbox.setSuffix(" px")
        self.line_width_spinbox.setToolTip("Set line width in pixels")
        form_layout.addRow(QLabel("Line Width:"), self.line_width_spinbox)

        # 5. View Mode
        self.view_mode_combo = QComboBox()
        self.view_modes = ["Outline and Fill", "Outline Only", "Fill Only"]
        self.view_mode_combo.addItems(self.view_modes)
        self.view_mode_combo.setToolTip("Select the default KML view mode")
        form_layout.addRow(QLabel("View Mode:"), self.view_mode_combo)

        # 6. Zoom Level Offset
        self.zoom_offset_spinbox = QSpinBox()
        self.zoom_offset_spinbox.setRange(-5, 5) # Example range
        self.zoom_offset_spinbox.setToolTip("Adjust zoom level after fitting to KML bounds (-5 to +5)")
        form_layout.addRow(QLabel("Zoom Level Offset:"), self.zoom_offset_spinbox)

        main_layout.addLayout(form_layout)

        # Buttons
        self.button_box = QDialogButtonBox()
        self.save_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Save)
        self.reset_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Reset)
        self.cancel_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Cancel)

        self.button_box.accepted.connect(self.accept) # Save maps to accept
        self.button_box.rejected.connect(self.reject) # Cancel maps to reject
        self.reset_button.clicked.connect(self._populate_fields_with_defaults)

        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

        self._load_initial_settings()

    def _get_contrasting_text_color(self, hex_color_str: str) -> str:
        try:
            color = QColor(hex_color_str)
            # Using luminance formula to decide text color
            # Luminance = 0.299*R + 0.587*G + 0.114*B
            # Normalize RGB values to 0-1 range
            r, g, b = color.redF(), color.greenF(), color.blueF()
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return "#000000" if luminance > 0.5 else "#ffffff" # Black text on light, White text on dark
        except Exception:
            return "#000000" # Default to black if color parsing fails

    def _update_color_button_display(self, button: QPushButton, color_hex: str):
        button.setText(color_hex.upper())
        text_color = self._get_contrasting_text_color(color_hex)
        button.setStyleSheet(f"background-color: {color_hex}; color: {text_color};")

    def _load_initial_settings(self):
        settings = self.credential_manager.get_kml_default_view_settings()

        self._fill_color_hex = settings.get("kml_fill_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_color_hex"])
        self._update_color_button_display(self.fill_color_button, self._fill_color_hex)

        self.fill_opacity_slider.setValue(settings.get("kml_fill_opacity_percent", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_opacity_percent"]))
        # Spinbox will be updated by slider's signal

        self._line_color_hex = settings.get("kml_line_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_color_hex"])
        self._update_color_button_display(self.line_color_button, self._line_color_hex)

        self.line_width_spinbox.setValue(settings.get("kml_line_width_px", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_width_px"]))

        view_mode = settings.get("kml_view_mode", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_view_mode"])
        if view_mode in self.view_modes:
            self.view_mode_combo.setCurrentText(view_mode)

        self.zoom_offset_spinbox.setValue(settings.get("kml_zoom_offset", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_zoom_offset"]))


    def _populate_fields_with_defaults(self):
        defaults = CredentialManager.DEFAULT_KML_VIEW_SETTINGS

        self._fill_color_hex = defaults["kml_fill_color_hex"]
        self._update_color_button_display(self.fill_color_button, self._fill_color_hex)

        self.fill_opacity_slider.setValue(defaults["kml_fill_opacity_percent"])

        self._line_color_hex = defaults["kml_line_color_hex"]
        self._update_color_button_display(self.line_color_button, self._line_color_hex)

        self.line_width_spinbox.setValue(defaults["kml_line_width_px"])

        if defaults["kml_view_mode"] in self.view_modes:
            self.view_mode_combo.setCurrentText(defaults["kml_view_mode"])

        self.zoom_offset_spinbox.setValue(defaults["kml_zoom_offset"])

    def open_fill_color_dialog(self):
        current_color = QColor(self._fill_color_hex)
        color = QColorDialog.getColor(current_color, self, "Select Fill Color")
        if color.isValid():
            self._fill_color_hex = color.name().upper()
            self._update_color_button_display(self.fill_color_button, self._fill_color_hex)

    def open_line_color_dialog(self):
        current_color = QColor(self._line_color_hex)
        color = QColorDialog.getColor(current_color, self, "Select Line Color")
        if color.isValid():
            self._line_color_hex = color.name().upper()
            self._update_color_button_display(self.line_color_button, self._line_color_hex)

    def get_settings(self) -> dict:
        settings = {
            "kml_fill_color_hex": self._fill_color_hex,
            "kml_fill_opacity_percent": self.fill_opacity_spinbox.value(),
            "kml_line_color_hex": self._line_color_hex,
            "kml_line_width_px": self.line_width_spinbox.value(),
            "kml_view_mode": self.view_mode_combo.currentText(),
            "kml_zoom_offset": self.zoom_offset_spinbox.value()
        }
        return settings

    def accept(self):
        settings_to_save = self.get_settings()
        if self.credential_manager.save_kml_default_view_settings(settings_to_save):
            # Optionally, inform parent or log success
            print("Default KML view settings saved successfully.")
        else:
            # Optionally, show an error message to the user
            print("Failed to save default KML view settings.")
        super().accept()

if __name__ == '__main__':
    # This basic test requires a QApplication instance and a CredentialManager.
    # For now, this is just to ensure the file is syntactically valid.
    # A more complete test would involve showing the dialog.
    from PySide6.QtWidgets import QApplication
    import sys

    # Create a dummy CredentialManager for testing if the dialog can be instantiated
    # This dummy doesn't need a real DB for this basic test.
    import platformdirs # Import for the real CredentialManager instantiation path
    import os # Import for os.path operations
    
    # Make DummyCredentialManager inherit from CredentialManager to satisfy type hint
    class DummyCredentialManager(CredentialManager): 
        def __init__(self):
            # Need to call super, but CredentialManager might need a path.
            # For a dummy, we might not want to initialize a real settings file.
            # Let's assume CredentialManager's __init__ can be called without args,
            # or handles None/default path for settings for this dummy scenario.
            # If CredentialManager.__init__ strictly requires a path, this might need adjustment
            # or the Dummy should entirely mock the interface without calling super's __init__.
            # For now, let's try without super().__init__() if it causes issues,
            # as we are overriding the only methods used by the dialog.
            # However, type checker might still complain if super().__init__ is not called.
            # A better dummy might avoid inheritance and just provide the needed methods.
            # Given the error, inheritance is the most direct fix for the type checker.
            # Let's try a minimal super call if possible, or skip if it's too complex for dummy.
            # For this test, we only care about the methods used by DefaultViewSettingsDialog.
            # The real CredentialManager __init__ creates a settings file. We don't want that for this dummy.
            # So, we will NOT call super().__init__() and just override methods.
            # This makes it a structural subtype for the methods it implements.
            # The type error is about "incompatible argument type", inheritance fixes this at static analysis level.
            pass # No super().__init__() to avoid real file IO for a dummy

        DEFAULT_KML_VIEW_SETTINGS = { # This will effectively override any class-level one in CredentialManager for this instance
            "kml_fill_color_hex": "#112233",
            "kml_fill_opacity_percent": 20,
            "kml_line_color_hex": "#aabbcc",
            "kml_line_width_px": 2,
            "kml_view_mode": "Outline Only",
            "kml_zoom_offset": -2
        }
        def get_kml_default_view_settings(self):
            print("Dummy CM: get_kml_default_view_settings called")
            return self.DEFAULT_KML_VIEW_SETTINGS.copy()
        def save_kml_default_view_settings(self, settings_dict):
            print(f"Dummy CM: save_kml_default_view_settings called with: {settings_dict}")
            return True

    app = QApplication(sys.argv)
    # Ensure the platformdirs path exists for CredentialManager, even if dummy is used for dialog
    # This helps if a real CredentialManager is instantiated later for other tests in this block

    # Test with Dummy Credential Manager
    print("Testing DefaultViewSettingsDialog with DummyCredentialManager...")
    dummy_cm = DummyCredentialManager()
    dialog_dummy = DefaultViewSettingsDialog(credential_manager=dummy_cm)
    # dialog_dummy.show() # This would show the dialog
    print(f"Dialog created with dummy CM. Fill color button text: {dialog_dummy.fill_color_button.text()}")
    assert dialog_dummy.fill_color_button.text() == dummy_cm.DEFAULT_KML_VIEW_SETTINGS["kml_fill_color_hex"].upper()
    assert dialog_dummy.fill_opacity_spinbox.value() == dummy_cm.DEFAULT_KML_VIEW_SETTINGS["kml_fill_opacity_percent"]

    # Test with real CredentialManager (requires DB setup from its own test block)
    print("\nTesting DefaultViewSettingsDialog with real CredentialManager...")
    # This part assumes the CredentialManager's __main__ block has run or can be run
    # to set up its DB. For an isolated test, we might need to manage the DB file here.
    # For now, we just instantiate it.

    # Create the directory if it doesn't exist to prevent CredentialManager init error
    real_cm_app_data_path = platformdirs.user_data_dir(CredentialManager.APP_NAME, CredentialManager.APP_AUTHOR)
    if not os.path.exists(real_cm_app_data_path):
        os.makedirs(real_cm_app_data_path, exist_ok=True)
        print(f"Created directory for real CredentialManager: {real_cm_app_data_path}")

    # Clean up previous test DB if it exists to ensure fresh state for CredentialManager settings
    db_file_path_for_test = os.path.join(real_cm_app_data_path, CredentialManager.DB_FILE_NAME)
    if os.path.exists(db_file_path_for_test):
        os.remove(db_file_path_for_test)
        print(f"Removed existing DB for fresh CredentialManager test: {db_file_path_for_test}")

    cm_real = CredentialManager() # Will create a new DB or load existing

    # Scenario 1: Fresh DB, get defaults from CredentialManager constant
    print("Scenario 1: Fresh DB, loading initial settings (should be class defaults)")
    dialog_real_fresh = DefaultViewSettingsDialog(credential_manager=cm_real)
    initial_settings = dialog_real_fresh.get_settings()
    print(f"Initial settings from dialog (fresh CM): {initial_settings}")
    for key, value in CredentialManager.DEFAULT_KML_VIEW_SETTINGS.items():
        assert initial_settings[key] == value, f"Fresh CM default mismatch for {key}"

    # Scenario 2: Save new settings, then check
    print("\nScenario 2: Saving new settings via dialog accept")
    test_settings_to_save = {
        "kml_fill_color_hex": "#abcdef",
        "kml_fill_opacity_percent": 77,
        "kml_line_color_hex": "#123456",
        "kml_line_width_px": 4,
        "kml_view_mode": "Fill Only",
        "kml_zoom_offset": 1
    }
    dialog_to_save = DefaultViewSettingsDialog(credential_manager=cm_real)
    # Manually set dialog values as if user interacted
    dialog_to_save._fill_color_hex = test_settings_to_save["kml_fill_color_hex"]
    dialog_to_save.fill_opacity_spinbox.setValue(test_settings_to_save["kml_fill_opacity_percent"])
    dialog_to_save._line_color_hex = test_settings_to_save["kml_line_color_hex"]
    dialog_to_save.line_width_spinbox.setValue(test_settings_to_save["kml_line_width_px"])
    dialog_to_save.view_mode_combo.setCurrentText(test_settings_to_save["kml_view_mode"])
    dialog_to_save.zoom_offset_spinbox.setValue(test_settings_to_save["kml_zoom_offset"])

    dialog_to_save.accept() # This will call save_kml_default_view_settings

    # Verify by creating a new dialog instance and loading settings
    dialog_verify_save = DefaultViewSettingsDialog(credential_manager=cm_real)
    verified_settings = dialog_verify_save.get_settings() # get_settings reads from UI which is loaded by _load_initial_settings
    print(f"Settings after save & reload: {verified_settings}")
    for key, value in test_settings_to_save.items():
        assert verified_settings[key] == value, f"Saved setting mismatch for {key}. Expected {value}, got {verified_settings[key]}"
    print("Save and reload verified.")

    # Scenario 3: Reset to defaults
    print("\nScenario 3: Resetting to defaults")
    dialog_verify_save._populate_fields_with_defaults() # Simulate reset button click
    reset_settings = dialog_verify_save.get_settings()
    print(f"Settings after reset: {reset_settings}")
    for key, value in CredentialManager.DEFAULT_KML_VIEW_SETTINGS.items():
        assert reset_settings[key] == value, f"Reset default mismatch for {key}"
    print("Reset to defaults verified.")

    print("DefaultViewSettingsDialog tests completed.")
    # sys.exit(app.exec()) # Uncomment to actually show and interact with the last dialog instance for manual testing
    sys.exit(0) # Exit cleanly for automated tests
