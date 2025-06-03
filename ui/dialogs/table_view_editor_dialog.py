from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                               QPushButton, QAbstractItemView, QDialogButtonBox,
                               QLabel, QFrame)
from PySide6.QtCore import Qt, Signal

class TableViewEditorDialog(QDialog):
    settings_saved = Signal(list) # Emits the list of visible and ordered column headers

    def __init__(self, all_column_headers, visible_column_headers, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Table Columns")
        self.setMinimumSize(600, 400)

        self._all_headers = list(all_column_headers) # Keep a copy of all possible headers
        self._initial_visible_headers = list(visible_column_headers) # For reset functionality

        main_layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Manage visible columns and their order in the main table. Drag items in the 'Visible Columns' list to reorder them.")
        instructions.setWordWrap(True)
        main_layout.addWidget(instructions)

        # Lists layout
        lists_layout = QHBoxLayout()
        main_layout.addLayout(lists_layout)

        # Available Columns (Hidden)
        available_layout = QVBoxLayout()
        available_layout.addWidget(QLabel("Available Columns (Hidden):"))
        self.available_list = QListWidget()
        available_layout.addWidget(self.available_list)
        lists_layout.addLayout(available_layout)

        # Action Buttons (Add/Remove)
        actions_layout = QVBoxLayout()
        actions_layout.addStretch()
        self.add_button = QPushButton(">>")
        self.remove_button = QPushButton("<<")
        actions_layout.addWidget(self.add_button)
        actions_layout.addWidget(self.remove_button)
        actions_layout.addStretch()
        lists_layout.addLayout(actions_layout)

        # Visible Columns
        visible_layout = QVBoxLayout()
        visible_layout.addWidget(QLabel("Visible Columns (Drag to Reorder):"))
        self.visible_list = QListWidget()
        self.visible_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.visible_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        visible_layout.addWidget(self.visible_list)
        lists_layout.addLayout(visible_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # Dialog Buttons
        button_box = QDialogButtonBox()
        self.save_button = button_box.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        self.cancel_button = button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        self.reset_button = button_box.addButton("Reset to Default", QDialogButtonBox.ButtonRole.ResetRole)
        main_layout.addWidget(button_box)

        # Populate lists
        self._populate_lists(visible_column_headers)

        # Connections
        self.add_button.clicked.connect(self.add_selected_to_visible)
        self.remove_button.clicked.connect(self.remove_selected_from_visible)
        
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self._reset_to_default_view)

    def _populate_lists(self, current_visible_headers):
        self.available_list.clear()
        self.visible_list.clear()

        visible_set = set(current_visible_headers)
        for header in self._all_headers:
            if header in visible_set:
                pass # Will be added to visible_list in order
            else:
                self.available_list.addItem(header)
        
        # Add to visible_list in the order they are currently visible
        for header in current_visible_headers:
             if header in self._all_headers: # Ensure it's a valid header
                self.visible_list.addItem(header)


    def add_selected_to_visible(self):
        selected_items = self.available_list.selectedItems()
        for item in selected_items:
            self.visible_list.addItem(item.text())
            self.available_list.takeItem(self.available_list.row(item))

    def remove_selected_from_visible(self):
        selected_items = self.visible_list.selectedItems()
        for item in selected_items:
            self.available_list.addItem(item.text())
            self.visible_list.takeItem(self.visible_list.row(item))
        # Sort available list for consistency, though not strictly necessary
        self.available_list.sortItems()

    def get_visible_ordered_headers(self):
        ordered_headers = []
        for i in range(self.visible_list.count()):
            ordered_headers.append(self.visible_list.item(i).text())
        return ordered_headers

    def accept(self):
        self.settings_saved.emit(self.get_visible_ordered_headers())
        super().accept()

    def _reset_to_default_view(self):
        # This should reset to the initial state passed during __init__
        # or, ideally, a true application default if available.
        # For now, using _initial_visible_headers if it was populated reasonably.
        # A more robust reset would re-fetch from CredentialManager's default.
        # For this implementation, we will repopulate based on all_column_headers being visible.
        self.log_message_callback("Table view editor reset to default (all columns visible in original order).", "info")
        self._populate_lists(self._all_headers) # Show all columns in original order

    def log_message_callback(self, message, level):
        # This is a placeholder. In a real app, this might be connected to a central logger.
        print(f"[{level.upper()}] TableViewEditorDialog: {message}")

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    
    # Example Data
    all_cols = ["ID", "UUID", "Name", "Date Added", "Status", "KML File", "Notes", "Last Edited"]
    current_vis_cols = ["ID", "Name", "Status", "KML File"]
    
    dialog = TableViewEditorDialog(all_cols, current_vis_cols)
    
    def handle_save(new_order):
        print("Settings saved. New order:", new_order)

    dialog.settings_saved.connect(handle_save)
    
    if dialog.exec():
        print("Dialog accepted.")
    else:
        print("Dialog cancelled.")
    
    # sys.exit(app.exec()) # Not needed if running interactively for test 