from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QDialogButtonBox, QApplication, QMessageBox, QStyle)
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtCore import Qt
import socket # Added import

class SharingInfoDialog(QDialog):
    def __init__(self, credential_manager, app_mode, parent=None):
        super().__init__(parent)
        self.credential_manager = credential_manager
        self.app_mode = app_mode

        self.setMinimumWidth(550) # Increased width slightly

        main_layout = QVBoxLayout(self)
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        main_layout.addWidget(self.description_label)

        # --- Machine Name (Central App mode only) ---
        self.machine_name_group_layout = QHBoxLayout()
        machine_name_label = QLabel("Machine Name:")
        self.machine_name_edit = QLineEdit()
        self.machine_name_edit.setReadOnly(True)
        self.machine_name_edit.setMinimumWidth(350)
        self.machine_name_group_layout.addWidget(machine_name_label)
        self.machine_name_group_layout.addWidget(self.machine_name_edit, 1)
        # Add to main_layout conditionally later

        # --- Database Path ---
        self.db_group_layout = QHBoxLayout()
        db_label = QLabel("Central Database Path:") # Changed label for clarity
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setMinimumWidth(350)
        self.db_copy_button = QPushButton("Copy")
        self.db_copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon))))
        self.db_copy_button.clicked.connect(lambda: self._copy_to_clipboard(self.db_path_edit.text()))
        self.db_group_layout.addWidget(db_label)
        self.db_group_layout.addWidget(self.db_path_edit, 1)
        self.db_group_layout.addWidget(self.db_copy_button)
        main_layout.addLayout(self.db_group_layout)

        # --- KML Folder Path ---
        self.kml_group_layout = QHBoxLayout()
        kml_label = QLabel("Central KML Folder Path:") # Changed label for clarity
        self.kml_folder_edit = QLineEdit()
        self.kml_folder_edit.setMinimumWidth(350)
        self.kml_copy_button = QPushButton("Copy")
        self.kml_copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirLinkIcon))))
        self.kml_copy_button.clicked.connect(lambda: self._copy_to_clipboard(self.kml_folder_edit.text()))
        self.kml_group_layout.addWidget(kml_label)
        self.kml_group_layout.addWidget(self.kml_folder_edit, 1)
        self.kml_group_layout.addWidget(self.kml_copy_button)
        main_layout.addLayout(self.kml_group_layout)

        # --- Button Box ---
        self.button_box = QDialogButtonBox()
        main_layout.addWidget(self.button_box)

        self._configure_for_mode()

    def _configure_for_mode(self):
        db_path_current = self.credential_manager.get_db_path() if self.credential_manager else "Not Configured"
        kml_folder_path_current = self.credential_manager.get_kml_folder_path() if self.credential_manager else "Not Configured"

        if self.app_mode == "Central App":
            self.setWindowTitle("Share Central App Paths")
            self.description_label.setText(
                "These are the paths configured for this Central Application instance. "
                "Share these with users who need to set up a 'Connected Application' instance on another computer on the same network."
            )
            # Add machine name layout to the main layout at a specific position (e.g., after description)
            self.layout().insertLayout(1, self.machine_name_group_layout)
            try:
                self.machine_name_edit.setText(socket.gethostname())
            except Exception as e:
                self.machine_name_edit.setText("Could not fetch")
                print(f"Error fetching hostname: {e}")

            self.db_path_edit.setText(db_path_current if db_path_current else "Not Configured")
            self.db_path_edit.setReadOnly(True)
            self.db_copy_button.setVisible(True)

            self.kml_folder_edit.setText(kml_folder_path_current if kml_folder_path_current else "Not Configured")
            self.kml_folder_edit.setReadOnly(True)
            self.kml_copy_button.setVisible(True)

            self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Close)
            self.button_box.rejected.connect(self.reject)

        elif self.app_mode == "Connected App":
            self.setWindowTitle("Configure Central App Connection")
            self.description_label.setText(
                "Enter the full network paths to the Central Application's shared database file and KML files folder. "
                "These paths are provided by the administrator of the Central App."
            )
            # Machine name is not shown in this mode, so ensure its layout is not added or is hidden if already part of a base layout
            # Since machine_name_group_layout is added conditionally, this is fine.

            self.db_path_edit.setText(db_path_current if db_path_current else "")
            self.db_path_edit.setReadOnly(False)
            self.db_path_edit.setPlaceholderText("\\\\\\\\server\\\\share\\\\central_database.db or /mnt/share/central_database.db")
            self.db_copy_button.setVisible(False) # Hide copy button

            self.kml_folder_edit.setText(kml_folder_path_current if kml_folder_path_current else "")
            self.kml_folder_edit.setReadOnly(False)
            self.kml_folder_edit.setPlaceholderText("\\\\\\\\server\\\\share\\\\kml_files\\\\ or /mnt/share/kml_files/")
            self.kml_copy_button.setVisible(False) # Hide copy button

            self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            self.button_box.accepted.connect(self._save_connected_app_settings)
            self.button_box.rejected.connect(self.reject)
        else:
            # Fallback for unknown mode
            self.setWindowTitle("Information")
            self.description_label.setText(f"App mode '{self.app_mode}' not fully supported by this dialog.")
            self.db_path_edit.setReadOnly(True)
            self.kml_folder_edit.setReadOnly(True)
            self.db_copy_button.setVisible(False)
            self.kml_copy_button.setVisible(False)
            self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Close)
            self.button_box.rejected.connect(self.reject)

    def _save_connected_app_settings(self):
        new_db_path = self.db_path_edit.text().strip()
        new_kml_folder_path = self.kml_folder_edit.text().strip()

        if not new_db_path or not new_kml_folder_path:
            QMessageBox.warning(self, "Input Error", "Both Database Path and KML Folder Path are required.")
            return

        # Basic validation (more can be added, e.g., checking if path looks like a network path or is accessible)
        # For now, we just save what the user provides.
        # Launcher app already performs os.path.exists checks during startup for Connected App.

        try:
            # Directly use _set_setting and then _load_settings as discussed
            self.credential_manager._set_setting("main_db_path", new_db_path)
            self.credential_manager._set_setting("kml_folder_path", new_kml_folder_path)
            self.credential_manager._load_settings() # Reload settings into credential_manager instance

            QMessageBox.information(self, "Settings Saved", 
                                    "Central App paths have been updated. "
                                    "The application might need a restart for changes to fully apply, "
                                    "or re-check paths upon next operation.")
            self.accept() # Close dialog
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {e}")
            # Optionally, log the error using a logger if available from parent
            print(f"Error saving connected app settings: {e}")


    def _copy_to_clipboard(self, text_to_copy):
        if text_to_copy and text_to_copy != "Not Configured":
            try:
                QGuiApplication.clipboard().setText(text_to_copy)
                if self.parent() and hasattr(self.parent(), 'log_message'):
                    self.parent().log_message(f"Path copied to clipboard: {text_to_copy}", "info")
                else:
                    print(f"Copied to clipboard: {text_to_copy}") 
            except Exception as e:
                if self.parent() and hasattr(self.parent(), 'log_message'):
                    self.parent().log_message(f"Error copying to clipboard: {e}", "error")
                else:
                    print(f"Error copying to clipboard: {e}")
        else:
            if self.parent() and hasattr(self.parent(), 'log_message'):
                 self.parent().log_message("Cannot copy 'Not Configured' or empty path.", "warning")
            else:
                print("Cannot copy 'Not Configured' or empty path.")


if __name__ == '__main__':
    import sys
    # Mock CredentialManager for testing
    class MockCredentialManager:
        def __init__(self, mode="Central App"):
            self._app_mode = mode
            self._db_path = "/mnt/shared_drive/main_database_prod.db"
            self._kml_folder_path = "/mnt/shared_drive/kml_files_central_repo/"
            if mode == "Connected App":
                self._db_path = "\\\\\\\\network-server\\\\share\\\\db.sqlite"
                self._kml_folder_path = "\\\\\\\\network-server\\\\share\\\\kmls"


        def get_app_mode(self): return self._app_mode
        def get_db_path(self): return self._db_path
        def get_kml_folder_path(self): return self._kml_folder_path
        
        # Mock internal methods used by the dialog
        def _set_setting(self, key, value): 
            print(f"MOCK: Setting {key} = {value}")
            if key == "main_db_path": self._db_path = value
            if key == "kml_folder_path": self._kml_folder_path = value

        def _load_settings(self): print("MOCK: Reloading settings")


    app = QApplication(sys.argv)
    
    print("Testing Central App mode dialog:")
    mock_cm_central = MockCredentialManager(mode="Central App")
    dialog_central = SharingInfoDialog(mock_cm_central, mock_cm_central.get_app_mode())
    dialog_central.show()
    # app.exec() # Don't block here for testing next dialog

    print("\nTesting Connected App mode dialog:")
    mock_cm_connected = MockCredentialManager(mode="Connected App")
    dialog_connected = SharingInfoDialog(mock_cm_connected, mock_cm_connected.get_app_mode())
    dialog_connected.show()
    
    sys.exit(app.exec()) 