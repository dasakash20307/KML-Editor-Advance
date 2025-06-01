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
                               QDialog, QProgressBar, QStyle) # Added QStyle
from PySide6.QtGui import QPixmap, QIcon, QAction, QStandardItemModel, QStandardItem, QFont, QColor
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize, QSortFilterProxyModel, QDate

from database.db_manager import DatabaseManager
from core.sync_manager import DatabaseLockManager # Added for DB Lock
from core.utils import resource_path
from core.data_processor import process_csv_row_data, CSV_HEADERS, process_api_row_data
from core.api_handler import fetch_data_from_mwater_api
from core.kml_generator import add_polygon_to_kml_object
import simplekml # Already present, used for KML generation
import datetime
import uuid # Added for UUID generation

# Assuming dialogs are in their own files and correctly imported
from .dialogs.api_sources_dialog import APISourcesDialog
# from .dialogs.duplicate_dialog import DuplicateDialog # Removed as per previous subtask
from .dialogs.output_mode_dialog import OutputModeDialog
from .dialogs.default_view_settings_dialog import DefaultViewSettingsDialog
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

API_FIELD_TO_DB_FIELD_MAP = {
    "UUID (use as the file name)": "uuid",
    "Response Code": "response_code",
    "Name of the Farmer": "farmer_name",
    "Village Name": "village_name",
    "Block": "block",
    "District": "district",
    "Proposed Area (Acre)": "proposed_area_acre",
    "Point 1 (UTM)": "p1_utm_str",
    "Point 1 (altitude)": "p1_altitude",
    "Point 2 (UTM)": "p2_utm_str",
    "Point 2 (altitude)": "p2_altitude",
    "Point 3 (UTM)": "p3_utm_str",
    "Point 3 (altitude)": "p3_altitude",
    "Point 4 (UTM)": "p4_utm_str",
    "Point 4 (altitude)": "p4_altitude",
}

# --- Table Model with Checkbox Support ---
class PolygonTableModel(QAbstractTableModel):
    CHECKBOX_COL = 0
    DB_ID_COL = 1
    UUID_COL = 2
    RESPONSE_CODE_COL = 3
    EVALUATION_STATUS_COL = 4
    FARMER_NAME_COL = 5
    VILLAGE_COL = 6
    DATE_ADDED_COL = 7
    KML_FILE_NAME_COL = 8
    KML_FILE_STATUS_COL = 9
    EDIT_COUNT_COL = 10
    LAST_EDIT_DATE_COL = 11
    EDITOR_DEVICE_ID_COL = 12
    EDITOR_NICKNAME_COL = 13
    DEVICE_CODE_COL = 14
    EXPORT_COUNT_COL = 15
    LAST_EXPORTED_COL = 16
    LAST_MODIFIED_COL = 17

    def __init__(self, data_list=None, parent=None, db_manager_instance=None):
        super().__init__(parent)
        self.db_manager = db_manager_instance
        self._data = []
        self._check_states = {}
        self._headers = ["", "DB ID", "UUID", "Response Code", "Evaluation Status", "Farmer Name", "Village", "Date Added", "KML File Name", "KML File Status", "Times Edited", "Last Edit Date", "Editor Device ID", "Editor Nickname", "Device Code (Creator)", "Export Count", "Last Exported", "Last Modified"]
        if data_list: self.update_data(data_list)

    def rowCount(self, parent=QModelIndex()): return len(self._data)
    def columnCount(self, parent=QModelIndex()): return len(self._headers)

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
            if col == self.DB_ID_COL: value = record[0]
            elif col == self.UUID_COL: value = record[1]
            elif col == self.RESPONSE_CODE_COL: value = record[2]
            elif col == self.EVALUATION_STATUS_COL: value = record[8]
            elif col == self.FARMER_NAME_COL: value = record[3]
            elif col == self.VILLAGE_COL: value = record[4]
            elif col == self.DATE_ADDED_COL: value = record[5]
            elif col == self.KML_FILE_NAME_COL: value = record[10]
            elif col == self.KML_FILE_STATUS_COL: value = record[11]
            elif col == self.EDIT_COUNT_COL: value = record[12]
            elif col == self.LAST_EDIT_DATE_COL: value = record[13]
            elif col == self.EDITOR_DEVICE_ID_COL: value = record[14]
            elif col == self.EDITOR_NICKNAME_COL: value = record[15]
            elif col == self.DEVICE_CODE_COL: value = record[9]
            elif col == self.EXPORT_COUNT_COL: value = record[6]
            elif col == self.LAST_EXPORTED_COL: value = record[7]
            elif col == self.LAST_MODIFIED_COL: value = record[16]
            else: return None

            if col == self.EXPORT_COUNT_COL and value is None: return "0"
            if col == self.LAST_EXPORTED_COL and value is None: return ""
            if isinstance(value, (datetime.datetime, datetime.date)):
                return value.strftime("%Y-%m-%d %H:%M:%S") if isinstance(value, datetime.datetime) else value.strftime("%Y-%m-%d")
            return str(value) if value is not None else ""

        elif role == Qt.ItemDataRole.BackgroundRole:
            status_value = record[8]
            if status_value == "Eligible": return QColor(144, 238, 144, int(255 * 0.7))
            elif status_value == "Not Eligible": return QColor(255, 182, 193, int(255 * 0.7))
            elif status_value == "Not Evaluated Yet": return QColor(255, 255, 255)
            else: return QColor(255, 255, 255)

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter if col != self.CHECKBOX_COL else Qt.AlignmentFlag.AlignCenter
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.KML_FILE_STATUS_COL and record[11] and \
               ("error" in str(record[11]).lower() or "deleted" in str(record[11]).lower()):
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
            new_status = str(value)
            main_window = self.parent()

            if not isinstance(main_window, MainWindow) or                not hasattr(main_window, 'db_lock_manager') or                not main_window.db_lock_manager:
                if isinstance(main_window, MainWindow):
                    main_window.log_message("PolygonTableModel: DatabaseLockManager not available in MainWindow.", "error")
                    QMessageBox.critical(main_window, "Error", "Database Lock Manager not available. Cannot save changes.")
                else:
                    # This case should ideally not happen if the model is parented correctly
                    print("PolygonTableModel: ERROR - Parent is not MainWindow or db_lock_manager not accessible.")
                return False

            operation_desc = f"Updating evaluation status for DB ID {db_id}"
            # Acquire lock with a short timeout
            lock_status = main_window.db_lock_manager.acquire_lock(10, operation_desc)

            if lock_status is True:
                update_success = False
                try:
                    if self.db_manager and hasattr(self.db_manager, 'update_evaluation_status'):
                        update_success = self.db_manager.update_evaluation_status(db_id, new_status)
                        if update_success:
                            # Correctly update the internal model data
                            # self._data[row] is a tuple, so it needs to be reconstructed
                            updated_record_list = list(self._data[row])
                            updated_record_list[8] = new_status # EVALUATION_STATUS is at index 8 of the tuple from get_all_polygon_data_for_display
                            self._data[row] = tuple(updated_record_list)

                            # Emit dataChanged for the entire row to refresh all delegates if needed,
                            # though specifically for background role and display role of this cell.
                            row_start_index = self.index(row, 0)
                            row_end_index = self.index(row, self.columnCount() - 1)
                            self.dataChanged.emit(row_start_index, row_end_index)
                            main_window.log_message(f"Evaluation status for ID {db_id} updated to '{new_status}'.", "info")
                        else:
                            main_window.log_message(f"DB update failed for eval status ID {db_id} to {new_status}", "error")
                            QMessageBox.warning(main_window, "DB Error", "Failed to update evaluation status in database.")
                    else:
                        main_window.log_message("DB Manager not available for eval status update.", "error")
                        QMessageBox.critical(main_window, "Error", "DB Manager not available.")
                finally:
                    main_window.db_lock_manager.release_lock()
                return update_success
            else: # Lock not acquired
                lock_info = main_window.db_lock_manager.get_current_lock_info()
                holder_nickname = lock_info.get('holder_nickname', 'Unknown') if lock_info else 'Unknown'
                locked_op_desc = lock_info.get('operation_description', 'Unknown operation') if lock_info else 'Unknown'

                if lock_status == "STALE_LOCK_DETECTED":
                    main_window.log_message(f"Stale lock detected for eval status update (ID {db_id}). Held by {holder_nickname} for '{locked_op_desc}'.", "warning")
                    QMessageBox.warning(main_window, "Database Stale Lock",
                                        f"Database lock by {holder_nickname} for '{locked_op_desc}' appears stale. "
                                        "Editing in table is blocked. Try main window actions for override options if available.")
                elif lock_status is False: # Locked by another, not stale
                    main_window.log_message(f"DB locked by {holder_nickname} for '{locked_op_desc}'. Eval status for ID {db_id} not updated.", "error")
                    QMessageBox.warning(main_window, "Database Locked",
                                        f"Database is locked by {holder_nickname} for '{locked_op_desc}'. Please try again later.")
                elif lock_status == "ERROR":
                    main_window.log_message(f"Error acquiring lock for eval status update (ID {db_id}).", "error")
                    QMessageBox.critical(main_window, "Lock Error", "Could not acquire database lock due to an internal error.")
                # For any non-True lock_status, the operation did not proceed.
                return False

        return False

    def flags(self, index):
        flags = super().flags(index)
        if index.column() == self.CHECKBOX_COL: flags |= Qt.ItemFlag.ItemIsUserCheckable
        elif index.column() == self.EVALUATION_STATUS_COL:
            flags |= Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        else: flags |= Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        return flags

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal: return self._headers[section]
        if role == Qt.ItemDataRole.FontRole and orientation == Qt.Orientation.Horizontal: return QFont("Segoe UI", 9, QFont.Weight.Bold)
        return None

    def update_data(self, new_data_list):
        self.beginResetModel()
        self._data = new_data_list if new_data_list is not None else []
        current_ids = {row[0] for row in self._data if row}
        self._check_states = {db_id: state for db_id, state in self._check_states.items() if db_id in current_ids}
        self.endResetModel()

    def get_checked_item_db_ids(self): return [db_id for db_id, state in self._check_states.items() if state == Qt.CheckState.Checked]

    def set_all_checkboxes(self, state=Qt.CheckState.Checked):
        self.beginResetModel()
        for row_data in self._data:
            if row_data and len(row_data) > 0: self._check_states[row_data[0]] = state
        self.endResetModel()

# --- Filter Proxy Model ---
class PolygonFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_uuid_text = ""
        self.filter_export_status = "All"
        self.filter_error_status = "All"

    def set_uuid_filter(self, text): self.filter_uuid_text = text.lower(); self.invalidateFilter()
    def set_export_status_filter(self, status): self.filter_export_status = status; self.invalidateFilter()
    def set_error_status_filter(self, status): self.filter_error_status = status; self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        source_model = self.sourceModel()
        assert isinstance(source_model, PolygonTableModel)
        if not source_model or source_row >= len(source_model._data): return False
        record = source_model._data[source_row]
        if not record or len(record) < 17: return False

        if self.filter_uuid_text:
            uuid_val_from_record = record[1]
            if uuid_val_from_record is None or self.filter_uuid_text not in str(uuid_val_from_record).lower(): return False

        export_count_from_record = record[6]
        export_count = export_count_from_record if export_count_from_record is not None else 0
        if self.filter_export_status == "Exported" and export_count == 0: return False
        if self.filter_export_status == "Not Exported" and export_count > 0: return False

        kml_status_val_from_record = record[11]
        kml_status_val = str(kml_status_val_from_record).lower() if kml_status_val_from_record is not None else ""
        if self.filter_error_status == "Error Records" and not ("error" in kml_status_val or "deleted" in kml_status_val): return False
        elif self.filter_error_status == "Valid Records" and ("error" in kml_status_val or "deleted" in kml_status_val): return False

        return True

# --- Delegate for Evaluation Status ComboBox ---
class EvaluationStatusDelegate(QStyledItemDelegate):
    def __init__(self, parent=None): super().__init__(parent); self.options = ["Not Evaluated Yet", "Eligible", "Not Eligible"]
    def createEditor(self, parent_widget, option, index): editor = QComboBox(parent_widget); editor.addItems(self.options); return editor
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.ItemDataRole.DisplayRole)
        editor.setCurrentText(value if value in self.options else "Not Evaluated Yet")
    def setModelData(self, editor, model, index): model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)

# --- API Import Progress Dialog ---
class APIImportProgressDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Import Progress"); self.setModal(True); self.setMinimumWidth(400); self._was_cancelled = False
        layout = QVBoxLayout(self)
        self.total_label = QLabel("Total Records to Process: 0"); layout.addWidget(self.total_label)
        self.processed_label = QLabel("Records Processed (Attempted): 0"); layout.addWidget(self.processed_label)
        self.new_added_label = QLabel("New Records Added: 0"); layout.addWidget(self.new_added_label)
        self.skipped_label = QLabel("Records Skipped (Duplicates/Errors): 0"); layout.addWidget(self.skipped_label)
        self.progress_bar = QProgressBar(); self.progress_bar.setRange(0, 0); self.progress_bar.setValue(0); layout.addWidget(self.progress_bar)
        self.cancel_button = QPushButton("Cancel"); self.cancel_button.clicked.connect(self._perform_cancel); layout.addWidget(self.cancel_button)
        self.setLayout(layout)
    def _perform_cancel(self): self._was_cancelled = True; self.reject()
    def set_total_records(self, count): self.total_label.setText(f"Total Records to Process: {count}"); self.progress_bar.setRange(0, count if count > 0 else 100)
    def update_progress(self,p,s,n): self.processed_label.setText(f"Records Processed (Attempted): {p}"); self.new_added_label.setText(f"New Records Added: {n}"); self.skipped_label.setText(f"Records Skipped (Duplicates/Errors): {s}"); self.progress_bar.setValue(p); QApplication.processEvents()
    def was_cancelled(self): return self._was_cancelled

class MainWindow(QMainWindow):
    def __init__(self, db_manager, credential_manager):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME_MW} - {APP_VERSION_MW}")
        self.app_icon_path = resource_path(APP_ICON_FILE_NAME_MW)
        if os.path.exists(self.app_icon_path): self.setWindowIcon(QIcon(self.app_icon_path))
        self.db_manager = db_manager; self.credential_manager = credential_manager
        if self.db_manager is None: QMessageBox.critical(self, "Initialization Error", "Database Manager not provided."); sys.exit(1)
        if self.credential_manager is None: QMessageBox.critical(self, "Initialization Error", "Credential Manager not provided."); sys.exit(1)

        # Initialize DatabaseLockManager (Basic from previous subtask)
        self.db_lock_manager = None
        if self.db_manager and self.credential_manager:
            db_path = self.credential_manager.get_db_path()
            if db_path:
                self.db_lock_manager = DatabaseLockManager(db_path, self.credential_manager)
                # self.log_message("DatabaseLockManager initialized.", "info") # Logging will be added later
            else:
                # self.log_message("Failed to initialize DatabaseLockManager: DB path not found.", "error")
                QMessageBox.critical(self, "Locking Error", "Could not initialize database lock manager: DB path missing.")
        else:
            # self.log_message("Failed to initialize DatabaseLockManager: DB Manager or Credential Manager missing.", "error")
            QMessageBox.critical(self, "Locking Error", "Could not initialize database lock manager: core components missing.")

        self.db_lock_retry_timer = QTimer(self)
        self.db_lock_retry_timer.setSingleShot(True)
        # Actual connection of timeout signal and advanced retry attributes will be in a later step.

        self.resize(1200, 800); self._center_window()
        self._create_main_layout(); self._create_header(); self._create_menus_and_toolbar(); self._create_status_bar()
        self.current_temp_kml_path = None; self.show_ge_instructions_popup_again = True
        self._setup_main_content_area(); self.load_data_into_table()
        self.log_message(f"{APP_NAME_MW} {APP_VERSION_MW} started. DB at: {self.db_manager.db_path}", "info")

    def _center_window(self):
        if self.screen(): screen_geo = self.screen().geometry(); self.move((screen_geo.width()-self.width())//2, (screen_geo.height()-self.height())//2)
    def _create_main_layout(self): self.central_widget = QWidget(); self.setCentralWidget(self.central_widget); self.main_layout = QVBoxLayout(self.central_widget); self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)
    def _create_header(self):
        header_widget = QWidget(); header_widget.setFixedHeight(60); header_widget.setStyleSheet("border-bottom: 1px solid #D0D0D0;")
        header_layout = QHBoxLayout(header_widget); header_layout.setContentsMargins(5,5,5,5); header_layout.setSpacing(5)
        logo_path = resource_path(LOGO_FILE_NAME_MW)
        if os.path.exists(logo_path): pixmap=QPixmap(logo_path);logo_label=QLabel();logo_label.setPixmap(pixmap.scaled(40,40,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)); header_layout.addWidget(logo_label,0,Qt.AlignmentFlag.AlignVCenter)
        else: header_layout.addWidget(QLabel("[L]"))
        title_label=QLabel(APP_NAME_MW);title_label.setFont(QFont("Segoe UI",16,QFont.Weight.Bold));title_label.setAlignment(Qt.AlignmentFlag.AlignCenter);header_layout.addWidget(title_label,1)
        version_label=QLabel(APP_VERSION_MW);version_label.setFont(QFont("Segoe UI",8,QFont.Weight.Normal,True));version_label.setStyleSheet(f"color:{INFO_COLOR_MW};");header_layout.addWidget(version_label,0,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(header_widget)
    def _create_menus_and_toolbar(self):
        menubar=self.menuBar();file_menu=menubar.addMenu("&File")
        self.export_data_action=QAction(QIcon.fromTheme("document-save-as",QIcon(self.app_icon_path)),"Export Displayed Data as &CSV...",self);self.export_data_action.triggered.connect(self.handle_export_displayed_data_csv);file_menu.addAction(self.export_data_action)
        file_menu.addSeparator();exit_action=QAction(QIcon.fromTheme("application-exit"),"E&xit",self);exit_action.setShortcut("Ctrl+Q");exit_action.setStatusTip("Exit application");exit_action.triggered.connect(self.close);file_menu.addAction(exit_action)
        data_menu=menubar.addMenu("&Data");self.import_csv_action=QAction(QIcon.fromTheme("document-open"),"Import &CSV...",self);self.import_csv_action.triggered.connect(self.handle_import_csv);data_menu.addAction(self.import_csv_action)
        self.fetch_api_action=QAction(QIcon.fromTheme("network-transmit-receive"),"&Fetch from API...",self);self.fetch_api_action.triggered.connect(lambda:self.handle_fetch_from_api());data_menu.addAction(self.fetch_api_action)
        self.manage_api_action=QAction(QIcon.fromTheme("preferences-system"),"Manage A&PI Sources...",self);self.manage_api_action.triggered.connect(self.handle_manage_api_sources);data_menu.addAction(self.manage_api_action);data_menu.addSeparator()
        self.delete_checked_action=QAction(QIcon.fromTheme("edit-delete"),"Delete Checked Rows...",self);self.delete_checked_action.triggered.connect(self.handle_delete_checked_rows);data_menu.addAction(self.delete_checked_action)
        self.clear_all_data_action=QAction(QIcon.fromTheme("edit-clear-all"),"Clear All Polygon Data...",self);self.clear_all_data_action.triggered.connect(self.handle_clear_all_data);data_menu.addAction(self.clear_all_data_action)
        kml_menu=menubar.addMenu("&KML");self.generate_kml_action=QAction(QIcon.fromTheme("document-export"),"&Generate KML for Checked Rows...",self);self.generate_kml_action.triggered.connect(self.handle_generate_kml);kml_menu.addAction(self.generate_kml_action)

        self.view_menu=menubar.addMenu("&View")
        self.toggle_ge_view_action=QAction("Google Earth View",self);self.toggle_ge_view_action.setCheckable(True);self.toggle_ge_view_action.toggled.connect(self._handle_ge_view_toggle);self.view_menu.addAction(self.toggle_ge_view_action)
        self.view_menu.addSeparator()
        self.default_kml_view_settings_action = QAction("Default KML View Settings...", self)
        self.default_kml_view_settings_action.triggered.connect(self.open_default_kml_view_settings_dialog)
        self.view_menu.addAction(self.default_kml_view_settings_action)

        help_menu=menubar.addMenu("&Help");self.about_action=QAction(QIcon.fromTheme("help-about"),"&About",self);self.about_action.triggered.connect(self.handle_about);help_menu.addAction(self.about_action)
        self.ge_instructions_action=QAction("GE &Instructions",self);self.ge_instructions_action.triggered.connect(self.handle_show_ge_instructions);help_menu.addAction(self.ge_instructions_action)
        self.toolbar=QToolBar("Main Toolbar");self.toolbar.setIconSize(QSize(20,20));self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon);self.toolbar.setMovable(True);self.addToolBar(Qt.ToolBarArea.TopToolBarArea,self.toolbar)
        self.toolbar.addAction(self.import_csv_action);self.toolbar.addSeparator()
        self.toggle_ge_view_button=QPushButton("GE View: OFF");self.toggle_ge_view_button.setCheckable(True);self.toggle_ge_view_button.toggled.connect(self._handle_ge_view_toggle);self.toolbar.addWidget(self.toggle_ge_view_button);self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel(" API Source: "));self.api_source_combo_toolbar=QComboBox();self.api_source_combo_toolbar.setMinimumWidth(150);self.refresh_api_source_dropdown();self.toolbar.addWidget(self.api_source_combo_toolbar)
        fetch_api_toolbar_action=QAction(QIcon.fromTheme("network-transmit-receive"),"&Fetch from Selected API",self);fetch_api_toolbar_action.triggered.connect(lambda:self.handle_fetch_from_api());self.toolbar.addAction(fetch_api_toolbar_action)
        manage_api_toolbar_action=QAction(QIcon.fromTheme("preferences-system"),"Manage API Sources",self);manage_api_toolbar_action.triggered.connect(self.handle_manage_api_sources);self.toolbar.addAction(manage_api_toolbar_action)
        self.toolbar.addSeparator();self.toolbar.addAction(self.generate_kml_action);self.toolbar.addAction(self.delete_checked_action)
    def _create_status_bar(self): self._main_status_bar=QStatusBar();self.setStatusBar(self._main_status_bar);self._main_status_bar.showMessage("Ready.",3000)

    def _setup_filter_panel(self):
        self.filter_groupbox = QGroupBox("Filters")
        self.filter_groupbox.setCheckable(False)
        self.filter_groupbox.setStyleSheet("""
            QGroupBox {
                border: 1px solid #B0B0B0; /* Lighter border than default */
                border-radius: 8px; /* Rounded edges */
                margin-top: 7px; /* Space for title */
                background-color: #F0F0F0; /* Slightly darker than typical window background */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px 0 5px;
                /* background-color: transparent; */ /* Often needed */
            }
        """)

        self.filter_widgets_container = QWidget()
        filter_layout = QGridLayout(self.filter_widgets_container)
        filter_layout.setContentsMargins(5,5,5,5)
        filter_layout.setSpacing(5)

        filter_layout.addWidget(QLabel("Filter UUID:"), 0, 0)
        self.uuid_filter_edit = QLineEdit(); self.uuid_filter_edit.setPlaceholderText("Contains...")
        # self.uuid_filter_edit.textChanged.connect(self.apply_filters) # Will be connected to Apply button
        filter_layout.addWidget(self.uuid_filter_edit, 0, 1, 1, 3)

        filter_layout.addWidget(QLabel("Export Status:"), 1, 0)
        self.export_status_combo = QComboBox(); self.export_status_combo.addItems(["All", "Exported", "Not Exported"])
        # self.export_status_combo.currentIndexChanged.connect(self.apply_filters) # Will be connected to Apply button
        filter_layout.addWidget(self.export_status_combo, 1, 1)

        filter_layout.addWidget(QLabel("Record Status:"), 1, 2)
        self.error_status_combo = QComboBox(); self.error_status_combo.addItems(["All", "Valid Records", "Error Records"])
        # self.error_status_combo.currentIndexChanged.connect(self.apply_filters) # Will be connected to Apply button
        filter_layout.addWidget(self.error_status_combo, 1, 3)

        # Buttons on row 2
        self.apply_filters_button = QPushButton("Apply Filters")
        self.apply_filters_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.apply_filters_button.setStyleSheet("""
            QPushButton {
                background-color: #E0EFFF; border: 1px solid #A0CFFF;
                padding: 5px 10px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #C0DFFF; }
            QPushButton:pressed { background-color: #A0CFFF; }
        """)
        self.apply_filters_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(self.apply_filters_button, 2, 0, 1, 2)

        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.clear_filters_button.setStyleSheet("""
            QPushButton {
                background-color: #E0EFFF; border: 1px solid #A0CFFF;
                padding: 5px 10px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #C0DFFF; }
            QPushButton:pressed { background-color: #A0CFFF; }
        """)
        self.clear_filters_button.clicked.connect(self.clear_filters)
        filter_layout.addWidget(self.clear_filters_button, 2, 2, 1, 2)

        filter_layout.setColumnStretch(1, 1); filter_layout.setColumnStretch(3, 1)

        groupbox_main_layout = QVBoxLayout(self.filter_groupbox)
        groupbox_main_layout.setContentsMargins(0,5,0,0)
        groupbox_main_layout.addWidget(self.filter_widgets_container)

        self.filter_groupbox.setVisible(False)
        return self.filter_groupbox

    def _toggle_filter_panel_visibility(self):
        if hasattr(self, 'filter_groupbox'):
            is_visible = self.filter_groupbox.isVisible()
            self.filter_groupbox.setVisible(not is_visible)

    def apply_filters(self):
        if not hasattr(self, 'filter_proxy_model'): return
        self.filter_proxy_model.set_uuid_filter(self.uuid_filter_edit.text())
        self.filter_proxy_model.set_export_status_filter(self.export_status_combo.currentText())
        self.filter_proxy_model.set_error_status_filter(self.error_status_combo.currentText())
        if hasattr(self, 'filter_groupbox') and self.filter_groupbox.isVisible():
            self.filter_groupbox.setVisible(False)

    def clear_filters(self):
        self.uuid_filter_edit.clear()
        self.export_status_combo.setCurrentIndex(0)
        self.error_status_combo.setCurrentIndex(0)
        self.apply_filters()

    def _setup_main_content_area(self):
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        # Pass credential_manager to MapViewWidget constructor
        self.map_view_widget = MapViewWidget(self.credential_manager, self); self.map_view_widget.setMinimumWidth(300)
        self.google_earth_view_widget = GoogleEarthWebViewWidget(self); self.google_earth_view_widget.setMinimumWidth(300)
        self.map_stack = QStackedWidget(self); self.map_stack.addWidget(self.map_view_widget); self.map_stack.addWidget(self.google_earth_view_widget)
        self.main_splitter.addWidget(self.map_stack)
        right_pane_widget = QWidget(); right_pane_layout = QVBoxLayout(right_pane_widget); right_pane_layout.setContentsMargins(10,0,10,10)

        self.table_editors_strip = QWidget()
        strip_layout = QHBoxLayout(self.table_editors_strip)
        strip_layout.setContentsMargins(0,0,0,0); strip_layout.addStretch()
        self.toggle_filter_panel_button = QPushButton(" Filters")
        self.toggle_filter_panel_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.toggle_filter_panel_button.setStyleSheet("padding: 3px;")
        self.toggle_filter_panel_button.clicked.connect(self._toggle_filter_panel_visibility)
        strip_layout.addWidget(self.toggle_filter_panel_button)
        right_pane_layout.addWidget(self.table_editors_strip)

        filter_panel_widget = self._setup_filter_panel()
        right_pane_layout.addWidget(filter_panel_widget)

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        table_container = QWidget(); table_layout = QVBoxLayout(table_container); table_layout.setContentsMargins(0,0,0,0)
        checkbox_header_layout = QHBoxLayout(); self.select_all_checkbox = QCheckBox("Select/Deselect All"); self.select_all_checkbox.stateChanged.connect(self.toggle_all_checkboxes); checkbox_header_layout.addWidget(self.select_all_checkbox); checkbox_header_layout.addStretch(); table_layout.addLayout(checkbox_header_layout)
        self.table_view = QTableView(); self.source_model = PolygonTableModel(parent=self, db_manager_instance=self.db_manager); self.filter_proxy_model = PolygonFilterProxyModel(self); self.filter_proxy_model.setSourceModel(self.source_model); self.table_view.setModel(self.filter_proxy_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.SelectedClicked); self.table_view.horizontalHeader().setStretchLastSection(True); self.table_view.setAlternatingRowColors(False); self.table_view.setSortingEnabled(True); self.table_view.sortByColumn(self.source_model.DATE_ADDED_COL,Qt.SortOrder.DescendingOrder)
        evaluation_delegate = EvaluationStatusDelegate(self.table_view); self.table_view.setItemDelegateForColumn(self.source_model.EVALUATION_STATUS_COL, evaluation_delegate)
        self.table_view.setColumnWidth(self.source_model.CHECKBOX_COL,30); self.table_view.setColumnWidth(self.source_model.DB_ID_COL,50); self.table_view.setColumnWidth(self.source_model.UUID_COL,130); self.table_view.setColumnWidth(self.source_model.RESPONSE_CODE_COL,120); self.table_view.setColumnWidth(self.source_model.EVALUATION_STATUS_COL,150); self.table_view.setColumnWidth(self.source_model.FARMER_NAME_COL,150); self.table_view.setColumnWidth(self.source_model.VILLAGE_COL,120); self.table_view.setColumnWidth(self.source_model.DATE_ADDED_COL,140); self.table_view.setColumnWidth(self.source_model.KML_FILE_NAME_COL,150); self.table_view.setColumnWidth(self.source_model.KML_FILE_STATUS_COL,110); self.table_view.setColumnWidth(self.source_model.EDIT_COUNT_COL,90); self.table_view.setColumnWidth(self.source_model.LAST_EDIT_DATE_COL,140); self.table_view.setColumnWidth(self.source_model.EDITOR_DEVICE_ID_COL,130); self.table_view.setColumnWidth(self.source_model.EDITOR_NICKNAME_COL,130); self.table_view.setColumnWidth(self.source_model.DEVICE_CODE_COL,140); self.table_view.setColumnWidth(self.source_model.EXPORT_COUNT_COL,100); self.table_view.setColumnWidth(self.source_model.LAST_EXPORTED_COL,140); self.table_view.setColumnWidth(self.source_model.LAST_MODIFIED_COL,140)
        table_layout.addWidget(self.table_view); self.right_splitter.addWidget(table_container); self.table_view.selectionModel().selectionChanged.connect(self.on_table_selection_changed)
        log_container = QWidget(); log_layout = QVBoxLayout(log_container); log_layout.setContentsMargins(0,10,0,0); log_label = QLabel("Status and Logs:"); log_layout.addWidget(log_label); self.log_text_edit_qt_actual = QTextEdit(); self.log_text_edit_qt_actual.setReadOnly(True); self.log_text_edit_qt_actual.setFont(QFont("Segoe UI",9)); log_layout.addWidget(self.log_text_edit_qt_actual); self.right_splitter.addWidget(log_container)
        self.right_splitter.setStretchFactor(0,3); self.right_splitter.setStretchFactor(1,1); right_pane_layout.addWidget(self.right_splitter,1); self.main_splitter.addWidget(right_pane_widget)
        self.main_splitter.setStretchFactor(0,1); self.main_splitter.setStretchFactor(1,2); self.main_layout.addWidget(self.main_splitter,1)

    def toggle_all_checkboxes(self,state_int): self.source_model.set_all_checkboxes(Qt.CheckState(state_int))
    def on_table_selection_changed(self,selected,deselected):
        selected_proxy_indexes=self.table_view.selectionModel().selectedRows(); polygon_record=None
        if selected_proxy_indexes:
            source_model_index=self.filter_proxy_model.mapToSource(selected_proxy_indexes[0])
            if source_model_index.isValid():
                db_id_item=self.source_model.data(source_model_index.siblingAtColumn(self.source_model.DB_ID_COL))
                try: db_id=int(db_id_item); polygon_record=self.db_manager.get_polygon_data_by_id(db_id)
                except(ValueError,TypeError):self.log_message(f"Map/GE: Invalid ID for selected row.","error");polygon_record=None
                except Exception as e:self.log_message(f"Map/GE: Error fetching record: {e}","error");polygon_record=None
        if self.map_stack.currentIndex()==1:
            if polygon_record and polygon_record.get('status')=='valid_for_kml': self._trigger_ge_polygon_upload(polygon_record)
            else: self.log_message("GE View: No valid polygon record selected or record not valid for KML upload.","warning")
        else:
            if polygon_record and polygon_record.get('status')=='valid_for_kml':
                coords_lat_lon,utm_valid=[],True
                for i in range(1,5):
                    e,n=polygon_record.get(f'p{i}_easting'),polygon_record.get(f'p{i}_northing');zn,zl=polygon_record.get(f'p{i}_zone_num'),polygon_record.get(f'p{i}_zone_letter')
                    if None in[e,n,zn,zl]:utm_valid=False;break
                    try:lat,lon=utm.to_latlon(e,n,zn,zl);coords_lat_lon.append((lat,lon))
                    except Exception as e_conv:self.log_message(f"Map: UTM conv fail {polygon_record.get('uuid')},P{i}:{e_conv}","error");utm_valid=False;break
                if utm_valid and len(coords_lat_lon)==4:self.map_view_widget.display_polygon(coords_lat_lon,coords_lat_lon[0])
                elif hasattr(self,'map_view_widget'):self.map_view_widget.clear_map()
            # End of existing UTM to Lat/Lon conversion block for map_view_widget
            # Add new KML loading logic here:
            elif polygon_record: # Record exists, but might not be 'valid_for_kml' or UTM conversion failed
                kml_file_name = polygon_record.get('kml_file_name')
                main_kml_folder_path = self.credential_manager.get_kml_folder_path()

                if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip() and main_kml_folder_path:
                    full_kml_path = os.path.join(main_kml_folder_path, kml_file_name.strip())
                    if os.path.exists(full_kml_path):
                        self.map_view_widget.load_kml_for_display(full_kml_path)
                    else:
                        # KML file does not exist
                        self.log_message(f"KML file '{kml_file_name}' not found at '{full_kml_path}'. Updating status.", "warning")
                        if hasattr(self, 'map_view_widget'): self.map_view_widget.clear_map()
                        # db_id is already available from the earlier part of the method
                        if db_id is not None:
                             # This DB method (update_kml_file_status) will be implemented in a later task.
                             # For now, the call is placed here.
                            self.db_manager.update_kml_file_status(db_id, "File Deleted")
                            self.load_data_into_table() # Refresh table to show updated status
                        else:
                            self.log_message("DB ID not found for selected row, cannot update KML file status.", "error")
                else:
                    # kml_file_name is empty, invalid, or folder path is missing
                    if hasattr(self, 'map_view_widget'): self.map_view_widget.clear_map()
                    if not main_kml_folder_path:
                        self.log_message("KML folder path not configured. Cannot load KML.", "warning")
                    elif not kml_file_name or not isinstance(kml_file_name, str) or not kml_file_name.strip():
                         self.log_message(f"No KML file name for selected record (DB ID: {db_id if db_id is not None else 'Unknown'}). Clearing map.", "info")

            elif hasattr(self,'map_view_widget'):self.map_view_widget.clear_map() # Default clear if no valid record

    def refresh_api_source_dropdown(self):
        if hasattr(self,'api_source_combo_toolbar'):
            current_text=self.api_source_combo_toolbar.currentText();self.api_source_combo_toolbar.clear();sources=self.db_manager.get_mwater_sources()
            for sid,title,url in sources:self.api_source_combo_toolbar.addItem(title,userData=url)
            index=self.api_source_combo_toolbar.findText(current_text)
            if index!=-1:self.api_source_combo_toolbar.setCurrentIndex(index)
            elif sources:self.api_source_combo_toolbar.setCurrentIndex(0)
    def handle_manage_api_sources(self):dialog=APISourcesDialog(self,self.db_manager);dialog.exec();self.refresh_api_source_dropdown()
    def handle_import_csv(self):
        filepath,_=QFileDialog.getOpenFileName(self,"Select CSV File",os.path.expanduser("~/Documents"),"CSV files (*.csv);;All files (*.*)")
        if not filepath:return;self.log_message(f"Loading CSV: {filepath}","info")
        try:
            with open(filepath,mode='r',encoding='utf-8-sig')as csvfile:reader=csv.DictReader(csvfile);self._process_imported_data(list(reader),f"CSV '{os.path.basename(filepath)}'")
        except Exception as e:self.log_message(f"Error reading CSV '{filepath}': {e}","error");QMessageBox.critical(self,"CSV Error",f"Could not read CSV file:\n{e}")
    def handle_fetch_from_api(self,url=None,title=None):
        selected_api_url,selected_api_title=None,None
        if url and title:selected_api_url,selected_api_title=url,title;self.log_message(f"Fetching directly from API (via dialog):{selected_api_title}...","info")
        else:
            selected_api_title=self.api_source_combo_toolbar.currentText();selected_api_url=self.api_source_combo_toolbar.currentData()
            if not selected_api_url:QMessageBox.information(self,"API Fetch","No API source selected from dropdown or URL is missing.");return
            self.log_message(f"Fetching from selected API (dropdown):{selected_api_title}...","info")
        rows_from_api,error_msg=fetch_data_from_mwater_api(selected_api_url,selected_api_title)
        if error_msg:self.log_message(f"API Fetch Error ({selected_api_title}):{error_msg}","error");QMessageBox.warning(self,"API Fetch Error",error_msg);return
        if rows_from_api is not None:self._process_imported_data(rows_from_api,selected_api_title,is_api_data=True,api_map=API_FIELD_TO_DB_FIELD_MAP)
        else:self.log_message(f"No data returned or error for {selected_api_title}.","info")
    def _process_imported_data(self,row_list,source_description,is_api_data=False,api_map=None):
        if not row_list:self.log_message(f"No data rows found in {source_description}.","info");return
        if is_api_data and not api_map:self.log_message(f"API data processing aborted: api_map not provided for {source_description}.","error");QMessageBox.critical(self,"Processing Error","API map is missing for API data processing.");return
        if is_api_data:
            cleaned_row_list=[]
            for api_row_original_keys in row_list:cleaned_row_list.append({k.lstrip('\ufeff'):v for k,v in api_row_original_keys.items()})
            row_list=cleaned_row_list;self.log_message("Cleaned BOM characters from API data keys.","info")
            if row_list:self.log_message(f"API Data Keys (first row after BOM cleaning):{list(row_list[0].keys())}","info")
        if not self.credential_manager:self.log_message("Credential Manager not available.","error");QMessageBox.critical(self,"Error","Credential Manager not available.");return
        kml_root_path,device_id,device_nickname=self.credential_manager.get_kml_folder_path(),self.credential_manager.get_device_id(),self.credential_manager.get_device_nickname()
        if not kml_root_path or not device_id:self.log_message("KML root path or device ID not set.","error");QMessageBox.warning(self,"Configuration Error","KML root path or device ID not set.");return
        progress_dialog=APIImportProgressDialog(self);progress_dialog.set_total_records(len(row_list));progress_dialog.show()
        processed_in_loop,skipped_in_loop,new_added_in_loop=0,0,0
        for i,original_row_dict in enumerate(row_list):
            processed_in_loop+=1;current_errors=[];rc_from_row=""
            if is_api_data and api_map:
                api_rc_key=next((k for k,v in api_map.items()if v=="response_code"),None)
                if api_rc_key:rc_from_row=original_row_dict.get(api_rc_key,"").strip()
            else:
                response_code_header_key=CSV_HEADERS["response_code"]
                for k,v_csv in original_row_dict.items():
                    if k.lstrip('\ufeff')==response_code_header_key:rc_from_row=v_csv.strip()if v_csv else"";break
            if not rc_from_row:self.log_message(f"Row {i+1} from {source_description} skipped: Missing Response Code.","error");current_errors.append("Missing Response Code.");skipped_in_loop+=1;progress_dialog.update_progress(processed_in_loop,skipped_in_loop,new_added_in_loop);
            if progress_dialog.was_cancelled():break;continue
            if self.db_manager.check_duplicate_response_code(rc_from_row):self.log_message(f"Skipped duplicate RC '{rc_from_row}'.","info");skipped_in_loop+=1;progress_dialog.update_progress(processed_in_loop,skipped_in_loop,new_added_in_loop);
            if progress_dialog.was_cancelled():break;continue
            processed_flat=process_api_row_data(original_row_dict,api_map)if is_api_data and api_map else process_csv_row_data(original_row_dict)
            if not processed_flat.get("uuid"):generated_uuid=str(uuid.uuid4());self.log_message(f"UUID missing for RC '{rc_from_row}'. Generated: {generated_uuid}","warning");current_errors.append(f"UUID missing,generated:{generated_uuid}");processed_flat["uuid"]=generated_uuid
            if processed_flat.get('error_messages'):
                if isinstance(processed_flat['error_messages'],str):current_errors.append(f"Data processing issues:{processed_flat['error_messages']}")
                elif isinstance(processed_flat['error_messages'],list):current_errors.extend(processed_flat['error_messages'])
            kml_file_name,kml_content_ok,kml_saved_successfully=f"{processed_flat['uuid']}.kml",False,False
            if processed_flat.get('status')=='valid_for_kml':
                kml_doc=simplekml.Kml()
                try:
                    kml_content_ok=add_polygon_to_kml_object(kml_doc,processed_flat)
                    if not kml_content_ok:current_errors.append("Failed KML content gen.")
                except Exception as e_kml_gen:kml_content_ok=False;current_errors.append(f"KML gen exception:{e_kml_gen}");self.log_message(f"KML Gen Ex for {processed_flat['uuid']}:{e_kml_gen}","error")
                if kml_content_ok:
                    full_kml_path=os.path.join(kml_root_path,kml_file_name)
                    try:kml_doc.save(full_kml_path);kml_saved_successfully=True;self.log_message(f"KML saved:{full_kml_path}","info")
                    except Exception as e_kml_save:kml_saved_successfully=False;error_msg=f"Failed KML save'{full_kml_path}':{e_kml_save}";current_errors.append(error_msg);self.log_message(error_msg,"error")
            else:msg=f"Skipping KML gen for RC'{rc_from_row}'(UUID {processed_flat['uuid']}),status:'{processed_flat.get('status')}'";current_errors.append(msg);self.log_message(msg,"info")
            db_data=processed_flat.copy();db_data['kml_file_name']=kml_file_name;db_data['kml_file_status']="Created"if kml_saved_successfully else"Errored"
            api_device_code=processed_flat.get('device_code');db_data['device_code']=api_device_code if api_device_code else device_id
            db_data['editor_device_id']=device_id;db_data['editor_device_nickname']=device_nickname;db_data.pop('status',None)
            final_error_messages="\n".join(filter(None,current_errors));db_data['error_messages']=final_error_messages if final_error_messages else None
            db_data["last_modified"]=datetime.datetime.now().isoformat()
            existing_date_added=processed_flat.get("date_added")
            if existing_date_added and isinstance(existing_date_added,str)and existing_date_added.strip():db_data["date_added"]=existing_date_added
            else:db_data["date_added"]=datetime.datetime.now().isoformat()
            db_result_id=self.db_manager.add_or_update_polygon_data(db_data,overwrite=False)
            if db_result_id is not None:new_added_in_loop+=1;self.log_message(f"RC'{rc_from_row}'(UUID {db_data['uuid']})saved to DB ID {db_result_id}.KML:{db_data['kml_file_status']}.","info")
            else:self.log_message(f"Failed to save RC'{rc_from_row}'(UUID {db_data['uuid']})to DB.","error");skipped_in_loop+=1
            progress_dialog.update_progress(processed_in_loop,skipped_in_loop,new_added_in_loop)
            if progress_dialog.was_cancelled():self.log_message("Import cancelled by user.","info");break
        progress_dialog.close();self.load_data_into_table();self.log_message(f"Import from {source_description}:Attempted:{processed_in_loop},New Added:{new_added_in_loop},Skipped:{skipped_in_loop}.","info")
    def handle_export_displayed_data_csv(self):
        model_to_export=self.table_view.model()
        if not model_to_export or model_to_export.rowCount()==0:QMessageBox.information(self,"Export Data","No data to export.");return
        filepath,_=QFileDialog.getSaveFileName(self,"Save Displayed Data As CSV",os.path.expanduser("~/Documents/dilasa_displayed_data.csv"),"CSV Files (*.csv)")
        if not filepath:return
        try:
            headers=self.source_model._headers
            with open(filepath,'w',newline='',encoding='utf-8-sig')as csvfile:
                writer=csv.writer(csvfile);writer.writerow(headers[1:])
                for row in range(model_to_export.rowCount()):row_data=[model_to_export.data(model_to_export.index(row,col))for col in range(1,model_to_export.columnCount())];writer.writerow(row_data)
            self.log_message(f"Data exported to {filepath}","success");QMessageBox.information(self,"Export Successful",f"{model_to_export.rowCount()} displayed records exported to:\n{filepath}")
        except Exception as e:self.log_message(f"Error exporting CSV:{e}","error");QMessageBox.critical(self,"Export Error",f"Could not export data:{e}")
    def handle_delete_checked_rows(self):
        checked_ids = self.source_model.get_checked_item_db_ids()
        if not checked_ids:
            QMessageBox.information(self, "Delete Checked", "No records checked.")
            return

        def _do_delete():
            # Confirmation is part of the operation, so it's inside the callable
            if QMessageBox.question(self, "Confirm Delete", f"Delete {len(checked_ids)} checked record(s) permanently?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                if self.db_manager.delete_polygon_data(checked_ids):
                    self.log_message(f"{len(checked_ids)} checked record(s) deleted.", "info")
                    self.load_data_into_table() # This should be called only if db_operation returned True
                    return True # Indicate success for _execute_db_operation_with_lock
                else:
                    self.log_message("Failed to delete records.", "error")
                    QMessageBox.warning(self, "DB Error", "Could not delete records.")
                    return False # Indicate failure
            else:
                self.log_message("Delete operation cancelled by user.", "info")
                return False # Indicate operation was not performed / "failed" from lock perspective

        # The success of load_data_into_table is now handled by the return of _do_delete
        self._execute_db_operation_with_lock(
            operation_callable=_do_delete,
            operation_desc="Deleting checked rows",
            lock_duration=30,
            retry_callable_for_timer=self.handle_delete_checked_rows
        )

    def handle_clear_all_data(self):
        if not self.db_lock_manager:
            self.log_message("Database Lock Manager not available. Cannot clear data.", "error")
            QMessageBox.critical(self, "Critical Error", "Database Lock Manager is not initialized. Please restart the application.")
            return

        def _do_clear():
            if QMessageBox.question(self, "Confirm Clear All", "Delete ALL polygon data permanently?\nThis cannot be undone.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                if self.db_manager.delete_all_polygon_data():
                    self.log_message("All polygon data deleted.", "info")
                    self.source_model._check_states.clear() # Clear local check states
                    # self.load_data_into_table() # Will be called if _execute returns True
                    return True # Indicate success
                else:
                    self.log_message("Failed to clear all data from database.", "error")
                    QMessageBox.warning(self, "DB Error", "Could not clear all data from the database.")
                    return False # Indicate failure
            else:
                self.log_message("Clear all data operation cancelled by user.", "info")
                return False # Indicate operation was not performed

        if self._execute_db_operation_with_lock(
            operation_callable=_do_clear,
            operation_desc="Clearing all polygon data",
            lock_duration=60, # Slightly longer for a full clear
            retry_callable_for_timer=self.handle_clear_all_data
        ):
            self.load_data_into_table()

    def handle_generate_kml(self):
        checked_ids = self.source_model.get_checked_item_db_ids()
        if not checked_ids:
            QMessageBox.information(self, "Generate KML", "No records checked.")
            return

        records_data = [self.db_manager.get_polygon_data_by_id(db_id) for db_id in checked_ids]
        valid_for_kml = [r for r in records_data if r and r.get('status') == 'valid_for_kml']
        if not valid_for_kml:
            QMessageBox.information(self, "Generate KML", "Checked records not valid for KML.")
            return

        output_folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", os.path.expanduser("~/Documents"))
        if not output_folder:
            self.log_message("KML generation cancelled (folder selection).", "info")
            return

        output_mode_dialog = OutputModeDialog(self)
        kml_output_mode = output_mode_dialog.get_selected_mode()
        if not kml_output_mode: # User cancelled dialog
            self.log_message("KML generation cancelled (mode selection).", "info")
            return

        if not self.db_lock_manager:
            self.log_message("Database Lock Manager not available. Cannot generate KML.", "error")
            QMessageBox.critical(self, "Critical Error", "Database Lock Manager is not initialized. Please restart the application.")
            return

        def _do_kml_generation():
            # This inner function will only be called if the lock is acquired.
            self.log_message(f"Generating KMLs to: {output_folder} (Mode: {kml_output_mode})", "info")
            files_gen, ids_gen = 0, []
            heartbeat_interval_kml = 10  # records
            operation_successful = True

            try:
                if kml_output_mode == "single":
                    ts = datetime.datetime.now().strftime('%d.%m.%y')
                    fn = f"Consolidate_ALL_KML_{ts}_{len(valid_for_kml)}.kml"
                    doc = simplekml.Kml(name=f"Consolidated - {ts}")
                    for idx, pd in enumerate(valid_for_kml):
                        if idx > 0 and idx % heartbeat_interval_kml == 0: self.db_lock_manager.update_heartbeat()
                        if add_polygon_to_kml_object(doc, pd): ids_gen.append(pd['id'])
                    if doc.features: doc.save(os.path.join(output_folder, fn)); files_gen = 1
                elif kml_output_mode == "multiple":
                    for idx, pd in enumerate(valid_for_kml):
                        if idx > 0 and idx % heartbeat_interval_kml == 0: self.db_lock_manager.update_heartbeat()
                        doc = simplekml.Kml(name=pd['uuid'])
                        if add_polygon_to_kml_object(doc, pd):
                            doc.save(os.path.join(output_folder, f"{pd['uuid']}.kml"))
                            ids_gen.append(pd['id']); files_gen += 1

                for idx, rid in enumerate(ids_gen):
                    if idx > 0 and idx % heartbeat_interval_kml == 0: self.db_lock_manager.update_heartbeat()
                    self.db_manager.update_kml_export_status(rid)

                if ids_gen: self.load_data_into_table() # Refresh only if changes were made
                msg = f"{files_gen} KMLs generated for {len(ids_gen)} records." if files_gen > 0 else "No KMLs generated."
                self.log_message(msg, "success" if files_gen > 0 else "info")
                QMessageBox.information(self, "KML Generation", msg)
            except Exception as e_kml: # Catch specific KML/DB errors within the operation
                self.log_message(f"Error during KML generation/DB update: {e_kml}", "error")
                QMessageBox.critical(self, "KML/DB Error", f"An error occurred during KML generation or status update:\n{e_kml}")
                operation_successful = False # Mark operation as failed
            return operation_successful

        # Estimate duration: 2 seconds per record, min 30s, max 5 minutes (300s)
        estimated_duration = min(max(len(valid_for_kml) * 2, 30), 300)

        # _execute_db_operation_with_lock will handle the lock acquisition and release
        # It will also call load_data_into_table if _do_kml_generation returns True
        # However, _do_kml_generation already calls load_data_into_table if ids_gen is not empty.
        # To avoid double loading, we ensure _do_kml_generation handles its own UI updates.
        # The return value of _do_kml_generation now signals if the core task was done.
        self._execute_db_operation_with_lock(
            operation_callable=_do_kml_generation,
            operation_desc=f"Generating KMLs and updating {len(valid_for_kml)} export statuses",
            lock_duration=estimated_duration,
            retry_callable_for_timer=self.handle_generate_kml
        )

    def _trigger_ge_polygon_upload(self,polygon_record):
        self.log_message(f"GE View:Processing polygon UUID {polygon_record.get('uuid')}for GE upload.","info");kml_doc=simplekml.Kml(name=str(polygon_record.get('uuid','Polygon')))
        if add_polygon_to_kml_object(kml_doc,polygon_record):
            try:
                if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
                    try:
                        os.remove(self.current_temp_kml_path)
                        self.log_message(f"Old temp KML deleted:{self.current_temp_kml_path}","info")
                    except FileNotFoundError:
                        self.log_message(f"Old temp KML not found:{self.current_temp_kml_path}","warning")
                    except PermissionError:
                        self.log_message(f"Permission denied deleting old temp KML:{self.current_temp_kml_path}","error")
                    except Exception as e_del:
                        self.log_message(f"Error deleting old temp KML {self.current_temp_kml_path}:{e_del}","error")
                fd,temp_kml_path=tempfile.mkstemp(suffix=".kml",prefix="ge_poly_");os.close(fd);kml_doc.save(temp_kml_path);self.current_temp_kml_path=temp_kml_path;self.log_message(f"Temp KML saved to:{self.current_temp_kml_path}","info")
                QApplication.clipboard().setText(self.current_temp_kml_path);self.log_message("KML path copied.","info")
                if self.show_ge_instructions_popup_again:self._show_ge_instructions_popup()
            except Exception as e_kml_save:self.log_message(f"Error saving temp KML:{e_kml_save}","error");QMessageBox.warning(self,"KML Error",f"Could not save KML:{e_kml_save}")
        else:self.log_message(f"Failed KML content gen for UUID {polygon_record.get('uuid')}.","error");QMessageBox.warning(self,"KML Generation Failed","Could not generate KML content.")
    def _show_ge_instructions_popup(self):
        msg_box=QMessageBox(self);msg_box.setWindowTitle("Google Earth Instructions");msg_box.setTextFormat(Qt.TextFormat.PlainText)
        msg_box.setText("Instructions:\n1.Click GE window to focus.\n2.Ctrl+I to open import.\n3.Ctrl+V to paste path.\n4.Enter to load.\n5.Ctrl+H for history.");checkbox=QCheckBox("Do not show again");msg_box.setCheckBox(checkbox);msg_box.exec()
        if msg_box.checkBox().isChecked():self.show_ge_instructions_popup_again=False;self.log_message("GE instructions popup disabled for session.","info")
    def _handle_ge_view_toggle(self,checked):
        original_action_blocked,original_button_blocked=self.toggle_ge_view_action.signalsBlocked(),self.toggle_ge_view_button.signalsBlocked()
        self.toggle_ge_view_action.blockSignals(True);self.toggle_ge_view_button.blockSignals(True)
        self.toggle_ge_view_action.setChecked(checked);self.toggle_ge_view_button.setChecked(checked);self.toggle_ge_view_button.setText(f"GE View:{'ON'if checked else'OFF'}")
        self.toggle_ge_view_action.blockSignals(original_action_blocked);self.toggle_ge_view_button.blockSignals(original_button_blocked)
        if checked:self.map_stack.setCurrentIndex(1);self.google_earth_view_widget.set_focus_on_webview()
        else:self.map_stack.setCurrentIndex(0)
        self.log_message(f"Google Earth View Toggled:{'ON'if checked else'OFF'}","info")
    def handle_about(self):QMessageBox.about(self,f"About {APP_NAME_MW}",f"<b>{APP_NAME_MW}</b><br>Version:{APP_VERSION_MW}<br><br>{ORGANIZATION_TAGLINE_MW}<br><br>Processes geographic data for KML generation.")
    def handle_show_ge_instructions(self):self._show_ge_instructions_popup()
    def log_message(self,message,level="info"):
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S");log_entry=f"[{timestamp}][{level.upper()}] {message}"
        if hasattr(self,'log_text_edit_qt_actual'):
            color_map={"INFO":"#0078D7","ERROR":"#D32F2F","SUCCESS":"#388E3C","WARNING":"#FFA500"}
            text_color=QColor(color_map.get(level.upper(),"#333333"))
            self.log_text_edit_qt_actual.setTextColor(text_color);self.log_text_edit_qt_actual.append(log_entry);self.log_text_edit_qt_actual.ensureCursorVisible()
        else:print(log_entry)
        if hasattr(self,'_main_status_bar'):self._main_status_bar.showMessage(message,7000 if level=="info"else 10000)

    def open_default_kml_view_settings_dialog(self):
        dialog = DefaultViewSettingsDialog(self.credential_manager, self)
        if dialog.exec() == QDialog.Accepted:
            self.log_message("Default KML view settings saved.", "info")
            # Future enhancement: Consider refreshing currently displayed KML if applicable.
            # For now, new settings will apply to KMLs loaded or re-loaded henceforth.
            print("Default KML View Settings dialog accepted. Refresh logic would go here if implemented.")
        else:
            self.log_message("Default KML view settings dialog cancelled.", "info")

    def load_data_into_table(self):
        try:
            polygon_records=self.db_manager.get_all_polygon_data_for_display();self.source_model.update_data(polygon_records)
            if hasattr(self,'filter_proxy_model'):self.filter_proxy_model.invalidate()
        except Exception as e:self.log_message(f"Error loading data into table:{e}","error");QMessageBox.warning(self,"Load Data Error",f"Could not load records:{e}")
    def closeEvent(self,event):
        if hasattr(self,'map_view_widget') and self.map_view_widget:
            self.map_view_widget.cleanup()
        if hasattr(self,'google_earth_view_widget') and hasattr(self.google_earth_view_widget,'cleanup'):
            self.google_earth_view_widget.cleanup()
        if hasattr(self,'db_manager') and self.db_manager:
            self.db_manager.close()
        if self.current_temp_kml_path and os.path.exists(self.current_temp_kml_path):
            try:
                os.remove(self.current_temp_kml_path)
                self.log_message(f"Temp KML deleted:{self.current_temp_kml_path}","info")
            except Exception as e:
                self.log_message(f"Error deleting temp KML {self.current_temp_kml_path}:{e}","error")
        super().closeEvent(event)
