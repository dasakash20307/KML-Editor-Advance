import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, Signal

class NicknameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Device Nickname Setup")
        self.setModal(True)

        self.layout = QVBoxLayout(self)

        self.instruction_label = QLabel("Please provide a nickname for this device. This will help identify it if you use the 'Connected App' mode on other devices.")
        self.instruction_label.setWordWrap(True)
        self.layout.addWidget(self.instruction_label)

        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("e.g., Office PC, Field Laptop 1")
        self.layout.addWidget(self.nickname_input)

        self.button_layout = QHBoxLayout()
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.accept)
        self.next_button.setDefault(True)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.next_button)
        self.layout.addLayout(self.button_layout)

        self.setMinimumWidth(400)

    def get_nickname(self) -> str:
        return self.nickname_input.text().strip()

    def accept(self):
        if not self.get_nickname():
            QMessageBox.warning(self, "Input Required", "Nickname cannot be empty.")
            return
        super().accept()

class ModeSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Mode Setup")
        self.setModal(True)

        self.layout = QVBoxLayout(self)

        self.instruction_label = QLabel("Select the operational mode for this application instance:")
        self.instruction_label.setWordWrap(True)
        self.layout.addWidget(self.instruction_label)

        self.central_app_radio = QRadioButton("Central App (Manage a local database and KML files)")
        self.connected_app_radio = QRadioButton("Connected App (Connect to an existing Central App's shared data)")

        self.central_app_radio.setChecked(True) # Default selection

        self.layout.addWidget(self.central_app_radio)
        self.layout.addWidget(self.connected_app_radio)

        self.button_layout = QHBoxLayout()
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.accept)
        self.next_button.setDefault(True)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.next_button)
        self.layout.addLayout(self.button_layout)

        self.setMinimumWidth(400)

    def get_app_mode(self) -> str:
        if self.central_app_radio.isChecked():
            return "Central App"
        elif self.connected_app_radio.isChecked():
            return "Connected App"
        return "" # Should not happen

class PathConfigurationDialog(QDialog):
    # Signal to indicate setup is finished and paths are validated
    setup_finished = Signal(str, str)

    def __init__(self, app_mode: str, parent=None):
        super().__init__(parent)
        self.app_mode = app_mode
        self.setWindowTitle(f"Path Configuration ({self.app_mode})")
        self.setModal(True)

        self.layout = QVBoxLayout(self)

        self.db_path_label = QLabel() # Define before use in _setup_ui_for_mode
        self.kml_folder_label = QLabel() # Define before use

        self.db_path_input = QLineEdit()
        self.kml_folder_input = QLineEdit()

        self.db_browse_button = QPushButton("Browse...")
        self.kml_browse_button = QPushButton("Browse...")

        self._setup_ui_for_mode()

        self.button_layout = QHBoxLayout()
        self.finish_button = QPushButton("Finish Setup")
        self.finish_button.clicked.connect(self.validate_and_accept)
        self.finish_button.setDefault(True)

        self.button_layout.addStretch()
        self.button_layout.addWidget(self.finish_button)
        self.layout.addLayout(self.button_layout)

        self.setMinimumWidth(500)

    def _setup_ui_for_mode(self):
        main_group = QGroupBox("Data Paths Configuration")
        group_layout = QVBoxLayout()

        # Database Path
        db_path_layout = QHBoxLayout()
        # self.db_path_label = QLabel() # Already defined in __init__
        db_path_layout.addWidget(self.db_path_label)
        db_path_layout.addWidget(self.db_path_input)

        if self.app_mode == "Central App":
            self.db_path_label.setText("Main Database File Path (Create or Select):")
            self.db_path_input.setPlaceholderText("e.g., C:/Users/YourUser/Documents/DilasaData/main_data.db")
            self.db_path_input.setReadOnly(True)
            self.db_browse_button.clicked.connect(self._browse_db_file_central)
            db_path_layout.addWidget(self.db_browse_button)
        else: # Connected App
            self.db_path_label.setText("Central App's Database File Path (Network Path):")
            self.db_path_input.setPlaceholderText("e.g., //SHARED_SERVER/DilasaData/main_data.db")
            self.db_path_input.setReadOnly(False)
            self.db_browse_button.setVisible(False)
        group_layout.addLayout(db_path_layout)

        # KML Folder Path
        kml_folder_layout = QHBoxLayout()
        # self.kml_folder_label = QLabel() # Already defined in __init__
        kml_folder_layout.addWidget(self.kml_folder_label)
        kml_folder_layout.addWidget(self.kml_folder_input)

        if self.app_mode == "Central App":
            self.kml_folder_label.setText("KML Files Folder Path (Create or Select):")
            self.kml_folder_input.setPlaceholderText("e.g., C:/Users/YourUser/Documents/DilasaData/KML_Files")
            self.kml_folder_input.setReadOnly(True)
            self.kml_browse_button.clicked.connect(self._browse_kml_folder_central)
            kml_folder_layout.addWidget(self.kml_browse_button)
        else: # Connected App
            self.kml_folder_label.setText("Central App's KML Files Folder Path (Network Path):")
            self.kml_folder_input.setPlaceholderText("e.g., //SHARED_SERVER/DilasaData/KML_Files")
            self.kml_folder_input.setReadOnly(False)
            self.kml_browse_button.setVisible(False)
        group_layout.addLayout(kml_folder_layout)

        main_group.setLayout(group_layout)
        self.layout.addWidget(main_group)

    def _browse_db_file_central(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select or Create Main Database File",
            self.db_path_input.text() or os.path.expanduser("~/dilasa_main_data_v5.db"),
            "SQLite Database Files (*.db *.sqlite *.sqlite3);;All Files (*)"
        )
        if path:
            self.db_path_input.setText(path)

    def _browse_kml_folder_central(self):
        path = QFileDialog.getExistingDirectory(
            self,
            "Select KML Files Folder",
            self.kml_folder_input.text() or os.path.expanduser("~/Dilasa_KML_Files")
        )
        if path:
            self.kml_folder_input.setText(path)

    def get_paths(self) -> tuple[str, str]:
        return self.db_path_input.text().strip(), self.kml_folder_input.text().strip()

    def validate_and_accept(self):
        db_path, kml_folder_path = self.get_paths()

        if not db_path or not kml_folder_path:
            QMessageBox.warning(self, "Input Required", "Both database path and KML folder path must be provided.")
            return

        if self.app_mode == "Central App":
            if not any(db_path.lower().endswith(ext) for ext in ['.db', '.sqlite', '.sqlite3']):
                reply = QMessageBox.question(self, "Confirm Database Name",
                                             f"The database path '{db_path}' does not have a standard .db/.sqlite extension. "
                                             "Are you sure this is correct?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            db_parent_dir = os.path.dirname(db_path)
            if not os.path.exists(db_parent_dir):
                try:
                    os.makedirs(db_parent_dir, exist_ok=True)
                    print(f"Created database parent directory: {db_parent_dir}")
                except OSError as e:
                    QMessageBox.critical(self, "Error", f"Could not create database directory: {db_parent_dir}\\n{e}")
                    return

            if not os.path.exists(kml_folder_path):
                reply = QMessageBox.question(self, "Create Folder?",
                                             f"The KML folder '{kml_folder_path}' does not exist. "
                                             "Would you like to create it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if reply == QMessageBox.Yes:
                    try:
                        os.makedirs(kml_folder_path, exist_ok=True)
                        print(f"Created KML folder: {kml_folder_path}")
                    except OSError as e:
                        QMessageBox.critical(self, "Error", f"Could not create KML folder: {kml_folder_path}\\n{e}")
                        return
                else:
                    QMessageBox.warning(self, "Path Invalid", "KML folder must exist or be creatable for Central App mode.")
                    return
            elif not os.path.isdir(kml_folder_path):
                 QMessageBox.warning(self, "Path Invalid", f"The KML path '{kml_folder_path}' is not a directory.")
                 return

        self.setup_finished.emit(db_path, kml_folder_path)
        super().accept()


if __name__ == '__main__':
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    print("Testing NicknameDialog...")
    nickname_dialog = NicknameDialog()
    if nickname_dialog.exec():
        nickname = nickname_dialog.get_nickname()
        print(f"Nickname entered: {nickname}")
    else:
        print("NicknameDialog canceled.")

    print("\nTesting ModeSelectionDialog...")
    mode_dialog = ModeSelectionDialog()
    app_mode_selected = "Central App"
    if mode_dialog.exec():
        app_mode_selected = mode_dialog.get_app_mode()
        print(f"App mode selected: {app_mode_selected}")
    else:
        print("ModeSelectionDialog canceled.")

    print(f"\nTesting PathConfigurationDialog for mode: {app_mode_selected}...")
    path_dialog = PathConfigurationDialog(app_mode=app_mode_selected)

    def on_setup_finished(db_p, kml_p):
        print(f"Setup finished signal received: DB='{db_p}', KML='{kml_p}'")

    path_dialog.setup_finished.connect(on_setup_finished)

    if path_dialog.exec():
        db_p, kml_p = path_dialog.get_paths()
        print(f"Database path: {db_p}")
        print(f"KML folder path: {kml_p}")
    else:
        print("PathConfigurationDialog canceled.")

    print("\nTesting PathConfigurationDialog for the other mode...")
    other_mode = "Connected App" if app_mode_selected == "Central App" else "Central App"
    path_dialog_other = PathConfigurationDialog(app_mode=other_mode)
    path_dialog_other.setup_finished.connect(on_setup_finished)
    if path_dialog_other.exec():
        db_p, kml_p = path_dialog_other.get_paths()
        print(f"Database path (other mode): {db_p}")
        print(f"KML folder path (other mode): {kml_p}")
    else:
        print("PathConfigurationDialog (other mode) canceled.")

    print("\nAll dialog tests complete.")
