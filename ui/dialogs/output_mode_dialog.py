# File: DilasaKMLTool_v4/ui/dialogs/output_mode_dialog.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup, QDialogButtonBox, QFrame
from PySide6.QtCore import Qt
from .api_sources_dialog import center_dialog # Re-use centering utility

class OutputModeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Select KML Output Mode")
        self.setModal(True)
        self.selected_mode = "single"  # Default mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Choose how you want to export the KML files:"))

        self.button_group = QButtonGroup(self)

        # Single KML Option
        self.rb_single = QRadioButton("Single Consolidated KML File")
        self.rb_single.setChecked(True)
        self.button_group.addButton(self.rb_single)
        single_file_layout = QVBoxLayout()
        single_file_layout.addWidget(self.rb_single)

        hint_single = QLabel("Merges all selected records into one KML file.")
        hint_single.setObjectName("hintLabel")
        single_file_layout.addWidget(hint_single)
        single_file_layout.addStretch()

        layout.addLayout(single_file_layout)

        layout.addSpacing(10)

        # Multiple KMLs Option
        self.rb_multiple = QRadioButton("Multiple Individual KML Files")
        self.button_group.addButton(self.rb_multiple)
        multi_file_layout = QVBoxLayout()
        multi_file_layout.addWidget(self.rb_multiple)

        hint_multiple = QLabel("Exports each selected record as a separate KML file to the chosen directory.")
        hint_multiple.setObjectName("hintLabel")
        multi_file_layout.addWidget(hint_multiple)
        multi_file_layout.addStretch()

        layout.addLayout(multi_file_layout)
        
        layout.addStretch()

        # Dialog buttons
        self.dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.dialog_buttons.accepted.connect(self.accept_choice)
        self.dialog_buttons.rejected.connect(self.reject)
        layout.addWidget(self.dialog_buttons)
        
        self.setFixedSize(self.sizeHint())
        center_dialog(self, parent)

    def accept_choice(self):
        if self.rb_single.isChecked():
            self.selected_mode = "single"
        else:
            self.selected_mode = "multiple"
        self.accept()

    def get_selected_mode(self):
        # exec() returns 1 if accepted, 0 if rejected
        return self.selected_mode if self.exec() == QDialog.DialogCode.Accepted else None

