# File: DilasaKMLTool_v4/ui/dialogs/duplicate_dialog.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox
from PySide6.QtCore import Qt
from .api_sources_dialog import center_dialog 

class DuplicateDialog(QDialog):
    def __init__(self, parent_main_window, response_code): 
        super().__init__(parent_main_window)
        self.setWindowTitle("Duplicate Entry Found")
        self.setMinimumWidth(450); self.setModal(True)
        self.choice = "skip"; self.apply_to_all = False

        layout = QVBoxLayout(self); layout.setContentsMargins(15,15,15,15); layout.setSpacing(10)
        message_label = QLabel(f"A record with Response Code '<b>{response_code}</b>' already exists in the database.")
        message_label.setWordWrap(True); layout.addWidget(message_label)
        layout.addWidget(QLabel("What would you like to do?"))

        button_layout = QHBoxLayout()
        for text, choice_val in [("Overwrite Existing", "overwrite"), 
                                 ("Skip This Duplicate", "skip"), 
                                 ("Cancel Entire Import", "cancel_all")]:
            btn = QPushButton(text); btn.clicked.connect(lambda ch=choice_val: self._set_choice(ch))
            button_layout.addWidget(btn)
        layout.addLayout(button_layout)

        self.apply_to_all_checkbox = QCheckBox("Apply this choice to all subsequent duplicates in this import session")
        layout.addWidget(self.apply_to_all_checkbox)
        
        self.setFixedSize(self.sizeHint()) 
        center_dialog(self, parent_main_window)

    def _set_choice(self, choice_str):
        self.choice = choice_str
        self.apply_to_all = self.apply_to_all_checkbox.isChecked()
        self.accept() 

    def get_user_choice(self):
        return self.choice, self.apply_to_all if self.exec() == QDialog.DialogCode.Accepted else ("skip", False)

