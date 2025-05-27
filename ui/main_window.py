# DilasaKMLTool_v4/ui/main_window.py (Significant Updates)
# ----------------------------------------------------------------------
import os 
import sys 
import csv
import utm 
import tempfile # Added for _trigger_ge_polygon_upload
import subprocess # Added for _trigger_ge_polygon_upload

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
                               QSplitter, QFrame, QStatusBar, QMenuBar, QMenu, QToolBar, QPushButton,
                               QAbstractItemView, QHeaderView, QMessageBox, QFileDialog, QComboBox,
                               QSizePolicy, QTextEdit, QInputDialog, QLineEdit, QDateEdit, QGridLayout,
                               QCheckBox, QGroupBox, QStackedWidget, QApplication, QStyledItemDelegate,
                               QDialog, QProgressBar) # Added QDialog, QProgressBar
from PySide6.QtGui import QPixmap, QIcon, QAction, QStandardItemModel, QStandardItem, QFont, QColor
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize, QSortFilterProxyModel, QDate

from database.db_manager import DatabaseManager
from core.utils import resource_path
from core.data_processor import process_csv_row_data, CSV_HEADERS 
from core.api_handler import fetch_data_from_mwater_api
from core.kml_generator import add_polygon_to_kml_object 
import simplekml # Already present, used for KML generation
import datetime 

# Assuming dialogs are in their own files and correctly imported
from .dialogs.api_sources_dialog import APISourcesDialog 
from .dialogs.duplicate_dialog import DuplicateDialog # Will be removed
from .dialogs.output_mode_dialog import OutputModeDialog 
from .widgets.map_view_widget import MapViewWidget
from .widgets.google_earth_webview_widget import GoogleEarthWebViewWidget 


# Constants 
APP_NAME_MW = "Dilasa Advance KML Tool"
APP_VERSION_MW = "Beta.v4.001.Dv-A.Das"
LOGO_FILE_NAME_MW = "dilasa_logo.jpg" 
APP_ICON_FILE_NAME_MW = "app_icon.ico" 
INFO_COLOR_MW = "#0078D7"
ERROR_COLOR_MW = "#D32F2F"     
SUCCESS_COLOR_MW = "#388E3C"   
FG_COLOR_MW = "#333333"        
ORGANIZATION_TAGLINE_MW = "Developed by Dilasa Janvikash Pratishthan to support community upliftment"

# --- Table Model with Checkbox Support ---
class PolygonTableModel(QAbstractTableModel):
    CHECKBOX_COL = 0
    ID_COL = 1
    EVALUATION_STATUS_COL = 2  # New column
    STATUS_COL = 3             # Was 2
    UUID_COL = 4               # Was 3
    FARMER_COL = 5             # Was 4
    VILLAGE_COL = 6            # Was 5
    DATE_ADDED_COL = 7         # Was 6
    EXPORT_COUNT_COL = 8       # Was 7
    LAST_EXPORTED_COL = 9      # Was 8

    def __init__(self, data_list=None, parent=None, db_manager_instance=None): 
        super().__init__(parent)
        self.db_manager = db_manager_instance 
        self._data = []
        self._check_states = {}
        self._headers = ["", "ID", "Evaluation Status", "Status", "UUID", "Farmer Name", "Village",
                         "Date Added", "Export Count", "Last Exported"]
        if data_list: self.update_data(data_list)

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers) # Updated implicitly by _headers length

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid(): return None
        row, col = index.row(), index.column()
        if row >= len(self._data): return None
        record = self._data[row] 
        db_id = record[0] 

        if role == Qt.ItemDataRole.CheckStateRole and col == self.CHECKBOX_COL:
            return self._check_states.get(db_id, Qt.CheckState.Unchecked)
        
        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.CHECKBOX_COL: return None
            value = None
            if col == self.ID_COL: value = record[0]
            elif col == self.EVALUATION_STATUS_COL: value = record[8] 
            elif col == self.STATUS_COL: value = record[1]
            elif col == self.UUID_COL: value = record[2]
            elif col == self.FARMER_COL: value = record[3]
            elif col == self.VILLAGE_COL: value = record[4]
            elif col == self.DATE_ADDED_COL: value = record[5]
            elif col == self.EXPORT_COUNT_COL: value = record[6]
            elif col == self.LAST_EXPORTED_COL: value = record[7]
            else: return None

            if col == self.EXPORT_COUNT_COL and value is None: return "0" 
            if col == self.LAST_EXPORTED_COL and value is None: return ""  
            if isinstance(value, (datetime.datetime, datetime.date)): 
                return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime.datetime) else value.strftime("%Y-%m-%d")
            return str(value) if value is not None else ""

        elif role == Qt.ItemDataRole.BackgroundRole:
            evaluation_status_val = record[8] 
            if col == self.EVALUATION_STATUS_COL:
                if evaluation_status_val == "Eligible":
                    return QColor(144, 238, 144, int(255 * 0.7)) 
                elif evaluation_status_val == "Not Eligible":
                    return QColor(255, 182, 193, int(255 * 0.7)) 
                return None 
            return None 
            
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter if col != self.CHECKBOX_COL else Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.ForegroundRole: 
            if col == self.STATUS_COL and record[1] and "error" in str(record[1]).lower():
                return QColor("red")
        elif role == Qt.ItemDataRole.FontRole and col != self.CHECKBOX_COL: 
             return QFont("Segoe UI", 9)
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid(): return False
        row, col = index.row(), index.column()
        if row >= len(self._data) or not self._data[row]: return False
        db_id = self._data[row][0]

        if role == Qt.ItemDataRole.CheckStateRole and col == self.CHECKBOX_COL:
            self._check_states[db_id] = Qt.CheckState(value)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            return True
        
        if role == Qt.ItemDataRole.EditRole and col == self.EVALUATION_STATUS_COL:
            print(f"[TableModel.setData] Entered for EVALUATION_STATUS_COL. Row: {row}, Col: {col}, New Value: '{value}'")
            new_status = str(value)
            
            db_id = self._data[row][0] 
            print(f"[TableModel.setData] DB ID: {db_id}")

            if self.db_manager and hasattr(self.db_manager, 'update_evaluation_status'):
                print(f"[TableModel.setData] Attempting DB update for ID {db_id} to status '{new_status}'")
                update_success = self.db_manager.update_evaluation_status(db_id, new_status) 
                print(f"[TableModel.setData] DB update_success: {update_success}")

                if update_success:
                    print(f"[TableModel.setData] Before internal update: self._data[{row}] = {self._data[row]}")
                    updated_record_list = list(self._data[row])
                    updated_record_list[8] = new_status 
                    self._data[row] = tuple(updated_record_list)
                    print(f"[TableModel.setData] After internal update: self._data[{row}] = {self._data[row]}")
                    
                    print(f"[TableModel.setData] Emitting dataChanged for index ({row},{col})")
                    self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.BackgroundRole])
                    
                    parent_main_window = self.parent() 
                    if parent_main_window and hasattr(parent_main_window, 'log_message'):
                         parent_main_window.log_message(f"Evaluation status for ID {db_id} updated to '{new_status}'.", "info")
                    return True
                else:
                    error_msg = f"DB update failed for record ID {db_id} with status {new_status}"
                    print(f"[TableModel.setData] {error_msg}")
                    parent_main_window = self.parent()
                    if parent_main_window and hasattr(parent_main_window, 'log_message'):
                         parent_main_window.log_message(error_msg, "error")
                    return False
            else:
                error_msg = f"Error: self.db_manager not available or missing update_evaluation_status method for record ID {db_id}"
                print(f"[TableModel.setData] {error_msg}")
                parent_main_window = self.parent()
                if parent_main_window and hasattr(parent_main_window, 'log_message'): 
                    parent_main_window.log_message(error_msg, "error")
                return False
        return False

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == self.CHECKBOX_COL:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif index.column() == self.EVALUATION_STATUS_COL:
            flags |= Qt.ItemFlag.ItemIsEditable
            flags |= Qt.ItemFlag.ItemIsSelectable 
            flags |= Qt.ItemFlag.ItemIsEnabled
        else:
            flags |= Qt.ItemFlag.ItemIsSelectable 
            flags |= Qt.ItemFlag.ItemIsEnabled
        return flags

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        if role == Qt.ItemDataRole.FontRole and orientation == Qt.Orientation.Horizontal: 
            return QFont("Segoe UI", 9, QFont.Weight.Bold)
        return None

    def update_data(self, new_data_list):
        self.beginResetModel()
        self._data = new_data_list if new_data_list is not None else []
        current_ids = {row[0] for row in self._data if row} 
        self._check_states = {db_id: state for db_id, state in self._check_states.items() if db_id in current_ids}
        self.endResetModel()

    def get_checked_item_db_ids(self):
        return [db_id for db_id, state in self._check_states.items() if state == Qt.CheckState.Checked]

    def set_all_checkboxes(self, state=Qt.CheckState.Checked):
        self.beginResetModel() 
        for row_data in self._data:
            if row_data and len(row_data) > 0: 
                 db_id = row_data[0] 
                 self._check_states[db_id] = state
        self.endResetModel()

# --- Filter Proxy Model ---
class PolygonFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_uuid_text = ""
        self.filter_after_date_added = None 
        self.filter_before_date_added = None 
        self.filter_export_status = "All" 
        self.filter_error_status = "All"  

    def set_uuid_filter(self, text):
        self.filter_uuid_text = text.lower()
        self.invalidateFilter()

    def set_date_added_filter(self, after_date, before_date): 
        self.filter_after_date_added = after_date if after_date and after_date.isValid() else None
        self.filter_before_date_added = before_date if before_date and before_date.isValid() else None
        self.invalidateFilter()
        
    def set_export_status_filter(self, status): 
        self.filter_export_status = status
        self.invalidateFilter()

    def set_error_status_filter(self, status): 
        self.filter_error_status = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        if not source_model or source_row >= len(source_model._data): return False
        record = source_model._data[source_row]
        if not record or len(record) < 8: 
            return False 

        if self.filter_uuid_text:
            uuid_val = str(record[2]).lower() 
            if self.filter_uuid_text not in uuid_val: return False
        
        date_added_str = record[5]
        if date_added_str:
            try:
                row_date_added = QDate.fromString(date_added_str.split(" ")[0], "yyyy-MM-dd")
                if row_date_added.isValid():
                    if self.filter_after_date_added and row_date_added < self.filter_after_date_added: return False
                    if self.filter_before_date_added and row_date_added > self.filter_before_date_added: return False
            except Exception: pass 

        export_count = record[6] if record[6] is not None else 0
        if self.filter_export_status == "Exported" and export_count == 0: return False
        if self.filter_export_status == "Not Exported" and export_count > 0: return False

        status_val = str(record[1]).lower()
        if self.filter_error_status == "Error Records" and "error" not in status_val: return False
        if self.filter_error_status == "Valid Records" and "error" in status_val: return False
            
        return True

# --- Delegate for Evaluation Status ComboBox ---
class EvaluationStatusDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.options = ["Not Evaluated Yet", "Eligible", "Not Eligible"]

    def createEditor(self, parent_widget, option, index): 
        editor = QComboBox(parent_widget)
        editor.addItems(self.options)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        if value in self.options:
            editor.setCurrentText(value)
        else: 
            editor.setCurrentText("Not Evaluated Yet")

    def setModelData(self, editor, model, index):
        value = editor.currentText()
        print(f"[Delegate.setModelData] Called for index ({index.row()},{index.column()}). Value: {value}")
        model.setData(index, value, Qt.ItemDataRole.EditRole)

# --- API Import Progress Dialog ---
class APIImportProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Import Progress")
        self.setModal(True)
        self.setMinimumWidth(400) 
        self._was_cancelled = False

        layout = QVBoxLayout(self)

        self.total_label = QLabel("Total Records to Process: 0")
        layout.addWidget(self.total_label)

        self.processed_label = QLabel("Records Processed (Attempted): 0") 
        layout.addWidget(self.processed_label)
        
        self.new_added_label = QLabel("New Records Added: 0")
        layout.addWidget(self.new_added_label)

        self.skipped_label = QLabel("Records Skipped (Duplicates/Errors): 0")
        layout.addWidget(self.skipped_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._perform_cancel)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def _perform_cancel(self):
        self._was_cancelled = True
        self.reject() 

    def set_total_records(self, count):
        self.total_label.setText(f"Total Records to Process: {count}")
        if count > 0:
            self.progress_bar.setRange(0, count)
        else:
            self.progress_bar.setRange(0, 100) 

    def update_progress(self, processed_count, skipped_count, new_added_count):
        self.processed_label.setText(f"Records Processed (Attempted): {processed_count}")
        self.new_added_label.setText(f"New Records Added: {new_added_count}")
        self.skipped_label.setText(f"Records Skipped (Duplicates/Errors): {skipped_count}")
        
        self.progress_bar.setValue(processed_count) 
        QApplication.processEvents() 

    def was_cancelled(self):
        return self._was_cancelled 


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME_MW} - {APP_VERSION_MW}")
        self.app_icon_path = resource_path(APP_ICON_FILE_NAME_MW) 
        if os.path.exists(self.app_icon_path): self.setWindowIcon(QIcon(self.app_icon_path))
        else: print(f"Warning: Main window icon '{self.app_icon_path}' not found.")
        try: self.db_manager = DatabaseManager()
        except Exception as e: QMessageBox.critical(self, "DB Error", f"DB init failed: {e}\nExiting."); sys.exit(1) 
        
        self.resize(1200, 800); self._center_window() 
        self._create_main_layout()
        self._create_header() 
        self._create_menus_and_toolbar() 
        self._create_status_bar()
        
        self.current_temp_kml_path = None
        self.show_ge_instructions_popup_again = True

        self._setup_main_content_area() 
        self.load_data_into_table() 
        
        self.log_message(f"{APP_NAME_MW} {APP_VERSION_MW} started. DB at: {self.db_manager.db_path}", "info")


    def _center_window(self):
        if self.screen(): screen_geo = self.screen().geometry(); self.move((screen_geo.width()-self.width())//2, (screen_geo.height()-self.height())//2)
    
    def _create_main_layout(self):
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0) 

    def _create_header(self):
        header_widget = QWidget()
        header_widget.setFixedHeight(60) 
        header_widget.setStyleSheet("background-color: #F0F0F0; border-bottom: 1px solid #D0D0D0;") 
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 5, 5, 5) 
        header_layout.setSpacing(5) 

        logo_path = resource_path(LOGO_FILE_NAME_MW)
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path); logo_label = QLabel()
            logo_label.setPixmap(pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)) 
            header_layout.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignVCenter) 
        else: header_layout.addWidget(QLabel("[L]"))
        
        title_label = QLabel(APP_NAME_MW); title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold)) 
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label, 1) 

        version_label = QLabel(APP_VERSION_MW); version_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Normal, True)) 
        version_label.setStyleSheet(f"color: {INFO_COLOR_MW};")
        header_layout.addWidget(version_label, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        
        self.main_layout.addWidget(header_widget) 


    def _create_menus_and_toolbar(self): 
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        self.export_data_action = QAction(QIcon.fromTheme("document-save-as", QIcon(self.app_icon_path)), "Export Displayed Data as &CSV...", self)
        self.export_data_action.triggered.connect(self.handle_export_displayed_data_csv)
        file_menu.addAction(self.export_data_action)
        file_menu.addSeparator()
        exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit", self) 
        exit_action.setShortcut("Ctrl+Q"); exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close); file_menu.addAction(exit_action)
        
        data_menu = menubar.addMenu("&Data")
        self.import_csv_action = QAction(QIcon.fromTheme("document-open"),"Import &CSV...", self)
        self.import_csv_action.triggered.connect(self.handle_import_csv)
        data_menu.addAction(self.import_csv_action)
        
        self.fetch_api_action = QAction(QIcon.fromTheme("network-transmit-receive"), "&Fetch from API...", self) 
        self.fetch_api_action.triggered.connect(self.handle_fetch_from_api)
        data_menu.addAction(self.fetch_api_action)

        self.manage_api_action = QAction(QIcon.fromTheme("preferences-system"),"Manage A&PI Sources...", self)
        self.manage_api_action.triggered.connect(self.handle_manage_api_sources)
        data_menu.addAction(self.manage_api_action)
        data_menu.addSeparator()
        self.delete_checked_action = QAction(QIcon.fromTheme("edit-delete"),"Delete Checked Rows...", self) 
        self.delete_checked_action.triggered.connect(self.handle_delete_checked_rows) 
        data_menu.addAction(self.delete_checked_action)
        self.clear_all_data_action = QAction(QIcon.fromTheme("edit-clear-all"),"Clear All Polygon Data...", self)
        self.clear_all_data_action.triggered.connect(self.handle_clear_all_data) 
        data_menu.addAction(self.clear_all_data_action)

        kml_menu = menubar.addMenu("&KML")
        self.generate_kml_action = QAction(QIcon.fromTheme("document-export"),"&Generate KML for Checked Rows...", self) 
        self.generate_kml_action.triggered.connect(self.handle_generate_kml) 
        kml_menu.addAction(self.generate_kml_action)

        self.view_menu = menubar.addMenu("&View")
        self.toggle_ge_view_action = QAction("Google Earth View", self)
        self.toggle_ge_view_action.setCheckable(True)
        self.toggle_ge_view_action.toggled.connect(self._handle_ge_view_toggle)
        self.view_menu.addAction(self.toggle_ge_view_action)

        help_menu = menubar.addMenu("&Help"); 
        self.about_action = QAction(QIcon.fromTheme("help-about"),"&About", self)
        self.about_action.triggered.connect(self.handle_about)
        help_menu.addAction(self.about_action)

        self.ge_instructions_action = QAction("GE &Instructions", self)
        self.ge_instructions_action.triggered.connect(self.handle_show_ge_instructions)
        help_menu.addAction(self.ge_instructions_action)
        
        self.toolbar = QToolBar("Main Toolbar") 
        self.toolbar.setIconSize(QSize(20,20)) 
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon) 
        self.toolbar.setMovable(True) 
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        self.toolbar.addAction(self.import_csv_action) 
        self.toolbar.addSeparator() 

        self.toggle_ge_view_button = QPushButton("GE View: OFF")
        self.toggle_ge_view_button.setCheckable(True)
        self.toggle_ge_view_button.toggled.connect(self._handle_ge_view_toggle)
        self.toolbar.addWidget(self.toggle_ge_view_button)
        self.toolbar.addSeparator()
        
        self.toolbar.addWidget(QLabel(" API Source: ")) 
        self.api_source_combo_toolbar = QComboBox() 
        self.api_source_combo_toolbar.setMinimumWidth(150)
        self.refresh_api_source_dropdown() 
        self.toolbar.addWidget(self.api_source_combo_toolbar)
        self.toolbar.addAction(self.fetch_api_action)
        
        manage_api_toolbar_action = QAction(QIcon.fromTheme("preferences-system"), "Manage API Sources", self)
        manage_api_toolbar_action.triggered.connect(self.handle_manage_api_sources)
        self.toolbar.addAction(manage_api_toolbar_action)

        self.toolbar.addSeparator()
        self.toolbar.addAction(self.generate_kml_action)
        self.toolbar.addAction(self.delete_checked_action) 


    def _create_status_bar(self):
        self.statusBar = QStatusBar(); self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready.", 3000)

    def _setup_filter_panel(self):
        self.filter_groupbox = QGroupBox("Filters") 
        self.filter_groupbox.setCheckable(True)
        self.filter_groupbox.setChecked(False) 

        self.filter_widgets_container = QWidget() 
        filter_layout = QGridLayout(self.filter_widgets_container)
        filter_layout.setContentsMargins(5,5,5,5) 
        filter_layout.setSpacing(5)
        
        filter_layout.addWidget(QLabel("Filter UUID:"), 0, 0)
        self.uuid_filter_edit = QLineEdit(); self.uuid_filter_edit.setPlaceholderText("Contains...")
        self.uuid_filter_edit.textChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.uuid_filter_edit, 0, 1, 1, 3) 

        filter_layout.addWidget(QLabel("Date Added After:"), 1, 0)
        self.date_added_after_edit = QDateEdit(); self.date_added_after_edit.setCalendarPopup(True)
        self.date_added_after_edit.setDisplayFormat("yyyy-MM-dd"); self.date_added_after_edit.clear() 
        self.date_added_after_edit.setSpecialValueText(" "); self.date_added_after_edit.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.date_added_after_edit, 1, 1)

        filter_layout.addWidget(QLabel("Before:"), 1, 2)
        self.date_added_before_edit = QDateEdit(); self.date_added_before_edit.setCalendarPopup(True)
        self.date_added_before_edit.setDisplayFormat("yyyy-MM-dd"); self.date_added_before_edit.clear()
        self.date_added_before_edit.setSpecialValueText(" "); self.date_added_before_edit.dateChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.date_added_before_edit, 1, 3)

        filter_layout.addWidget(QLabel("Export Status:"), 2, 0)
        self.export_status_combo = QComboBox(); self.export_status_combo.addItems(["All", "Exported", "Not Exported"])
        self.export_status_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.export_status_combo, 2, 1)

        filter_layout.addWidget(QLabel("Record Status:"), 2, 2)
        self.error_status_combo = QComboBox(); self.error_status_combo.addItems(["All", "Valid Records", "Error Records"])
        self.error_status_combo.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addWidget(self.error_status_combo, 2, 3)

        clear_filters_button = QPushButton("Clear Filters")
        clear_filters_button.clicked.connect(self.clear_filters)
        filter_layout.addWidget(clear_filters_button, 0, 4, Qt.AlignmentFlag.AlignRight) 
        
        filter_layout.setColumnStretch(1, 1); filter_layout.setColumnStretch(3, 1)
        
        groupbox_main_layout = QVBoxLayout(self.filter_groupbox)
        groupbox_main_layout.setContentsMargins(0,5,0,0) 
        groupbox_main_layout.addWidget(self.filter_widgets_container)
        
        self.filter_groupbox.toggled.connect(self.filter_widgets_container.setVisible)
        self.filter_widgets_container.setVisible(self.filter_groupbox.isChecked()) 

        return self.filter_groupbox


    def apply_filters(self):
        if not hasattr(self, 'filter_proxy_model'): return
        self.filter_proxy_model.set_uuid_filter(self.uuid_filter_edit.text())
        
        after_date = self.date_added_after_edit.date() if self.date_added_after_edit.text().strip() and self.date_added_after_edit.date().isValid() else None
        before_date = self.date_added_before_edit.date() if self.date_added_before_edit.text().strip() and self.date_added_before_edit.date().isValid() else None
        self.filter_proxy_model.set_date_added_filter(after_date, before_date)
        
        self.filter_proxy_model.set_export_status_filter(self.export_status_combo.currentText())
        self.filter_proxy_model.set_error_status_filter(self.error_status_combo.currentText())


    def clear_filters(self):
        self.uuid_filter_edit.clear()
        self.date_added_after_edit.clear(); self.date_added_after_edit.setSpecialValueText(" ")
        self.date_added_before_edit.clear(); self.date_added_before_edit.setSpecialValueText(" ")      
        self.export_status_combo.setCurrentIndex(0) 
        self.error_status_combo.setCurrentIndex(0)  

    def _setup_main_content_area(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal) 
        
        self.map_view_widget = MapViewWidget(self) 
        self.map_view_widget.setMinimumWidth(300) 

        self.google_earth_view_widget = GoogleEarthWebViewWidget(self)
        self.google_earth_view_widget.setMinimumWidth(300)

        self.map_stack = QStackedWidget(self)
        self.map_stack.addWidget(self.map_view_widget) 
        self.map_stack.addWidget(self.google_earth_view_widget) 
        
        self.main_splitter.addWidget(self.map_stack)

        right_pane_widget = QWidget()
        right_pane_layout = QVBoxLayout(right_pane_widget)
        right_pane_layout.setContentsMargins(10,0,10,10) 

        filter_panel_widget = self._setup_filter_panel()
        right_pane_layout.addWidget(filter_panel_widget)


        self.right_splitter = QSplitter(Qt.Orientation.Vertical) 
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0,0,0,0) 
        
        checkbox_header_layout = QHBoxLayout()
        self.select_all_checkbox = QCheckBox("Select/Deselect All")
        self.select_all_checkbox.stateChanged.connect(self.toggle_all_checkboxes)
        checkbox_header_layout.addWidget(self.select_all_checkbox)
        checkbox_header_layout.addStretch()
        table_layout.addLayout(checkbox_header_layout)
        
        self.table_view = QTableView()
        # self.db_manager is initialized in MainWindow.__init__
        # Pass the db_manager instance to the PolygonTableModel constructor
        self.source_model = PolygonTableModel(parent=self, db_manager_instance=self.db_manager) 
        self.filter_proxy_model = PolygonFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.source_model)
        self.table_view.setModel(self.filter_proxy_model)

        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # Allow editing specifically for delegate-managed columns, triggered by DoubleClicked or SelectedClicked
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True) 
        # Sort by Date Added (column index 7 after new column) by default
        self.table_view.sortByColumn(self.source_model.DATE_ADDED_COL, Qt.SortOrder.DescendingOrder) 

        # Setup Delegate for Evaluation Status Column
        evaluation_delegate = EvaluationStatusDelegate(self.table_view) # Pass table_view as parent
        self.table_view.setItemDelegateForColumn(self.source_model.EVALUATION_STATUS_COL, evaluation_delegate)

        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #D0D0D0; gridline-color: #E0E0E0;
                selection-background-color: #AED6F1; selection-color: black;
                alternate-background-color: #F8F8F8;
            }
            QTableView::item { padding: 5px; border-bottom: 1px solid #E0E0E0; border-right: none; }
            QTableView::item:selected { background-color: #AED6F1; color: black; }
            QHeaderView::section { background-color: #EAEAEA; padding: 6px;
                                   border: none; border-bottom: 1px solid #C0C0C0; font-weight: bold; }
            QHeaderView { border: none; }
        """)

        self.table_view.setColumnWidth(self.source_model.CHECKBOX_COL, 30)
        self.table_view.setColumnWidth(self.source_model.ID_COL, 50)
        self.table_view.setColumnWidth(self.source_model.EVALUATION_STATUS_COL, 150) # New column width
        self.table_view.setColumnWidth(self.source_model.STATUS_COL, 100)
        self.table_view.setColumnWidth(self.source_model.UUID_COL, 120) # Example, adjust as needed
        self.table_view.setColumnWidth(self.source_model.FARMER_COL, 150) # Example, adjust as needed
        self.table_view.setColumnWidth(self.source_model.VILLAGE_COL, 120) # Example, adjust as needed
        # DATE_ADDED_COL, EXPORT_COUNT_COL, LAST_EXPORTED_COL can use default or be set too

        table_layout.addWidget(self.table_view) 
        self.right_splitter.addWidget(table_container)
        self.table_view.selectionModel().selectionChanged.connect(self.on_table_selection_changed)

        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0,10,0,0) 
        log_label = QLabel("Status and Logs:")
        log_layout.addWidget(log_label)
        self.log_text_edit_qt_actual = QTextEdit() 
        self.log_text_edit_qt_actual.setReadOnly(True)
        self.log_text_edit_qt_actual.setFont(QFont("Segoe UI", 9))
        log_layout.addWidget(self.log_text_edit_qt_actual) 
        self.right_splitter.addWidget(log_container)
        
        self.right_splitter.setStretchFactor(0, 3) 
        self.right_splitter.setStretchFactor(1, 1) 

        right_pane_layout.addWidget(self.right_splitter, 1) 
        self.main_splitter.addWidget(right_pane_widget) 
        
        self.main_splitter.setStretchFactor(0, 1) 
        self.main_splitter.setStretchFactor(1, 2) 
        
        self.main_layout.addWidget(self.main_splitter, 1) 
        

    def toggle_all_checkboxes(self, state_int):
        check_state = Qt.CheckState(state_int)
        self.source_model.set_all_checkboxes(check_state)

    def on_table_selection_changed(self, selected, deselected):
        selected_proxy_indexes = self.table_view.selectionModel().selectedRows()
        polygon_record = None # Initialize polygon_record

        if selected_proxy_indexes:
            source_model_index = self.filter_proxy_model.mapToSource(selected_proxy_indexes[0])
            if source_model_index.isValid():
                db_id_item = self.source_model.data(source_model_index.siblingAtColumn(self.source_model.ID_COL))
                try:
                    db_id = int(db_id_item)
                    polygon_record = self.db_manager.get_polygon_data_by_id(db_id)
                except (ValueError, TypeError):
                    self.log_message(f"Map/GE: Invalid ID for selected row.", "error")
                    polygon_record = None # Ensure it's None on error
                except Exception as e:
                    self.log_message(f"Map/GE: Error fetching record: {e}", "error")
                    polygon_record = None # Ensure it's None on error
        
        # Logic for Google Earth View
        if self.map_stack.currentIndex() == 1: # Google Earth View is active
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                self._trigger_ge_polygon_upload(polygon_record)
            else:
                # Clear map if no valid selection or record not valid for KML
                # self.google_earth_view_widget.clear_polygon_highlight() # Assuming such a method might exist
                self.log_message("GE View: No valid polygon record selected or record not valid for KML upload.", "warning")
        # Logic for original MapViewWidget
        else:
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                coords_lat_lon, utm_valid = [], True
                for i in range(1,5):
                    e,n=polygon_record.get(f'p{i}_easting'),polygon_record.get(f'p{i}_northing')
                    zn,zl=polygon_record.get(f'p{i}_zone_num'),polygon_record.get(f'p{i}_zone_letter')
                    if None in [e,n,zn,zl]: utm_valid=False; break
                    try: lat,lon=utm.to_latlon(e,n,zn,zl); coords_lat_lon.append((lat,lon)) 
                    except Exception as e_conv: self.log_message(f"Map: UTM conv fail {polygon_record.get('uuid')}, P{i}: {e_conv}","error"); utm_valid=False; break
                if utm_valid and len(coords_lat_lon)==4: self.map_view_widget.display_polygon(coords_lat_lon,coords_lat_lon[0])
                elif hasattr(self,'map_view_widget'): self.map_view_widget.clear_map()
            else: # No valid selection or record not suitable for map
                if hasattr(self,'map_view_widget'): self.map_view_widget.clear_map()

    def refresh_api_source_dropdown(self):
        if hasattr(self, 'api_source_combo_toolbar'):
            current_text = self.api_source_combo_toolbar.currentText()
            self.api_source_combo_toolbar.clear()
            sources = self.db_manager.get_mwater_sources()
            for sid, title, url in sources: self.api_source_combo_toolbar.addItem(title, userData=url) 
            index = self.api_source_combo_toolbar.findText(current_text)
            if index != -1: self.api_source_combo_toolbar.setCurrentIndex(index)
            elif sources: self.api_source_combo_toolbar.setCurrentIndex(0)

    def handle_manage_api_sources(self):
        dialog = APISourcesDialog(self, self.db_manager); dialog.exec(); self.refresh_api_source_dropdown() 

    def handle_import_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select CSV File", os.path.expanduser("~/Documents"), "CSV files (*.csv);;All files (*.*)")
        if not filepath: return
        self.log_message(f"Loading CSV: {filepath}", "info")
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                self._process_imported_data(list(reader), f"CSV '{os.path.basename(filepath)}'") 
        except Exception as e: self.log_message(f"Error reading CSV '{filepath}': {e}", "error"); QMessageBox.critical(self, "CSV Error", f"Could not read CSV file:\n{e}")

    def handle_fetch_from_api(self):
        selected_api_title = self.api_source_combo_toolbar.currentText() 
        selected_api_url = self.api_source_combo_toolbar.currentData() 
        if not selected_api_url: QMessageBox.information(self, "API Fetch", "No API source selected or URL is missing."); return
        self.log_message(f"Fetching from API: {selected_api_title}...", "info") 
        rows_from_api, error_msg = fetch_data_from_mwater_api(selected_api_url, selected_api_title)
        if error_msg: self.log_message(f"API Fetch Error ({selected_api_title}): {error_msg}", "error"); QMessageBox.warning(self, "API Fetch Error", error_msg); return
        if rows_from_api is not None: self._process_imported_data(rows_from_api, selected_api_title) 
        else: self.log_message(f"No data returned or error for {selected_api_title}.", "info")

    def _process_imported_data(self, row_list, source_description):
        if not row_list:
            self.log_message(f"No data rows found in {source_description}.", "info")
            return

        progress_dialog = APIImportProgressDialog(self)
        progress_dialog.set_total_records(len(row_list))
        progress_dialog.show()

        processed_in_loop = 0
        skipped_in_loop = 0
        new_added_in_loop = 0
        
        for i, original_row_dict in enumerate(row_list):
            processed_in_loop += 1
            rc_from_row = ""
            for k, v in original_row_dict.items():
                if k.lstrip('\ufeff') == CSV_HEADERS["response_code"]:
                    rc_from_row = v.strip()
                    break
            
            if not rc_from_row:
                self.log_message(f"Row {i+1} from {source_description} skipped: Missing Response Code.", "error")
                skipped_in_loop += 1
                progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
                if progress_dialog.was_cancelled(): break
                continue

            is_dup_id = self.db_manager.check_duplicate_response_code(rc_from_row)
            if is_dup_id:
                self.log_message(f"Skipped duplicate Response Code '{rc_from_row}'.", "info")
                skipped_in_loop += 1
                progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
                if progress_dialog.was_cancelled(): break
                continue

            processed_flat = process_csv_row_data(original_row_dict)
            cur_uuid, cur_rc = processed_flat.get("uuid"), processed_flat.get("response_code")

            if not cur_uuid or not cur_rc:
                error_detail = processed_flat.get('error_messages', 'Unknown processing error')
                self.log_message(f"Data processing error for original RC '{rc_from_row}'. Details: {error_detail}", "error")
                skipped_in_loop += 1
                progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
                if progress_dialog.was_cancelled(): break
                continue
            
            processed_flat["last_modified"] = datetime.datetime.now().isoformat()
            # Always attempt to add, overwrite is False as we skip duplicates now
            db_result_id = self.db_manager.add_or_update_polygon_data(processed_flat, overwrite=False)

            if db_result_id is not None:
                if not is_dup_id: # It was a new record if is_dup_id was None/False before DB call
                    new_added_in_loop += 1
            else:
                self.log_message(f"Failed to save RC '{cur_rc}' to DB.", "error")
                skipped_in_loop += 1 # Count as skipped if DB operation failed

            progress_dialog.update_progress(processed_in_loop, skipped_in_loop, new_added_in_loop)
            if progress_dialog.was_cancelled():
                self.log_message("Import cancelled by user.", "info")
                break
        
        progress_dialog.close()
        self.load_data_into_table()
        self.log_message(
            f"Import from {source_description}: "
            f"Attempted: {processed_in_loop}, "
            f"New Added: {new_added_in_loop}, "
            f"Skipped (Duplicates/Errors): {skipped_in_loop}.",
            "info"
        )

    def handle_export_displayed_data_csv(self): 
        model_to_export = self.table_view.model() 
        if not model_to_export or model_to_export.rowCount() == 0: QMessageBox.information(self, "Export Data", "No data displayed to export."); return
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Displayed Data As CSV", os.path.expanduser("~/Documents/dilasa_displayed_data.csv"), "CSV Files (*.csv)")
        if not filepath: return
        try:
            headers = self.source_model._headers 
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile); writer.writerow(headers[1:]) 
                for row in range(model_to_export.rowCount()):
                    row_data = [model_to_export.data(model_to_export.index(row, col)) for col in range(1, model_to_export.columnCount())] 
                    writer.writerow(row_data)
            self.log_message(f"Data exported to {filepath}", "success")
            QMessageBox.information(self, "Export Successful", f"{model_to_export.rowCount()} displayed records exported to:\n{filepath}")
        except Exception as e: self.log_message(f"Error exporting displayed data to CSV: {e}", "error"); QMessageBox.critical(self, "Export Error", f"Could not export displayed data: {e}")

    def handle_delete_checked_rows(self): 
        checked_ids = self.source_model.get_checked_item_db_ids()
        if not checked_ids: QMessageBox.information(self, "Delete Checked", "No records checked for deletion."); return
        if QMessageBox.question(self, "Confirm Delete", f"Delete {len(checked_ids)} checked record(s) permanently?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_polygon_data(checked_ids):
                self.log_message(f"{len(checked_ids)} checked record(s) deleted.", "info"); self.load_data_into_table() 
            else: self.log_message("Failed to delete checked records.", "error"); QMessageBox.warning(self, "DB Error", "Could not delete records.")

    def handle_clear_all_data(self):
        if QMessageBox.question(self, "Confirm Clear All", "Delete ALL polygon data records permanently?\nThis cannot be undone.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_all_polygon_data():
                self.log_message("All polygon data records deleted.", "info"); self.source_model._check_states.clear(); self.load_data_into_table()
            else: self.log_message("Failed to clear data.", "error"); QMessageBox.warning(self, "DB Error", "Could not clear data.")
    
    def handle_generate_kml(self): 
        checked_ids = self.source_model.get_checked_item_db_ids()
        if not checked_ids: QMessageBox.information(self, "Generate KML", "No records checked for KML generation."); return
        records_data = [self.db_manager.get_polygon_data_by_id(db_id) for db_id in checked_ids]
        valid_for_kml = [r for r in records_data if r and r.get('status') == 'valid_for_kml']
        if not valid_for_kml: QMessageBox.information(self, "Generate KML", "Checked records are not valid for KML."); return
        output_folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", os.path.expanduser("~/Documents"))
        if not output_folder: self.log_message("KML generation cancelled.", "info"); return
        output_mode_dialog = OutputModeDialog(self); kml_output_mode = output_mode_dialog.get_selected_mode()
        if not kml_output_mode: self.log_message("KML gen cancelled (mode selection).", "info"); return
        self.log_message(f"Generating KMLs to: {output_folder} (Mode: {kml_output_mode})", "info")
        files_gen, ids_gen = 0, []
        try:
            if kml_output_mode == "single":
                ts=datetime.datetime.now().strftime('%d.%m.%y'); fn=f"Consolidate_ALL_KML_{ts}_{len(valid_for_kml)}.kml"
                doc=simplekml.Kml(name=f"Consolidated - {ts}")
                for pd in valid_for_kml: 
                    if add_polygon_to_kml_object(doc, pd): ids_gen.append(pd['id'])
                if doc.features: doc.save(os.path.join(output_folder,fn)); files_gen=1
            elif kml_output_mode == "multiple":
                for pd in valid_for_kml:
                    doc=simplekml.Kml(name=pd['uuid'])
                    if add_polygon_to_kml_object(doc, pd): doc.save(os.path.join(output_folder,f"{pd['uuid']}.kml")); ids_gen.append(pd['id']); files_gen+=1
            for rid in ids_gen: self.db_manager.update_kml_export_status(rid)
            if ids_gen: self.load_data_into_table()
            msg=f"{files_gen} KMLs generated for {len(ids_gen)} records." if files_gen > 0 else "No KMLs generated."
            self.log_message(msg,"success" if files_gen>0 else "info"); QMessageBox.information(self,"KML Generation",msg)
        except Exception as e: self.log_message(f"KML Gen Error: {e}","error"); QMessageBox.critical(self,"KML Error",f"Error:\n{e}")

    def _trigger_ge_polygon_upload(self, polygon_record):
        self.log_message(f"GE View: Processing polygon UUID {polygon_record.get('uuid')} for Google Earth upload.", "info")

        kml_doc = simplekml.Kml(name=str(polygon_record.get('uuid', 'Polygon')))
        if add_polygon_to_kml_object(kml_doc, polygon_record):
            try:
                # Delete old temp KML if it exists
                if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
                    try:
                        os.remove(self.current_temp_kml_path)
                        self.log_message(f"Old temporary KML file deleted: {self.current_temp_kml_path}", "info")
                    except FileNotFoundError:
                        self.log_message(f"Old temporary KML file not found for deletion: {self.current_temp_kml_path}", "warning")
                    except PermissionError:
                        self.log_message(f"Permission denied while deleting old temporary KML file: {self.current_temp_kml_path}", "error")
                    except Exception as e_del:
                        self.log_message(f"Error deleting old temporary KML file {self.current_temp_kml_path}: {e_del}", "error")
                
                fd, temp_kml_path = tempfile.mkstemp(suffix=".kml", prefix="ge_poly_")
                os.close(fd) 
                kml_doc.save(temp_kml_path)
                self.current_temp_kml_path = temp_kml_path # Store new path
                self.log_message(f"Temporary KML saved to: {self.current_temp_kml_path}", "info")

                QApplication.clipboard().setText(self.current_temp_kml_path)
                self.log_message("KML file path copied to clipboard.", "info")

                if self.show_ge_instructions_popup_again:
                    self._show_ge_instructions_popup()

            except Exception as e_kml_save:
                self.log_message(f"Error saving temporary KML or copying to clipboard: {e_kml_save}", "error")
                QMessageBox.warning(self, "KML Error", f"Could not save KML or copy path: {e_kml_save}")
        else:
            self.log_message(f"Failed to generate KML content for polygon UUID {polygon_record.get('uuid')}.", "error")
            QMessageBox.warning(self, "KML Generation Failed", "Could not generate KML content for the selected polygon.")

    def _show_ge_instructions_popup(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Google Earth Instructions")
        msg_box.setTextFormat(Qt.TextFormat.PlainText) # Ensure plain text interpretation for newlines
        msg_box.setText("Instructions:\n"
                        "1. Click on the Google Earth window to focus.\n"
                        "2. Press Ctrl+I to open the import dialog.\n"
                        "3. Press Ctrl+V to paste the KML file path.\n"
                        "4. Press Enter to load the KML.\n"
                        "5. Press Ctrl+H for historical imagery view.")
        
        checkbox = QCheckBox("Do not show this popup again")
        msg_box.setCheckBox(checkbox)
        
        msg_box.exec()
        
        if msg_box.checkBox().isChecked():
            self.show_ge_instructions_popup_again = False
            self.log_message("Google Earth instructions popup will not be shown again for this session.", "info")

    def _handle_ge_view_toggle(self, checked):
        original_action_blocked = self.toggle_ge_view_action.signalsBlocked()
        original_button_blocked = self.toggle_ge_view_button.signalsBlocked()

        self.toggle_ge_view_action.blockSignals(True)
        self.toggle_ge_view_button.blockSignals(True)

        self.toggle_ge_view_action.setChecked(checked)
        self.toggle_ge_view_button.setChecked(checked)
        self.toggle_ge_view_button.setText(f"GE View: {'ON' if checked else 'OFF'}")

        self.toggle_ge_view_action.blockSignals(original_action_blocked)
        self.toggle_ge_view_button.blockSignals(original_button_blocked)

        if checked:
            self.map_stack.setCurrentIndex(1)
            self.google_earth_view_widget.set_focus_on_webview()
        else:
            self.map_stack.setCurrentIndex(0)

        self.log_message(f"Google Earth View Toggled: {'ON' if checked else 'OFF'}", "info")

    def handle_about(self):
        QMessageBox.about(self, f"About {APP_NAME_MW}", f"<b>{APP_NAME_MW}</b><br>Version: {APP_VERSION_MW}<br><br>{ORGANIZATION_TAGLINE_MW}<br><br>Processes geographic data for KML generation.")

    def handle_show_ge_instructions(self):
        self._show_ge_instructions_popup()

    def log_message(self, message, level="info"): 
        if hasattr(self, 'log_text_edit_qt_actual'): 
            color_map = {"info": INFO_COLOR_MW, "error": ERROR_COLOR_MW, "success": SUCCESS_COLOR_MW}
            self.log_text_edit_qt_actual.setTextColor(QColor(color_map.get(level, FG_COLOR_MW)))
            self.log_text_edit_qt_actual.append(f"[{level.upper()}] {message}")
            self.log_text_edit_qt_actual.ensureCursorVisible() 
        else: print(f"LOG [{level.upper()}]: {message}")
        if hasattr(self, 'statusBar'): self.statusBar.showMessage(message, 7000 if level=="info" else 10000)
            
    def load_data_into_table(self): 
        try:
            polygon_records = self.db_manager.get_all_polygon_data_for_display()
            self.source_model.update_data(polygon_records) 
        except Exception as e:
            self.log_message(f"Error loading data into table: {e}", "error")
            QMessageBox.warning(self, "Load Data Error", f"Could not load polygon records: {e}")

    def closeEvent(self, event):
        if hasattr(self, 'map_view_widget') and self.map_view_widget: self.map_view_widget.cleanup()
        if hasattr(self, 'google_earth_view_widget') and hasattr(self.google_earth_view_widget, 'cleanup'):
             self.google_earth_view_widget.cleanup() 
        if hasattr(self, 'db_manager') and self.db_manager: self.db_manager.close()

        # Clean up the last temporary KML file if it exists
        if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
            try:
                os.remove(self.current_temp_kml_path)
                self.log_message(f"Temporary KML file deleted on exit: {self.current_temp_kml_path}", "info")
            except Exception as e:
                self.log_message(f"Error deleting temporary KML file {self.current_temp_kml_path} on exit: {e}", "error")
        
        super().closeEvent(event)

[end of ui/main_window.py]
