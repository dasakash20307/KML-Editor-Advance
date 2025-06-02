# DilasaKMLTool_v4/ui/main_window.py (Significant Updates)
# ----------------------------------------------------------------------
import os
import sys
import csv
import utm
import tempfile
import subprocess

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
                               QSplitter, QFrame, QStatusBar, QMenuBar, QMenu, QToolBar, QPushButton,
                               QAbstractItemView, QHeaderView, QMessageBox, QFileDialog, QComboBox,
                               QSizePolicy, QTextEdit, QInputDialog, QLineEdit, QDateEdit, QGridLayout,
                               QCheckBox, QGroupBox, QStackedWidget, QApplication, QStyledItemDelegate,
                               QDialog, QProgressBar, QStyle)
from PySide6.QtGui import QPixmap, QIcon, QAction, QStandardItemModel, QStandardItem, QFont, QColor
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize, QSortFilterProxyModel, QDate

from database.db_manager import DatabaseManager
from core.sync_manager import DatabaseLockManager, KMLFileLockManager
from core.utils import resource_path
from core.kml_generator import add_polygon_to_kml_object # Used by KMLHandler via MainWindow's _trigger_ge_polygon_upload
import simplekml # Used by KMLHandler via MainWindow's _trigger_ge_polygon_upload
import datetime
import uuid

# Dialogs and Custom Widgets
from .dialogs.api_sources_dialog import APISourcesDialog
from .dialogs.output_mode_dialog import OutputModeDialog
from .dialogs.default_view_settings_dialog import DefaultViewSettingsDialog
from .dialogs import APIImportProgressDialog
from .widgets.map_view_widget import MapViewWidget
from .widgets.google_earth_webview_widget import GoogleEarthWebViewWidget
from .table_models import PolygonTableModel, PolygonFilterProxyModel
from .table_delegates import EvaluationStatusDelegate
from .lock_handlers import LockHandler
from .data_handlers import DataHandler
from .kml_handlers import KMLHandler


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

class MainWindow(QMainWindow):
    def __init__(self, db_manager, credential_manager):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME_MW} - {APP_VERSION_MW}")
        self.app_icon_path = resource_path(APP_ICON_FILE_NAME_MW)
        if os.path.exists(self.app_icon_path): self.setWindowIcon(QIcon(self.app_icon_path))

        self.db_manager = db_manager
        self.credential_manager = credential_manager
        if self.db_manager is None: QMessageBox.critical(self, "Initialization Error", "Database Manager not provided."); sys.exit(1)
        if self.credential_manager is None: QMessageBox.critical(self, "Initialization Error", "Credential Manager not provided."); sys.exit(1)

        self.db_lock_manager = None
        if self.db_manager and self.credential_manager:
            db_path = self.credential_manager.get_db_path()
            if db_path:
                self.db_lock_manager = DatabaseLockManager(db_path, self.credential_manager, logger_callable=self.log_message)
            else:
                QMessageBox.critical(self, "Locking Error", "Could not initialize database lock manager: DB path missing.")
        else:
            QMessageBox.critical(self, "Locking Error", "Could not initialize database lock manager: core components missing.")

        self.kml_file_lock_manager = None
        if self.credential_manager:
            kml_folder_path = self.credential_manager.get_kml_folder_path()
            if kml_folder_path:
                self.kml_file_lock_manager = KMLFileLockManager(kml_folder_path, self.credential_manager, logger_callable=self.log_message)
            else:
                QMessageBox.critical(self, "Locking Error", "Could not initialize KML lock manager: KML folder path missing.")
        else:
            QMessageBox.critical(self, "Locking Error", "Could not initialize KML lock manager: Credential Manager missing.")

        self.MAX_LOCK_RETRIES = 5
        self.LOCK_RETRY_TIMEOUT_MS = 7000

        self.API_FIELD_TO_DB_FIELD_MAP = {
            "UUID (use as the file name)": "uuid", "Response Code": "response_code",
            "Name of the Farmer": "farmer_name", "Village Name": "village_name",
            "Block": "block", "District": "district", "Proposed Area (Acre)": "proposed_area_acre",
            "Point 1 (UTM)": "p1_utm_str", "Point 1 (altitude)": "p1_altitude",
            "Point 2 (UTM)": "p2_utm_str", "Point 2 (altitude)": "p2_altitude",
            "Point 3 (UTM)": "p3_utm_str", "Point 3 (altitude)": "p3_altitude",
            "Point 4 (UTM)": "p4_utm_str", "Point 4 (altitude)": "p4_altitude",
        }

        # Instantiate Handlers
        self.lock_handler = LockHandler(
            main_window_ref=self,
            db_lock_manager=self.db_lock_manager,
            kml_file_lock_manager=self.kml_file_lock_manager,
            credential_manager=self.credential_manager,
            log_message_callback=self.log_message,
            update_status_bar_callback=self._main_status_bar.showMessage, # Pass actual method
            max_lock_retries=self.MAX_LOCK_RETRIES,
            lock_retry_timeout_ms=self.LOCK_RETRY_TIMEOUT_MS
        )

        self._create_main_layout() # For status bar
        self._create_status_bar() # For status bar message access

        self._setup_main_content_area_models_views() # Create models and views before data_handler

        self.data_handler = DataHandler(
            main_window_ref=self,
            db_manager=self.db_manager,
            credential_manager=self.credential_manager,
            lock_handler=self.lock_handler,
            log_message_callback=self.log_message,
            update_status_bar_callback=self._main_status_bar.showMessage,
            source_model=self.source_model,
            table_view=self.table_view,
            api_field_to_db_map=self.API_FIELD_TO_DB_FIELD_MAP
        )

        self.kml_handler = KMLHandler(
            main_window_ref=self,
            db_manager=self.db_manager,
            credential_manager=self.credential_manager,
            log_message_callback=self.log_message,
            map_stack=self.map_stack,
            map_view_widget=self.map_view_widget,
            google_earth_view_widget=self.google_earth_view_widget,
            table_view=self.table_view,
            source_model=self.source_model,
            filter_proxy_model=self.filter_proxy_model
        )

        self.resize(1200, 800); self._center_window()
        self._create_header()
        self._create_menus_and_toolbar() # Connect actions here
        self._setup_main_content_area_layout() # Layout widgets

        self._connect_signals() # Central place for signal connections

        self.load_data_into_table()
        self.log_message(f"{APP_NAME_MW} {APP_VERSION_MW} started. DB at: {self.db_manager.db_path}", "info")

    def _create_main_layout(self):
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)

    def _create_header(self):
        # ... (header creation code remains same)
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
        self.export_data_action=QAction(QIcon.fromTheme("document-save-as",QIcon(self.app_icon_path)),"Export Displayed Data as &CSV...",self)
        file_menu.addAction(self.export_data_action)
        file_menu.addSeparator();exit_action=QAction(QIcon.fromTheme("application-exit"),"E&xit",self);exit_action.setShortcut("Ctrl+Q");exit_action.setStatusTip("Exit application");exit_action.triggered.connect(self.close);file_menu.addAction(exit_action)

        data_menu=menubar.addMenu("&Data")
        self.import_csv_action=QAction(QIcon.fromTheme("document-open"),"Import &CSV...",self)
        data_menu.addAction(self.import_csv_action)
        self.fetch_api_action=QAction(QIcon.fromTheme("network-transmit-receive"),"&Fetch from API...",self)
        data_menu.addAction(self.fetch_api_action)
        self.manage_api_action=QAction(QIcon.fromTheme("preferences-system"),"Manage A&PI Sources...",self);self.manage_api_action.triggered.connect(self.handle_manage_api_sources);data_menu.addAction(self.manage_api_action);data_menu.addSeparator()
        self.delete_checked_action=QAction(QIcon.fromTheme("edit-delete"),"Delete Checked Rows...",self) # Renamed from delete_selected_action
        data_menu.addAction(self.delete_checked_action)
        self.clear_all_data_action=QAction(QIcon.fromTheme("edit-clear-all"),"Clear All Polygon Data...",self)
        data_menu.addAction(self.clear_all_data_action)

        kml_menu=menubar.addMenu("&KML")
        self.generate_kml_action=QAction(QIcon.fromTheme("document-export"),"&Generate KML for Checked Rows...",self)
        kml_menu.addAction(self.generate_kml_action)

        self.view_menu=menubar.addMenu("&View")
        self.toggle_ge_view_action=QAction("Google Earth View",self);self.toggle_ge_view_action.setCheckable(True);self.toggle_ge_view_action.toggled.connect(self._handle_ge_view_toggle);self.view_menu.addAction(self.toggle_ge_view_action)
        self.view_menu.addSeparator()
        self.default_kml_view_settings_action = QAction("Default KML View Settings...", self)
        self.default_kml_view_settings_action.triggered.connect(self.open_default_kml_view_settings_dialog)
        self.view_menu.addAction(self.default_kml_view_settings_action)

        help_menu=menubar.addMenu("&Help");self.about_action=QAction(QIcon.fromTheme("help-about"),"&About",self);self.about_action.triggered.connect(self.handle_about);help_menu.addAction(self.about_action)
        self.ge_instructions_action=QAction("GE &Instructions",self) # Will connect to KMLHandler
        help_menu.addAction(self.ge_instructions_action)

        self.toolbar=QToolBar("Main Toolbar");self.toolbar.setIconSize(QSize(20,20));self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon);self.toolbar.setMovable(True);self.addToolBar(Qt.ToolBarArea.TopToolBarArea,self.toolbar)
        self.toolbar.addAction(self.import_csv_action);self.toolbar.addSeparator()
        self.toggle_ge_view_button=QPushButton("GE View: OFF");self.toggle_ge_view_button.setCheckable(True);self.toggle_ge_view_button.toggled.connect(self._handle_ge_view_toggle);self.toolbar.addWidget(self.toggle_ge_view_button);self.toolbar.addSeparator()
        self.toolbar.addWidget(QLabel(" API Source: "));self.api_source_combo_toolbar=QComboBox();self.api_source_combo_toolbar.setMinimumWidth(150);self.refresh_api_source_dropdown();self.toolbar.addWidget(self.api_source_combo_toolbar)

        self.fetch_api_toolbar_action=QAction(QIcon.fromTheme("network-transmit-receive"),"&Fetch from Selected API",self) # Renamed for clarity
        self.toolbar.addAction(self.fetch_api_toolbar_action)

        manage_api_toolbar_action=QAction(QIcon.fromTheme("preferences-system"),"Manage API Sources",self);manage_api_toolbar_action.triggered.connect(self.handle_manage_api_sources);self.toolbar.addAction(manage_api_toolbar_action)
        self.toolbar.addSeparator();self.toolbar.addAction(self.generate_kml_action);self.toolbar.addAction(self.delete_checked_action)

    def _connect_signals(self):
        # Connections to DataHandler
        self.import_csv_action.triggered.connect(self.data_handler.handle_import_csv)
        self.fetch_api_action.triggered.connect(lambda: self.data_handler.handle_fetch_from_api(api_source_combo_toolbar=self.api_source_combo_toolbar))
        self.fetch_api_toolbar_action.triggered.connect(lambda: self.data_handler.handle_fetch_from_api(api_source_combo_toolbar=self.api_source_combo_toolbar))
        self.export_data_action.triggered.connect(self.data_handler.handle_export_displayed_data_csv)
        self.delete_checked_action.triggered.connect(self.data_handler.handle_delete_checked_rows)
        self.clear_all_data_action.triggered.connect(self.data_handler.handle_clear_all_data)
        self.generate_kml_action.triggered.connect(lambda: self.data_handler.handle_generate_kml(output_mode_dialog_class=OutputModeDialog))

        self.source_model.evaluation_status_changed.connect(self.data_handler.update_evaluation_status_in_db)
        self.data_handler.data_changed_signal.connect(self.load_data_into_table)

        # Connections to KMLHandler
        self.table_view.selectionModel().selectionChanged.connect(self.on_table_selection_changed) # MainWindow's method will call KMLHandler's
        self.ge_instructions_action.triggered.connect(self.kml_handler._show_ge_instructions_popup)
        if hasattr(self.kml_handler, 'kml_data_updated_signal'): # Check if signal exists
             self.kml_handler.kml_data_updated_signal.connect(self.load_data_into_table)


    def _create_status_bar(self):
        self._main_status_bar=QStatusBar()
        self.setStatusBar(self._main_status_bar)
        self._main_status_bar.showMessage("Ready.",3000)

    def _setup_main_content_area_models_views(self): # Split from _setup_main_content_area
        # This part needs to be called before DataHandler and KMLHandler instantiation
        self.map_view_widget = MapViewWidget(self.credential_manager, self)
        self.google_earth_view_widget = GoogleEarthWebViewWidget(self)
        self.map_stack = QStackedWidget(self)
        self.map_stack.addWidget(self.map_view_widget)
        self.map_stack.addWidget(self.google_earth_view_widget)

        self.source_model = PolygonTableModel(parent=self, db_manager_instance=self.db_manager)
        self.filter_proxy_model = PolygonFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.source_model)

        self.table_view = QTableView()
        self.table_view.setModel(self.filter_proxy_model)

    def _setup_main_content_area_layout(self): # Split from _setup_main_content_area
        # This part layouts the widgets after they (and handlers) are created
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
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

        # self.table_view already created and model set in _setup_main_content_area_models_views
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.SelectedClicked); self.table_view.horizontalHeader().setStretchLastSection(True); self.table_view.setAlternatingRowColors(False); self.table_view.setSortingEnabled(True); self.table_view.sortByColumn(PolygonTableModel.DATE_ADDED_COL,Qt.SortOrder.DescendingOrder)
        evaluation_delegate = EvaluationStatusDelegate(self.table_view); self.table_view.setItemDelegateForColumn(PolygonTableModel.EVALUATION_STATUS_COL, evaluation_delegate)
        self.table_view.setColumnWidth(PolygonTableModel.CHECKBOX_COL,30); self.table_view.setColumnWidth(PolygonTableModel.DB_ID_COL,50); # etc.
        # ... (set all other column widths as before) ...
        self.table_view.setColumnWidth(PolygonTableModel.UUID_COL,130); self.table_view.setColumnWidth(PolygonTableModel.RESPONSE_CODE_COL,120); self.table_view.setColumnWidth(PolygonTableModel.EVALUATION_STATUS_COL,150); self.table_view.setColumnWidth(PolygonTableModel.FARMER_NAME_COL,150); self.table_view.setColumnWidth(PolygonTableModel.VILLAGE_COL,120); self.table_view.setColumnWidth(PolygonTableModel.DATE_ADDED_COL,140); self.table_view.setColumnWidth(PolygonTableModel.KML_FILE_NAME_COL,150); self.table_view.setColumnWidth(PolygonTableModel.KML_FILE_STATUS_COL,110); self.table_view.setColumnWidth(PolygonTableModel.EDIT_COUNT_COL,90); self.table_view.setColumnWidth(PolygonTableModel.LAST_EDIT_DATE_COL,140); self.table_view.setColumnWidth(PolygonTableModel.EDITOR_DEVICE_ID_COL,130); self.table_view.setColumnWidth(PolygonTableModel.EDITOR_NICKNAME_COL,130); self.table_view.setColumnWidth(PolygonTableModel.DEVICE_CODE_COL,140); self.table_view.setColumnWidth(PolygonTableModel.EXPORT_COUNT_COL,100); self.table_view.setColumnWidth(PolygonTableModel.LAST_EXPORTED_COL,140); self.table_view.setColumnWidth(PolygonTableModel.LAST_MODIFIED_COL,140)

        table_layout.addWidget(self.table_view); self.right_splitter.addWidget(table_container)
        # self.table_view.selectionModel().selectionChanged.connect(self.on_table_selection_changed) # Moved to _connect_signals

        log_container = QWidget(); log_layout = QVBoxLayout(log_container); log_layout.setContentsMargins(0,10,0,0); log_label = QLabel("Status and Logs:"); log_layout.addWidget(log_label); self.log_text_edit_qt_actual = QTextEdit(); self.log_text_edit_qt_actual.setReadOnly(True); self.log_text_edit_qt_actual.setFont(QFont("Segoe UI",9)); log_layout.addWidget(self.log_text_edit_qt_actual); self.right_splitter.addWidget(log_container)
        self.right_splitter.setStretchFactor(0,3); self.right_splitter.setStretchFactor(1,1); right_pane_layout.addWidget(self.right_splitter,1); self.main_splitter.addWidget(right_pane_widget)
        self.main_splitter.setStretchFactor(0,1); self.main_splitter.setStretchFactor(1,2); self.main_layout.addWidget(self.main_splitter,1)

    def toggle_all_checkboxes(self,state_int): self.source_model.set_all_checkboxes(Qt.CheckState(state_int))

    def on_table_selection_changed(self,selected,deselected):
        # This method now primarily handles map updates. KML/GE logic is delegated.
        self.kml_handler.on_table_selection_changed(selected, deselected) # Delegate to KML Handler

        # Keep map update logic here for now, or move to MapViewWidget listening to table selection
        selected_proxy_indexes=self.table_view.selectionModel().selectedRows()
        polygon_record=None
        db_id = None
        if selected_proxy_indexes:
            source_model_index=self.filter_proxy_model.mapToSource(selected_proxy_indexes[0])
            if source_model_index.isValid():
                db_id_item=self.source_model.data(source_model_index.siblingAtColumn(PolygonTableModel.DB_ID_COL))
                try:
                    db_id=int(db_id_item)
                    polygon_record=self.db_manager.get_polygon_data_by_id(db_id)
                except (ValueError,TypeError): polygon_record=None
                except Exception: polygon_record=None # General exception

        # This part updates the MapViewWidget (non-GE, non-KML part of original method)
        if self.map_stack.currentIndex() == 0: # Map View is active
            if polygon_record and polygon_record.get('status') == 'valid_for_kml':
                coords_lat_lon, utm_valid = [], True
                for i in range(1, 5):
                    e, n = polygon_record.get(f'p{i}_easting'), polygon_record.get(f'p{i}_northing')
                    zn, zl = polygon_record.get(f'p{i}_zone_num'), polygon_record.get(f'p{i}_zone_letter')
                    if None in [e, n, zn, zl]: utm_valid = False; break
                    try:
                        lat, lon = utm.to_latlon(e, n, int(zn), zl)
                        coords_lat_lon.append((lat, lon))
                    except Exception: utm_valid = False; break
                if utm_valid and len(coords_lat_lon) == 4:
                    self.map_view_widget.display_polygon(coords_lat_lon, coords_lat_lon[0])
                elif hasattr(self.map_view_widget, 'clear_map'):
                    self.map_view_widget.clear_map()
            # If KML file exists but record not 'valid_for_kml' (e.g. no UTM), still try to load KML on map
            elif polygon_record and polygon_record.get('kml_file_name'):
                 kml_file_name = polygon_record.get('kml_file_name')
                 main_kml_folder_path = self.credential_manager.get_kml_folder_path()
                 if kml_file_name and isinstance(kml_file_name, str) and kml_file_name.strip() and main_kml_folder_path:
                    full_kml_path = os.path.join(main_kml_folder_path, kml_file_name.strip())
                    if os.path.exists(full_kml_path):
                        self.map_view_widget.load_kml_for_display(full_kml_path) # MapViewWidget needs this method
                    # No DB update for missing file here, KMLHandler's on_table_selection_changed handles that
                else: # Fallback to clear map if no valid KML path
                    if hasattr(self.map_view_widget, 'clear_map'): self.map_view_widget.clear_map()
            elif hasattr(self.map_view_widget, 'clear_map'): # Default clear
                self.map_view_widget.clear_map()

    def refresh_api_source_dropdown(self):
        if hasattr(self,'api_source_combo_toolbar'):
            current_text=self.api_source_combo_toolbar.currentText();self.api_source_combo_toolbar.clear();sources=self.db_manager.get_mwater_sources()
            for sid,title,url in sources:self.api_source_combo_toolbar.addItem(title,userData=url)
            index=self.api_source_combo_toolbar.findText(current_text)
            if index!=-1:self.api_source_combo_toolbar.setCurrentIndex(index)
            elif sources:self.api_source_combo_toolbar.setCurrentIndex(0)

    def handle_manage_api_sources(self):
        dialog=APISourcesDialog(self,self.db_manager);dialog.exec();self.refresh_api_source_dropdown()

    def _handle_ge_view_toggle(self,checked):
        original_action_blocked,original_button_blocked=self.toggle_ge_view_action.signalsBlocked(),self.toggle_ge_view_button.signalsBlocked()
        self.toggle_ge_view_action.blockSignals(True);self.toggle_ge_view_button.blockSignals(True)
        self.toggle_ge_view_action.setChecked(checked);self.toggle_ge_view_button.setChecked(checked);self.toggle_ge_view_button.setText(f"GE View:{'ON'if checked else'OFF'}")
        self.toggle_ge_view_action.blockSignals(original_action_blocked);self.toggle_ge_view_button.blockSignals(original_button_blocked)
        if checked:self.map_stack.setCurrentIndex(1);self.google_earth_view_widget.set_focus_on_webview()
        else:self.map_stack.setCurrentIndex(0)
        self.log_message(f"Google Earth View Toggled:{'ON'if checked else'OFF'}","info")

    def handle_about(self):QMessageBox.about(self,f"About {APP_NAME_MW}",f"<b>{APP_NAME_MW}</b><br>Version:{APP_VERSION_MW}<br><br>{ORGANIZATION_TAGLINE_MW}<br><br>Processes geographic data for KML generation.")
    def handle_show_ge_instructions(self): # This now calls KMLHandler's method
        if hasattr(self, 'kml_handler'): self.kml_handler._show_ge_instructions_popup()

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
        else:
            self.log_message("Default KML view settings dialog cancelled.", "info")

    def load_data_into_table(self):
        try:
            polygon_records=self.db_manager.get_all_polygon_data_for_display();self.source_model.update_data(polygon_records)
            if hasattr(self,'filter_proxy_model'):self.filter_proxy_model.invalidate()
        except Exception as e:self.log_message(f"Error loading data into table:{e}","error");QMessageBox.warning(self,"Load Data Error",f"Could not load records:{e}")

    def closeEvent(self,event):
        if hasattr(self,'map_view_widget') and self.map_view_widget: self.map_view_widget.cleanup()
        if hasattr(self,'google_earth_view_widget') and hasattr(self.google_earth_view_widget,'cleanup'): self.google_earth_view_widget.cleanup()
        if hasattr(self,'db_manager') and self.db_manager: self.db_manager.close()
        if hasattr(self, 'kml_handler'): self.kml_handler.cleanup_temp_kml() # Cleanup temp KML
        super().closeEvent(event)

    # Getter for KML output directory (example, adjust if settings/config manager is different)
    # def get_kml_output_directory(self):
    #     if hasattr(self, 'config_manager'):
    #         return self.config_manager.get_setting("kml_output_directory", os.path.expanduser("~/Documents"))
    #     return os.path.expanduser("~/Documents")

    # Getter for app settings (example)
    # def get_app_setting(self, key, default=None):
    #     if hasattr(self, 'settings'): # Assuming QSettings object
    #         return self.settings.value(key, default)
    #     return default

    # update_status_bar method for callbacks
    def update_status_bar(self, message, timeout=0):
        if hasattr(self, '_main_status_bar'):
            self._main_status_bar.showMessage(message, timeout)

    # Placeholder for _setup_main_content_area to avoid breaking the call order
    # It's split into _setup_main_content_area_models_views and _setup_main_content_area_layout
    def _setup_main_content_area(self):
        self._setup_main_content_area_models_views()
        # Instantiation of handlers is done in __init__ after models/views are ready
        self._setup_main_content_area_layout()
