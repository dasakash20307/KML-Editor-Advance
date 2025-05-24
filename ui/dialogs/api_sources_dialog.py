# File: DilasaKMLTool_v4/ui/dialogs/api_sources_dialog.py
# ----------------------------------------------------------------------
import os 
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableView, QLineEdit,
                               QPushButton, QLabel, QAbstractItemView, QHeaderView,
                               QMessageBox, QDialogButtonBox)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QFont, QIcon
from PySide6.QtCore import Qt

def center_dialog(dialog, parent_window=None): 
    dialog.updateGeometry() 
    if parent_window:
        parent_rect = parent_window.geometry()
        dialog_rect = dialog.frameGeometry()
        x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
        dialog.move(x, y)
    else: 
        if dialog.screen():
            screen_geo = dialog.screen().geometry()
            dialog.move((screen_geo.width() - dialog.width()) // 2,
                        (screen_geo.height() - dialog.height()) // 2)
    
    if parent_window and hasattr(parent_window, 'app_icon_path') and parent_window.app_icon_path and os.path.exists(parent_window.app_icon_path):
        try:
            dialog.setWindowIcon(QIcon(parent_window.app_icon_path))
        except Exception as e:
            print(f"Dialog icon error: {e}")


class APISourcesDialog(QDialog):
    def __init__(self, parent_main_window, db_manager):
        super().__init__(parent_main_window)
        self.parent_main_window = parent_main_window
        self.db_manager = db_manager
        self.setWindowTitle("Manage mWater API Sources")
        self.setMinimumSize(600, 400)
        self.setModal(True)

        self.current_selection_id = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.table_view = QTableView()
        self.table_model = QStandardItemModel(0, 3, self) 
        self.table_model.setHorizontalHeaderLabels(["ID", "Title", "URL"])
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
        self.table_view.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)    
        self.table_view.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)         
        self.table_view.setColumnHidden(0, True) 
        self.table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table_view)

        form_layout = QHBoxLayout()
        self.title_label = QLabel("Title:")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter a descriptive title")
        self.url_label = QLabel("URL:")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Paste mWater API URL here")
        form_layout.addWidget(self.title_label); form_layout.addWidget(self.title_edit)
        form_layout.addWidget(self.url_label); form_layout.addWidget(self.url_edit, 1) 
        layout.addLayout(form_layout)

        action_buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New Source")
        self.add_button.clicked.connect(self._add_source)
        self.save_edit_button = QPushButton("Save Changes")
        self.save_edit_button.clicked.connect(self._save_edited_source)
        self.save_edit_button.setEnabled(False)
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self._delete_source)
        self.delete_button.setEnabled(False)
        
        action_buttons_layout.addWidget(self.add_button); action_buttons_layout.addWidget(self.save_edit_button)
        action_buttons_layout.addWidget(self.delete_button); action_buttons_layout.addStretch()
        layout.addLayout(action_buttons_layout)

        self.dialog_button_box = QDialogButtonBox()
        self.use_button = self.dialog_button_box.addButton("Fetch using this URL", QDialogButtonBox.ButtonRole.ActionRole)
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self._use_source)
        self.dialog_button_box.addButton(QDialogButtonBox.StandardButton.Close)
        self.dialog_button_box.rejected.connect(self.reject) 
        layout.addWidget(self.dialog_button_box)

        self._load_sources_into_table()
        center_dialog(self, parent_main_window)


    def _load_sources_into_table(self):
        self.table_model.removeRows(0, self.table_model.rowCount())
        sources = self.db_manager.get_mwater_sources()
        for source_id, title, url in sources:
            self.table_model.appendRow([QStandardItem(str(source_id)), QStandardItem(title), QStandardItem(url)])
        self.parent_main_window.refresh_api_source_dropdown() 

    def _on_selection_changed(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            self.current_selection_id = int(self.table_model.item(row, 0).text()) 
            self.title_edit.setText(self.table_model.item(row, 1).text())
            self.url_edit.setText(self.table_model.item(row, 2).text())
            self.save_edit_button.setEnabled(True); self.delete_button.setEnabled(True); self.use_button.setEnabled(True)
        else:
            self.current_selection_id = None; self.title_edit.clear(); self.url_edit.clear()
            self.save_edit_button.setEnabled(False); self.delete_button.setEnabled(False); self.use_button.setEnabled(False)

    def _add_source(self):
        title, url = self.title_edit.text().strip(), self.url_edit.text().strip()
        if not title or not url: QMessageBox.warning(self, "Input Error", "Title and URL cannot be empty."); return
        if self.db_manager.add_mwater_source(title, url):
            self._load_sources_into_table(); self.title_edit.clear(); self.url_edit.clear()
            QMessageBox.information(self, "Success", "API Source added.")
        else: QMessageBox.warning(self, "Database Error", "Failed to add API Source. URL might already exist.")

    def _save_edited_source(self):
        if self.current_selection_id is None: return
        title, url = self.title_edit.text().strip(), self.url_edit.text().strip()
        if not title or not url: QMessageBox.warning(self, "Input Error", "Title and URL cannot be empty."); return
        if self.db_manager.update_mwater_source(self.current_selection_id, title, url):
            self._load_sources_into_table(); QMessageBox.information(self, "Success", "API Source updated.")
        else: QMessageBox.warning(self, "Database Error", "Failed to update API Source. URL might conflict.")
            
    def _delete_source(self):
        if self.current_selection_id is None: return
        if QMessageBox.question(self, "Confirm Delete", f"Delete API source: '{self.title_edit.text()}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_mwater_source(self.current_selection_id):
                self._load_sources_into_table(); self.title_edit.clear(); self.url_edit.clear()
                self.current_selection_id = None; self._on_selection_changed(self.table_view.selectionModel().selection(), self.table_view.selectionModel().selection())
                QMessageBox.information(self, "Success", "API Source deleted.")
            else: QMessageBox.warning(self, "Database Error", "Failed to delete API Source.")

    def _use_source(self):
        if self.current_selection_id is None: return
        self.parent_main_window.fetch_data_from_api_url(self.url_edit.text(), self.title_edit.text())
        self.accept() 
