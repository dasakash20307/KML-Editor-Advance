from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QDialogButtonBox, QApplication)
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtCore import Qt

class SharingInfoDialog(QDialog):
    def __init__(self, credential_manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Central Application Shared Paths")
        self.setMinimumWidth(500)
        self.credential_manager = credential_manager

        main_layout = QVBoxLayout(self)

        description_label = QLabel(
            "These are the paths configured for this Central Application instance. "
            "Use these paths when setting up a 'Connected Application' instance on another computer on the same network."
        )
        description_label.setWordWrap(True)
        main_layout.addWidget(description_label)

        db_path = self.credential_manager.get_db_path()
        kml_folder_path = self.credential_manager.get_kml_folder_path()

        # Database Path
        db_group_layout = QHBoxLayout()
        db_label = QLabel("Main Database File Path:")
        self.db_path_edit = QLineEdit(db_path if db_path else "Not Configured")
        self.db_path_edit.setReadOnly(True)
        self.db_path_edit.setMinimumWidth(300)
        db_copy_button = QPushButton("Copy")
        db_copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon(QApplication.style().standardIcon(QApplication.StandardPixmap.SP_FileLinkIcon)))) # Fallback icon
        db_copy_button.clicked.connect(lambda: self._copy_to_clipboard(self.db_path_edit.text()))
        db_group_layout.addWidget(db_label)
        db_group_layout.addWidget(self.db_path_edit, 1)
        db_group_layout.addWidget(db_copy_button)
        main_layout.addLayout(db_group_layout)

        # KML Folder Path
        kml_group_layout = QHBoxLayout()
        kml_label = QLabel("KML Files Folder Path:   ") # Added spaces for alignment
        self.kml_folder_edit = QLineEdit(kml_folder_path if kml_folder_path else "Not Configured")
        self.kml_folder_edit.setReadOnly(True)
        self.kml_folder_edit.setMinimumWidth(300)
        kml_copy_button = QPushButton("Copy")
        kml_copy_button.setIcon(QIcon.fromTheme("edit-copy", QIcon(QApplication.style().standardIcon(QApplication.StandardPixmap.SP_DirLinkIcon)))) # Fallback icon
        kml_copy_button.clicked.connect(lambda: self._copy_to_clipboard(self.kml_folder_edit.text()))
        kml_group_layout.addWidget(kml_label)
        kml_group_layout.addWidget(self.kml_folder_edit, 1)
        kml_group_layout.addWidget(kml_copy_button)
        main_layout.addLayout(kml_group_layout)

        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject) # Close connects to reject
        main_layout.addWidget(button_box)

    def _copy_to_clipboard(self, text_to_copy):
        if text_to_copy and text_to_copy != "Not Configured":
            try:
                QGuiApplication.clipboard().setText(text_to_copy)
                # Optionally, provide feedback e.g., via status bar or a temporary label
                # self.parent().log_message(f"Path copied to clipboard: {text_to_copy}", "info")
                print(f"Copied to clipboard: {text_to_copy}") # Placeholder feedback
            except Exception as e:
                # self.parent().log_message(f"Error copying to clipboard: {e}", "error")
                print(f"Error copying to clipboard: {e}") # Placeholder feedback
        else:
            # self.parent().log_message("Cannot copy 'Not Configured' or empty path.", "warning")
            print("Cannot copy 'Not Configured' or empty path.") # Placeholder feedback


if __name__ == '__main__':
    import sys
    # Mock CredentialManager for testing
    class MockCredentialManager:
        def get_db_path(self):
            return "/mnt/shared_drive/main_database_prod.db"
        def get_kml_folder_path(self):
            return "/mnt/shared_drive/kml_files_central_repo/"

    app = QApplication(sys.argv)
    mock_cm = MockCredentialManager()
    dialog = SharingInfoDialog(mock_cm)
    dialog.show()
    sys.exit(app.exec()) 