# DilasaKMLTool_v4/ui/main_window.py (Significant Updates)
# ----------------------------------------------------------------------
import os
import sys
import csv
import utm
import tempfile
import subprocess
import platform
import ctypes

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
                               QSplitter, QFrame, QStatusBar, QMenuBar, QMenu, QToolBar, QPushButton,
                               QAbstractItemView, QHeaderView, QMessageBox, QFileDialog, QComboBox,
                               QSizePolicy, QTextEdit, QInputDialog, QLineEdit, QDateEdit, QGridLayout,
                               QCheckBox, QGroupBox, QStackedWidget, QApplication, QStyledItemDelegate,
                               QDialog, QProgressBar, QStyle)
from PySide6.QtGui import QPixmap, QIcon, QAction, QStandardItemModel, QStandardItem, QFont, QColor
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, QSize, QSortFilterProxyModel, QDate

from main_app import VERSION # Import VERSION for window title
from database.db_manager import DatabaseManager
from core.sync_manager import DatabaseLockManager, KMLFileLockManager
from core.utils import resource_path
from core.kml_generator import add_polygon_to_kml_object # Used by KMLHandler via MainWindow's _trigger_ge_polygon_upload
import simplekml # Used by KMLHandler via MainWindow's _trigger_ge_polygon_upload
import datetime
import uuid
import qtmodern.styles

# Dialogs and Custom Widgets
from .dialogs.about_dialog import AboutDialog # Import the new AboutDialog
from .dialogs.api_sources_dialog import APISourcesDialog
from .dialogs.output_mode_dialog import OutputModeDialog
from .dialogs.default_view_settings_dialog import DefaultViewSettingsDialog
from .dialogs import APIImportProgressDialog
from .widgets.kml_editor_view_widget import KMLEditorViewWidget # UPDATED
from .widgets.google_earth_webview_widget import GoogleEarthWebViewWidget
from .table_models import PolygonTableModel, PolygonFilterProxyModel
from .table_delegates import EvaluationStatusDelegate
from .lock_handlers import LockHandler
from .data_handlers import DataHandler
from .kml_handlers import KMLHandler
from .dialogs.table_view_editor_dialog import TableViewEditorDialog # Added
from .dialogs.sharing_info_dialog import SharingInfoDialog # Added
from .multi_kml_view_edit import MultiKmlViewEdit # Added for Multi-KML feature


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
        self.setWindowTitle(f"Advanced KML Editor - v{VERSION}") # Use imported VERSION

        # Set window icon
        app_icon_path_generic = resource_path(APP_ICON_FILE_NAME_MW) # Usually app_icon.ico
        logo_png_path = resource_path("assets/logo.png")

        icon_to_set = None
        if os.path.exists(logo_png_path):
            loaded_icon = QIcon(logo_png_path)
            if not loaded_icon.isNull():
                icon_to_set = loaded_icon

        if icon_to_set is None and os.path.exists(app_icon_path_generic):
            loaded_icon = QIcon(app_icon_path_generic)
            if not loaded_icon.isNull():
                icon_to_set = loaded_icon

        if icon_to_set is None:
            icon_to_set = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)

        self.setWindowIcon(icon_to_set)

        self.db_manager = db_manager
        self.credential_manager = credential_manager
        if self.db_manager is None: QMessageBox.critical(self, "Initialization Error", "Database Manager not provided."); sys.exit(1)
        if self.credential_manager is None: QMessageBox.critical(self, "Initialization Error", "Credential Manager not provided."); sys.exit(1)

        # Initialize theme
        app = QApplication.instance()

        # Set global application font
        if app: # Ensure app instance exists
            font = QFont("Segoe UI", 12)
            app.setFont(font)

        if app and self.credential_manager:
            current_theme = self.credential_manager.load_app_theme()
            if current_theme == "dark":
                qtmodern.styles.dark(app)
                if platform.system() == "Windows":
                    try:
                        ctypes.windll.uxtheme.SetPreferredAppMode(2)  # Dark
                    except Exception as e:
                        print(f"Failed to set Windows dark mode: {e}")
            else:  # Light theme
                qtmodern.styles.light(app)
                if platform.system() == "Windows":
                    try:
                        ctypes.windll.uxtheme.SetPreferredAppMode(1)  # Light
                    except Exception as e:
                        print(f"Failed to set Windows light mode: {e}")

            # Apply global QSS stylesheet
            try:
                qss_path = resource_path("assets/style.qss")
                if os.path.exists(qss_path):
                    with open(qss_path, "r") as f:
                        stylesheet = f.read()
                    app.setStyleSheet(stylesheet)
            except Exception as e:
                print(f"Error loading global stylesheet: {e}")

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


        self._create_main_layout() # For status bar
        self._create_status_bar() # For status bar message access
        
        # Instantiate Handlers (moved after status bar creation)
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
            # map_view_widget=self.map_view_widget, # OLD
            kml_editor_view_widget=self.kml_editor_widget, # NEW
            lock_handler=self.lock_handler, # NEW
            google_earth_view_widget=self.google_earth_view_widget,
            table_view=self.table_view,
            source_model=self.source_model,
            filter_proxy_model=self.filter_proxy_model
        )
        
        # Initialize the Multi-KML feature handler
        self.multi_kml_handler = MultiKmlViewEdit(
            main_window_ref=self,
            credential_manager=self.credential_manager,
            kml_handler=self.kml_handler
        )

        self.resize(1200, 800); self._center_window()
        self._create_header()
        self._create_menus_and_toolbar() # Connect actions here
        self._setup_main_content_area_layout() # Layout widgets

        self._connect_signals() # Central place for signal connections

        self.load_data_into_table()
        self.log_message(f"Advanced KML Editor v{VERSION} started. DB at: {self.db_manager.db_path}", "info")

    def _create_main_layout(self):
        self.central_widget = QWidget(); self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)

    def _create_header(self):
        # ... (header creation code remains same)
        header_widget = QWidget(); header_widget.setFixedHeight(60); # header_widget.setStyleSheet("border-bottom: 1px solid #D0D0D0;") # Removed inline style
        header_widget.setObjectName("mainWindowHeader") # Added object name
        header_layout = QHBoxLayout(header_widget); header_layout.setContentsMargins(5,5,5,5); header_layout.setSpacing(5)

        # Use window icon for header logo if possible, else fallback to dilasa_logo.jpg
        header_logo_label = QLabel()
        window_icon = self.windowIcon()
        if not window_icon.isNull():
            pixmap = window_icon.pixmap(QSize(40,40))
            header_logo_label.setPixmap(pixmap)
        elif os.path.exists(resource_path(LOGO_FILE_NAME_MW)): # Fallback to dilasa_logo.jpg
            pixmap=QPixmap(resource_path(LOGO_FILE_NAME_MW))
            header_logo_label.setPixmap(pixmap.scaled(40,40,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        else:
            header_logo_label.setText("[L]") # Fallback text
        header_layout.addWidget(header_logo_label,0,Qt.AlignmentFlag.AlignVCenter)

        title_label=QLabel("Advanced KML Editor");title_label.setFont(QFont("Segoe UI",16,QFont.Weight.Bold));title_label.setAlignment(Qt.AlignmentFlag.AlignCenter);header_layout.addWidget(title_label,1)
        # version_label displays main_app.VERSION now, consistent with window title
        version_label=QLabel(f"v{VERSION}");version_label.setFont(QFont("Segoe UI",8,QFont.Weight.Normal,True));
        version_label.setObjectName("versionLabel")
        header_layout.addWidget(version_label,0,Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(header_widget)

    def _create_menus_and_toolbar(self):
        menubar=self.menuBar();file_menu=menubar.addMenu("&File")
        self.export_data_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Export Displayed Data as &CSV...",self)
        file_menu.addAction(self.export_data_action)

        self.sharing_info_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView), "Central App Sharing Info...", self)
        file_menu.addAction(self.sharing_info_action)

        file_menu.addSeparator()
        exit_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton),"E&xit",self)
        exit_action.setShortcut("Ctrl+Q");exit_action.setStatusTip("Exit application");exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        data_menu=menubar.addMenu("&Data")
        self.import_csv_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton),"Import &CSV...",self)
        data_menu.addAction(self.import_csv_action)
        self.fetch_api_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown),"&Fetch from API...",self)
        data_menu.addAction(self.fetch_api_action)
        self.manage_api_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_SettingsIcon),"Manage A&PI Sources...",self)
        self.manage_api_action.triggered.connect(self.handle_manage_api_sources);data_menu.addAction(self.manage_api_action);data_menu.addSeparator()
        self.delete_checked_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon),"Delete Checked Rows...",self)
        data_menu.addAction(self.delete_checked_action)
        self.clear_all_data_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton),"Clear All Polygon Data...",self)
        data_menu.addAction(self.clear_all_data_action)
        data_menu.addSeparator()
        self.export_csv_template_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Export CSV Template...", self)
        data_menu.addAction(self.export_csv_template_action)


        kml_menu=menubar.addMenu("&KML")
        self.generate_kml_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),"&Generate KML for Checked Rows...",self) # SP_FileIcon or SP_DriveHDIcon
        kml_menu.addAction(self.generate_kml_action)

        self.view_menu=menubar.addMenu("&View")
        self.toggle_ge_view_action=QAction("Google Earth View",self) # Icon set on button directly
        self.toggle_ge_view_action.setCheckable(True);self.toggle_ge_view_action.toggled.connect(self._handle_ge_view_toggle)
        self.view_menu.addAction(self.toggle_ge_view_action)
        self.view_menu.addSeparator()
        self.default_kml_view_settings_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopSettingsIcon),"Default KML View Settings...", self)
        self.default_kml_view_settings_action.triggered.connect(self.open_default_kml_view_settings_dialog)
        self.view_menu.addAction(self.default_kml_view_settings_action)

        self.table_view_editor_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Table View Editor...", self)
        self.view_menu.addAction(self.table_view_editor_action)

        self.view_menu.addSeparator()
        self.toggle_theme_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_CustomBase), "Toggle Theme (Light/Dark)", self) # SP_CustomBase as placeholder
        self.toggle_theme_action.triggered.connect(self._toggle_theme)
        self.view_menu.addAction(self.toggle_theme_action)
        self.view_menu.addSeparator() # Separator before toolbar toggles

        # Add toggle action for Multi-KML Toolbar
        toggle_multi_kml_toolbar_action = self.multi_kml_toolbar.toggleViewAction()
        toggle_multi_kml_toolbar_action.setText("Multi-KML Toolbar")
        self.view_menu.addAction(toggle_multi_kml_toolbar_action)

        help_menu=menubar.addMenu("&Help")
        self.about_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),"&About",self)
        self.about_action.triggered.connect(self.handle_about);help_menu.addAction(self.about_action)
        self.ge_instructions_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion),"GE &Instructions",self) # Will connect to KMLHandler
        help_menu.addAction(self.ge_instructions_action)

        self.toolbar=QToolBar("Main Toolbar");self.toolbar.setIconSize(QSize(20,20));self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon);self.toolbar.setMovable(True);self.addToolBar(Qt.ToolBarArea.TopToolBarArea,self.toolbar)
        self.toolbar.addAction(self.import_csv_action);self.toolbar.addSeparator()

        self.toggle_ge_view_button=QPushButton("GE View: OFF")
        self.toggle_ge_view_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_GlobeIcon)) # SP_GlobeIcon or SP_CommandLink
        self.toggle_ge_view_button.setCheckable(True);self.toggle_ge_view_button.toggled.connect(self._handle_ge_view_toggle)
        self.toolbar.addWidget(self.toggle_ge_view_button);self.toolbar.addSeparator()

        self.toolbar.addWidget(QLabel(" API Source: "));self.api_source_combo_toolbar=QComboBox();self.api_source_combo_toolbar.setMinimumWidth(150);self.refresh_api_source_dropdown();self.toolbar.addWidget(self.api_source_combo_toolbar)

        self.fetch_api_toolbar_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown),"&Fetch from Selected API",self)
        self.toolbar.addAction(self.fetch_api_toolbar_action)

        manage_api_toolbar_action=QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_SettingsIcon),"Manage API Sources",self)
        manage_api_toolbar_action.triggered.connect(self.handle_manage_api_sources);self.toolbar.addAction(manage_api_toolbar_action)
        self.toolbar.addSeparator();self.toolbar.addAction(self.generate_kml_action);self.toolbar.addAction(self.delete_checked_action)

        # Add Table View Editor to toolbar for easier access
        self.edit_table_view_toolbar_button = QPushButton("Edit Table View")
        self.edit_table_view_toolbar_button.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.edit_table_view_toolbar_button)

        # --- Create Multi-KML Operations Toolbar ---
        self.multi_kml_toolbar = QToolBar("Multi-KML Operations Toolbar")
        self.multi_kml_toolbar.setObjectName("multiKmlToolbar")

        # Define actions for the Multi-KML toolbar
        self.multi_kml_view_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon), "Multi-KML View", self)
        self.multi_kml_view_action.triggered.connect(lambda: self.log_message("Placeholder: Multi-KML View clicked", "info"))

        self.multi_kml_edit_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon), "Multi-KML Editor", self) # Or SP_EditIcon
        self.multi_kml_edit_action.triggered.connect(lambda: self.log_message("Placeholder: Multi-KML Editor clicked", "info"))

        self.exit_multi_kml_mode_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton), "Exit Multi-KML Mode", self)
        self.exit_multi_kml_mode_action.triggered.connect(lambda: self.log_message("Placeholder: Exit Multi-KML Mode clicked", "info"))

        self.save_all_edits_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save All Edits", self)
        self.save_all_edits_action.triggered.connect(lambda: self.log_message("Placeholder: Save All Edits clicked", "info"))

        self.cancel_all_edits_action = QAction(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton), "Cancel All Edits", self)
        self.cancel_all_edits_action.triggered.connect(lambda: self.log_message("Placeholder: Cancel All Edits clicked", "info"))

        # Add actions to the Multi-KML toolbar
        self.multi_kml_toolbar.addAction(self.multi_kml_view_action)
        self.multi_kml_toolbar.addAction(self.multi_kml_edit_action)
        self.multi_kml_toolbar.addSeparator()
        self.multi_kml_toolbar.addAction(self.exit_multi_kml_mode_action)
        self.multi_kml_toolbar.addSeparator()
        self.multi_kml_toolbar.addAction(self.save_all_edits_action)
        self.multi_kml_toolbar.addAction(self.cancel_all_edits_action)

        # Make the toolbar detachable and dockable
        self.multi_kml_toolbar.setFloatable(True)
        self.multi_kml_toolbar.setMovable(True)

        # Add the toolbar to the main window, initially at the top
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.multi_kml_toolbar)


    def _connect_signals(self):
        # Connections to DataHandler
        self.import_csv_action.triggered.connect(self.data_handler.handle_import_csv)
        self.fetch_api_action.triggered.connect(lambda: self.data_handler.handle_fetch_from_api(api_source_combo_toolbar=self.api_source_combo_toolbar))
        self.fetch_api_toolbar_action.triggered.connect(lambda: self.data_handler.handle_fetch_from_api(api_source_combo_toolbar=self.api_source_combo_toolbar))
        self.export_data_action.triggered.connect(self.data_handler.handle_export_displayed_data_csv)
        self.delete_checked_action.triggered.connect(self.data_handler.handle_delete_checked_rows)
        self.clear_all_data_action.triggered.connect(self.data_handler.handle_clear_all_data)
        self.export_csv_template_action.triggered.connect(self.handle_export_csv_template) # New connection
        self.generate_kml_action.triggered.connect(lambda: self.data_handler.handle_generate_kml(output_mode_dialog_class=OutputModeDialog))

        self.source_model.evaluation_status_changed.connect(self.data_handler.update_evaluation_status_in_db)
        self.data_handler.data_changed_signal.connect(self.load_data_into_table)

        # Connections to KMLHandler
        self.table_view.selectionModel().selectionChanged.connect(self.kml_handler.on_table_selection_changed) # Directly connect to KMLHandler's method
        self.ge_instructions_action.triggered.connect(self.kml_handler._show_ge_instructions_popup)
        if hasattr(self.kml_handler, 'kml_data_updated_signal'):
             self.kml_handler.kml_data_updated_signal.connect(self.load_data_into_table)

        # Connection for saving KML from KMLEditorViewWidget
        if hasattr(self.kml_editor_widget, 'save_triggered_signal'):
            self.kml_editor_widget.save_triggered_signal.connect(self._handle_save_kml_changes_triggered)

        # Connection for Table View Editor
        self.table_view_editor_action.triggered.connect(self._open_table_view_editor) # Added
        self.edit_table_view_toolbar_button.clicked.connect(self._open_table_view_editor) # Added

        # Connection for Sharing Info Dialog
        self.sharing_info_action.triggered.connect(self._open_sharing_info_dialog) # Added
        
        # Multi-KML connections
        self.multi_kml_view_button.clicked.connect(self._toggle_multi_kml_mode)
        self.multi_kml_editor_button.clicked.connect(self.multi_kml_handler.enter_multi_edit_mode)
        self.single_kml_editor_button.clicked.connect(lambda: self.multi_kml_handler.enable_single_kml_mode())
        self.multi_kml_save_button.clicked.connect(self.multi_kml_handler.save_multi_kml_edits)
        self.multi_kml_cancel_button.clicked.connect(self.multi_kml_handler.cancel_multi_edit)
        self.multi_kml_handler.multi_kml_saved_signal.connect(self.on_multi_kml_saved)

    def _create_status_bar(self):
        self._main_status_bar=QStatusBar()
        self.setStatusBar(self._main_status_bar)
        self._main_status_bar.showMessage("Ready.",3000)

        # Add version label to the status bar
        self.version_status_label = QLabel(f"v{VERSION}") # Use VERSION from main_app.py and make it concise
        self.version_status_label.setObjectName("versionStatusLabel") # For QSS styling
        self._main_status_bar.addPermanentWidget(self.version_status_label)

    def _setup_main_content_area_models_views(self):
        # This part needs to be called before DataHandler and KMLHandler instantiation
        # self.map_view_widget = MapViewWidget(self.credential_manager, self) # OLD
        self.kml_editor_widget = KMLEditorViewWidget(log_message_callback=self.log_message, parent=self) # NEW
        self.google_earth_view_widget = GoogleEarthWebViewWidget(self)
        self.map_stack = QStackedWidget(self)
        # self.map_stack.addWidget(self.map_view_widget) # OLD
        self.map_stack.addWidget(self.kml_editor_widget) # NEW - KML Editor at index 0
        self.map_stack.addWidget(self.google_earth_view_widget) # GE View at index 1

        self.source_model = PolygonTableModel(parent=self, db_manager_instance=self.db_manager)
        self.filter_proxy_model = PolygonFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.source_model)

        self.table_view = QTableView()
        self.table_view.setModel(self.filter_proxy_model)

    def _setup_main_content_area_layout(self): # Split from _setup_main_content_area
        # This part layouts the widgets after they (and handlers) are created

        # Create a placeholder for KML Editor Controls panel
        self.kml_editor_controls_placeholder = QWidget()
        self.kml_editor_controls_placeholder.setMinimumHeight(50) # Ensure it's visible and shrinkable
        # You could add a QLabel to it for identification during development:
        # placeholder_layout = QVBoxLayout(self.kml_editor_controls_placeholder)
        # placeholder_layout.addWidget(QLabel("KML Editor Controls Placeholder - Resizable"))
        # self.kml_editor_controls_placeholder.setStyleSheet("background-color: lightblue;")


        # Vertical splitter for map_stack (top) and KML editor controls placeholder (bottom)
        self.left_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.left_vertical_splitter.addWidget(self.map_stack)
        self.left_vertical_splitter.addWidget(self.kml_editor_controls_placeholder)
        self.left_vertical_splitter.setSizes([400, 100]) # Initial sizes: map stack, controls placeholder

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.left_vertical_splitter) # Add new vertical splitter to the left

        right_pane_widget = QWidget(); right_pane_layout = QVBoxLayout(right_pane_widget); right_pane_layout.setContentsMargins(10,0,10,10)

        # Remove KML controls strip for Multi-KML buttons from here
        # self.kml_controls_strip = QWidget()
        # kml_controls_layout = QHBoxLayout(self.kml_controls_strip)
        # kml_controls_layout.setContentsMargins(0,0,0,0)
        # ... (Multi-KML buttons were here) ...
        # kml_controls_layout.addStretch()
        # right_pane_layout.addWidget(self.kml_controls_strip) # No longer adding this strip here
        
        self.table_editors_strip = QWidget()
        strip_layout = QHBoxLayout(self.table_editors_strip)
        strip_layout.setContentsMargins(0,0,0,0); strip_layout.addStretch()
        self.toggle_filter_panel_button = QPushButton(" Filters")
        self.toggle_filter_panel_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        # self.toggle_filter_panel_button.setStyleSheet("padding: 3px;") # Removed inline style
        self.toggle_filter_panel_button.clicked.connect(self._toggle_filter_panel_visibility)
        strip_layout.addWidget(self.toggle_filter_panel_button)
        right_pane_layout.addWidget(self.table_editors_strip)

        filter_panel_widget = self._setup_filter_panel()
        right_pane_layout.addWidget(filter_panel_widget)

        # Create and add the Multi-KML Operations GroupBox
        multi_kml_operations_group = self._setup_multi_kml_operations_panel()
        right_pane_layout.addWidget(multi_kml_operations_group) # Add this before the splitter

        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        table_container = QWidget(); table_layout = QVBoxLayout(table_container); table_layout.setContentsMargins(0,0,0,0)
        checkbox_header_layout = QHBoxLayout(); self.select_all_checkbox = QCheckBox("Select/Deselect All"); self.select_all_checkbox.stateChanged.connect(self.toggle_all_checkboxes); checkbox_header_layout.addWidget(self.select_all_checkbox); checkbox_header_layout.addStretch(); table_layout.addLayout(checkbox_header_layout)
        self.select_all_checkbox.setVisible(True) # Ensure it's always visible

        # self.table_view already created and model set in _setup_main_content_area_models_views
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.SelectedClicked); self.table_view.horizontalHeader().setStretchLastSection(True); self.table_view.setAlternatingRowColors(False); self.table_view.setSortingEnabled(True); self.table_view.sortByColumn(PolygonTableModel.DATE_ADDED_COL,Qt.SortOrder.DescendingOrder)
        evaluation_delegate = EvaluationStatusDelegate(self.table_view); self.table_view.setItemDelegateForColumn(PolygonTableModel.EVALUATION_STATUS_COL, evaluation_delegate)
        self.table_view.setColumnWidth(PolygonTableModel.CHECKBOX_COL,30); self.table_view.setColumnWidth(PolygonTableModel.DB_ID_COL,50); # etc.
        # ... (set all other column widths as before) ...
        self.table_view.setColumnWidth(PolygonTableModel.UUID_COL,130); self.table_view.setColumnWidth(PolygonTableModel.RESPONSE_CODE_COL,120); self.table_view.setColumnWidth(PolygonTableModel.EVALUATION_STATUS_COL,150); self.table_view.setColumnWidth(PolygonTableModel.FARMER_NAME_COL,150); self.table_view.setColumnWidth(PolygonTableModel.VILLAGE_COL,120); self.table_view.setColumnWidth(PolygonTableModel.DATE_ADDED_COL,140); self.table_view.setColumnWidth(PolygonTableModel.KML_FILE_NAME_COL,150);
        self.table_view.setColumnWidth(PolygonTableModel.PLACEMARK_NAME_COL, 180); # <<<< SET WIDTH FOR NEW COLUMN
        self.table_view.setColumnWidth(PolygonTableModel.KML_FILE_STATUS_COL,110); self.table_view.setColumnWidth(PolygonTableModel.EDIT_COUNT_COL,90); self.table_view.setColumnWidth(PolygonTableModel.LAST_EDIT_DATE_COL,140); self.table_view.setColumnWidth(PolygonTableModel.EDITOR_DEVICE_ID_COL,130); self.table_view.setColumnWidth(PolygonTableModel.EDITOR_NICKNAME_COL,130); self.table_view.setColumnWidth(PolygonTableModel.DEVICE_CODE_COL,140); self.table_view.setColumnWidth(PolygonTableModel.EXPORT_COUNT_COL,100); self.table_view.setColumnWidth(PolygonTableModel.LAST_EXPORTED_COL,140); self.table_view.setColumnWidth(PolygonTableModel.LAST_MODIFIED_COL,140)

        table_layout.addWidget(self.table_view); self.right_splitter.addWidget(table_container)

        log_container = QWidget(); log_layout = QVBoxLayout(log_container); log_layout.setContentsMargins(0,10,0,0); log_label = QLabel("Status and Logs:"); log_layout.addWidget(log_label); self.log_text_edit_qt_actual = QTextEdit(); self.log_text_edit_qt_actual.setReadOnly(True); self.log_text_edit_qt_actual.setFont(QFont("Segoe UI",9)); log_layout.addWidget(self.log_text_edit_qt_actual); self.right_splitter.addWidget(log_container)
        self.right_splitter.setStretchFactor(0,3); self.right_splitter.setStretchFactor(1,1); right_pane_layout.addWidget(self.right_splitter,1); self.main_splitter.addWidget(right_pane_widget)
        self.main_splitter.setStretchFactor(0,1); self.main_splitter.setStretchFactor(1,2); self.main_layout.addWidget(self.main_splitter,1)

        # Conditionally enable/disable actions based on app mode
        self._update_ui_for_app_mode()

        # Initial state for Multi-KML buttons (call after multi_kml_handler is initialized)
        if hasattr(self, 'multi_kml_handler'):
            self.multi_kml_handler.enable_single_kml_mode() # Start in single KML mode

    def toggle_all_checkboxes(self,state_int): self.source_model.set_all_checkboxes(Qt.CheckState(state_int))

    # on_table_selection_changed is now primarily handled by KMLHandler,
    # which is directly connected to table_view.selectionModel().selectionChanged.
    # The old on_table_selection_changed in MainWindow can be removed or simplified if it had other duties.
    # For now, let's remove the duplicated logic for map updates from here.
    # def on_table_selection_changed(self,selected,deselected):
    #     # This method now primarily handles map updates. KML/GE logic is delegated.
    #     # self.kml_handler.on_table_selection_changed(selected, deselected) # Delegate to KML Handler
    #     pass # Logic moved to KMLHandler.on_table_selection_changed


    def _handle_save_kml_changes_triggered(self, save_data: dict):
        """Handle save signal from KML editor with edited data"""
        self.log_message("MainWindow: Save KML changes triggered.", "info")

        # Retrieve necessary data from KMLEditorViewWidget
        db_id = getattr(self.kml_editor_widget, 'current_db_id', None)
        original_kml_filename = getattr(self.kml_editor_widget, 'current_kml_filename', None)

        if db_id is None or original_kml_filename is None:
            self.log_message("Error: DB ID or original KML filename not available in KML Editor for saving.", "error")
            QMessageBox.critical(self, "Save Error", "Cannot save changes: Missing context (DB ID or original filename).\nPlease re-select the item from the table.")
            self.kml_editor_widget.exit_edit_mode(reload_original_kml=True)
            return

        # Extract data from the save_data dictionary
        geometry_json_str = save_data.get('geometry')
        edited_name = save_data.get('name', '')
        edited_description = save_data.get('description', '')

        if geometry_json_str is None or geometry_json_str.lower() == "null":
            self.log_message("Error: Failed to retrieve edited geometry from map. Save aborted.", "error")
            QMessageBox.warning(self, "Save Error", "Could not retrieve edited geometry from the map. Save operation cancelled.")
            self.kml_editor_widget.exit_edit_mode(reload_original_kml=True)
            return

        # Call KMLHandler to perform the save operation
        save_success = self.kml_handler.save_edited_kml(
            db_id, original_kml_filename, geometry_json_str,
            edited_name, edited_description
        )

        if not save_success:
            # If save failed, KMLHandler should have reloaded original or cleared.
            # Ensure editor is out of edit mode.
            self.kml_editor_widget.exit_edit_mode(reload_original_kml=True)


    def refresh_api_source_dropdown(self):
        if hasattr(self,'api_source_combo_toolbar'):
            current_text=self.api_source_combo_toolbar.currentText();self.api_source_combo_toolbar.clear();sources=self.db_manager.get_mwater_sources()
            for sid,title,url in sources:self.api_source_combo_toolbar.addItem(title,userData=url)
            index=self.api_source_combo_toolbar.findText(current_text)
            if index!=-1:self.api_source_combo_toolbar.setCurrentIndex(index)
            elif sources:self.api_source_combo_toolbar.setCurrentIndex(0)

    def handle_manage_api_sources(self):
        dialog=APISourcesDialog(self,self.db_manager);dialog.exec();self.refresh_api_source_dropdown()

    def handle_export_csv_template(self):
        """Calls the DataHandler method to export the CSV template."""
        self.data_handler.handle_export_csv_template()

    def _handle_ge_view_toggle(self,checked):
        original_action_blocked,original_button_blocked=self.toggle_ge_view_action.signalsBlocked(),self.toggle_ge_view_button.signalsBlocked()
        self.toggle_ge_view_action.blockSignals(True);self.toggle_ge_view_button.blockSignals(True)
        self.toggle_ge_view_action.setChecked(checked);self.toggle_ge_view_button.setChecked(checked);self.toggle_ge_view_button.setText(f"GE View:{'ON'if checked else'OFF'}")
        self.toggle_ge_view_action.blockSignals(original_action_blocked);self.toggle_ge_view_button.blockSignals(original_button_blocked)

        current_map_index = 0 # Default to KML Editor view
        if checked:
            current_map_index = 1 # Google Earth View
            self.google_earth_view_widget.set_focus_on_webview()

        self.map_stack.setCurrentIndex(current_map_index)
        # Manually trigger selection change to update the newly visible map view
        self.kml_handler.on_table_selection_changed(None, None) # Pass dummy selection to re-trigger logic
        self.log_message(f"View Toggled. Active map index: {current_map_index} ({'GE View ON' if checked else 'KML Editor ON'})","info")


    def handle_about(self):
        # from main_app import VERSION # Ensure VERSION is available (already imported at class level)
        about_dialog = AboutDialog(version=VERSION, parent=self)
        about_dialog.exec()

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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.log_message("Default KML view settings saved.", "info")
        else:
            self.log_message("Default KML view settings dialog cancelled.", "info")

    def load_data_into_table(self):
        try:
            polygon_records=self.db_manager.get_all_polygon_data_for_display();self.source_model.update_data(polygon_records)
            if hasattr(self,'filter_proxy_model'):self.filter_proxy_model.invalidate()
        except Exception as e:self.log_message(f"Error loading data into table:{e}","error");QMessageBox.warning(self,"Load Data Error",f"Could not load records:{e}")

    def closeEvent(self,event):
        # if hasattr(self,'map_view_widget') and self.map_view_widget: self.map_view_widget.cleanup() # OLD
        if hasattr(self,'kml_editor_widget') and self.kml_editor_widget: self.kml_editor_widget.cleanup() # NEW
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

    def _center_window(self):
        # Placeholder method to center the window
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def _setup_filter_panel(self):
        self.filter_groupbox = QGroupBox("Filter Data")
        filter_layout = QGridLayout(self.filter_groupbox)
        filter_layout.setContentsMargins(5, 10, 5, 5) # Add some top margin for title
        filter_layout.setSpacing(10)

        # Row 0: Response Code
        filter_layout.addWidget(QLabel("Response Code:"), 0, 0)
        self.filter_response_code_edit = QLineEdit()
        self.filter_response_code_edit.setPlaceholderText("Enter Response Code (exact)")
        filter_layout.addWidget(self.filter_response_code_edit, 0, 1, 1, 3) # Span 3 columns

        # Row 1: Farmer Name
        filter_layout.addWidget(QLabel("Farmer Name:"), 1, 0)
        self.filter_farmer_name_edit = QLineEdit()
        self.filter_farmer_name_edit.setPlaceholderText("Contains text (case-insensitive)")
        filter_layout.addWidget(self.filter_farmer_name_edit, 1, 1, 1, 3)

        # Row 2: Village
        filter_layout.addWidget(QLabel("Village Name:"), 2, 0)
        self.filter_village_edit = QLineEdit()
        self.filter_village_edit.setPlaceholderText("Contains text (case-insensitive)")
        filter_layout.addWidget(self.filter_village_edit, 2, 1, 1, 3)

        # Row 3: Evaluation Status & KML File Status
        filter_layout.addWidget(QLabel("Evaluation Status:"), 3, 0)
        self.filter_eval_status_combo = QComboBox()
        self.filter_eval_status_combo.addItems(["All", "Not Evaluated Yet", "Eligible", "Not Eligible"])  # Match the order in EvaluationStatusDelegate
        filter_layout.addWidget(self.filter_eval_status_combo, 3, 1)

        filter_layout.addWidget(QLabel("KML File Status:"), 3, 2)
        self.filter_kml_status_combo = QComboBox()
        self.filter_kml_status_combo.addItems(["All", "Created", "Edited", "Errored", "File Deleted", "Pending Deletion"])
        filter_layout.addWidget(self.filter_kml_status_combo, 3, 3)

        # Row 4: Action Buttons
        self.apply_filters_button = QPushButton("Apply Filters")
        self.apply_filters_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.apply_filters_button.clicked.connect(self._apply_filters)
        filter_layout.addWidget(self.apply_filters_button, 4, 0, 1, 2) # Span 2 cols, align left

        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        self.clear_filters_button.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.clear_filters_button, 4, 2, 1, 2) # Span 2 cols, align right
        
        filter_layout.setColumnStretch(1, 1) # Allow middle columns to stretch a bit
        filter_layout.setColumnStretch(3, 1)

        self.filter_groupbox.setVisible(False) # Initially hidden
        return self.filter_groupbox

    def _toggle_filter_panel_visibility(self):
        is_visible = self.filter_groupbox.isVisible()
        self.filter_groupbox.setVisible(not is_visible)
        self.toggle_filter_panel_button.setText(" Filters" if is_visible else " Hide Filters")
        self.toggle_filter_panel_button.setIcon(self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileDialogDetailedView if is_visible else QStyle.StandardPixmap.SP_FileDialogListView
        ))
        self.log_message(f"Filter panel toggled to {'hidden' if is_visible else 'visible'}.")

    def _apply_filters(self):
        # Placeholder for applying filter logic
        criteria = {
            "response_code": self.filter_response_code_edit.text(),
            "farmer_name": self.filter_farmer_name_edit.text(),
            "village": self.filter_village_edit.text(),
            "evaluation_status": self.filter_eval_status_combo.currentText(),
            "kml_file_status": self.filter_kml_status_combo.currentText()
        }
        self.log_message(f"Apply filters called with criteria: {criteria}", "info")        
        if hasattr(self.filter_proxy_model, 'set_filter_criteria'):
            self.filter_proxy_model.set_filter_criteria(criteria)
        else:
            self.log_message("PolygonFilterProxyModel does not have set_filter_criteria method.", "error")

    def _clear_filters(self):
        # Placeholder for clearing filter logic
        self.filter_response_code_edit.clear()
        self.filter_farmer_name_edit.clear()
        self.filter_village_edit.clear()
        self.filter_eval_status_combo.setCurrentIndex(0) # "All"
        self.filter_kml_status_combo.setCurrentIndex(0) # "All"
        self.log_message("Clear filters called.", "info")
        if hasattr(self.filter_proxy_model, 'clear_filter_criteria'):
            self.filter_proxy_model.clear_filter_criteria()
        else:
            self.log_message("PolygonFilterProxyModel does not have clear_filter_criteria method.", "error")

    def _update_ui_for_app_mode(self):
        """Enable/disable UI elements based on the application mode."""
        app_mode = self.credential_manager.get_app_mode()
        # is_central_app = (app_mode == "Central App") # No longer solely dependent on this for sharing_info_action

        # Sharing info action is now always enabled as it serves a purpose in both modes.
        if hasattr(self, 'sharing_info_action'):
            self.sharing_info_action.setEnabled(True)
            self.sharing_info_action.setVisible(True)
            # Optionally, change text based on mode:
            # if app_mode == "Central App":
            #     self.sharing_info_action.setText("Share Central App Paths...")
            # elif app_mode == "Connected App":
            #     self.sharing_info_action.setText("Configure Central App Connection...")
            # else:
            #     self.sharing_info_action.setText("App Path Information...")

        self.log_message(f"UI updated for {app_mode} mode.", "info")

    def _open_sharing_info_dialog(self):
        app_mode = self.credential_manager.get_app_mode()
        if not app_mode:
            QMessageBox.warning(self, "Mode Error", "Application mode is not determined. Cannot open sharing/configuration dialog.")
            return

        dialog = SharingInfoDialog(self.credential_manager, app_mode, self)
        dialog.exec()

    # Placeholder for _setup_main_content_area to avoid breaking the call order
    # It's split into _setup_main_content_area_models_views and _setup_main_content_area_layout
    def _setup_main_content_area(self):
        self._setup_main_content_area_models_views()
        # Instantiation of handlers is done in __init__ after models/views are ready
        self._setup_main_content_area_layout()

    def _get_user_configurable_headers(self):
        """Returns the list of column headers that the user can show/hide/reorder."""
        if self.source_model and hasattr(self.source_model, '_headers'):
            # Exclude the first header if it's the checkbox column
            if self.source_model._headers and self.source_model._headers[0] == "": # Assuming checkbox header is empty string or specific ID
                return self.source_model._headers[1:]
            return self.source_model._headers
        return []

    def _open_table_view_editor(self):
        all_configurable_headers = self._get_user_configurable_headers()
        if not all_configurable_headers:
            QMessageBox.warning(self, "Table View Editor", "Could not retrieve column headers to configure.")
            return

        current_visible_ordered_config = self.credential_manager.load_table_view_config()
        
        # If no saved config, default to all configurable headers being visible in their original order
        if current_visible_ordered_config is None:
            current_visible_ordered_config = list(all_configurable_headers)
        else:
            # Filter current_visible_ordered_config to ensure all headers in it are valid and known
            current_visible_ordered_config = [h for h in current_visible_ordered_config if h in all_configurable_headers]


        dialog = TableViewEditorDialog(all_configurable_headers, current_visible_ordered_config, self)
        dialog.settings_saved.connect(self._handle_table_view_settings_saved)
        
        # Pass logger if dialog expects it, e.g. dialog.set_logger(self.log_message)
        # For now, dialog has its own print-based logger.

        if dialog.exec(): # This will be true if dialog.accept() was called
            self.log_message("Table view editor dialog accepted.", "info")
        else:
            self.log_message("Table view editor dialog cancelled or closed.", "info")

    def _handle_table_view_settings_saved(self, new_ordered_visible_headers: list[str]):
        self.log_message(f"Table view settings to save: {new_ordered_visible_headers}", "info")
        if self.credential_manager.save_table_view_config(new_ordered_visible_headers):
            self.log_message("Table view configuration saved successfully.", "info")
            self._apply_table_column_configuration(new_ordered_visible_headers)
        else:
            self.log_message("Failed to save table view configuration.", "error")
            QMessageBox.warning(self, "Save Error", "Could not save table view column configuration.")
    
    def _apply_table_column_configuration(self, ordered_visible_headers_config: list[str] | None = None):
        if not self.source_model or not hasattr(self.source_model, '_headers') or not self.table_view:
            self.log_message("Cannot apply table column config: model or table view not ready.", "warning")
            return

        all_model_headers = self.source_model._headers # Includes checkbox header at index 0
        
        # Determine the list of headers the user actually configured (excludes checkbox)
        user_configurable_headers_from_model = all_model_headers[1:] if all_model_headers and all_model_headers[0] == "" else all_model_headers

        final_ordered_visible_list_no_checkbox = []

        if ordered_visible_headers_config is None:
            loaded_config = self.credential_manager.load_table_view_config()
            if loaded_config is not None:
                final_ordered_visible_list_no_checkbox = [h for h in loaded_config if h in user_configurable_headers_from_model]
            else: # No saved config, default to all configurable headers visible
                final_ordered_visible_list_no_checkbox = list(user_configurable_headers_from_model)
        else: # Config was passed directly (e.g. after saving from dialog)
            final_ordered_visible_list_no_checkbox = [h for h in ordered_visible_headers_config if h in user_configurable_headers_from_model]


        header_view = self.table_view.horizontalHeader()

        # First, set visibility for all user-configurable columns
        for i, model_header_text in enumerate(user_configurable_headers_from_model):
            logical_index = i + 1 # Add 1 because column 0 is checkbox
            if model_header_text in final_ordered_visible_list_no_checkbox:
                self.table_view.setColumnHidden(logical_index, False)
            else:
                self.table_view.setColumnHidden(logical_index, True)

        # Then, reorder the visible columns
        # The checkbox column (logical index 0) is always at visual index 0 and fixed.
        # We are reordering starting from visual index 1.
        current_visual_idx_for_user_cols = 0
        for target_header_text in final_ordered_visible_list_no_checkbox:
            try:
                # Find the logical index of this header in the model (add 1 for checkbox offset)
                logical_idx_of_target_header = user_configurable_headers_from_model.index(target_header_text) + 1
            except ValueError:
                self.log_message(f"Header '{target_header_text}' from config not found in model headers. Skipping move.", "warning")
                continue

            current_visual_idx_of_target = header_view.visualIndex(logical_idx_of_target_header)
            
            # Target visual index is checkbox (0) + current_visual_idx_for_user_cols
            target_visual_index_overall = current_visual_idx_for_user_cols + 1 

            if current_visual_idx_of_target != target_visual_index_overall:
                header_view.moveSection(current_visual_idx_of_target, target_visual_index_overall)
            
            current_visual_idx_for_user_cols += 1
        
        self.log_message(f"Applied table column configuration. Visible and ordered: {final_ordered_visible_list_no_checkbox}", "info")

    def _toggle_theme(self):
        app = QApplication.instance()
        if not app or not self.credential_manager:
            self.log_message("Application instance or CredentialManager not available for theme toggle.", "error")
            return

        current_theme = self.credential_manager.load_app_theme()  # Should return 'light' or 'dark'
        new_theme = "dark" if current_theme == "light" else "light"

        self.log_message(f"Toggling theme from {current_theme} to {new_theme}", "info")

        # First save the theme preference
        if not self.credential_manager.save_app_theme(new_theme):
            self.log_message("Failed to save theme preference.", "error")
            return

        # Apply the theme
        if new_theme == "dark":
            qtmodern.styles.dark(app)
            if platform.system() == "Windows":
                try:
                    ctypes.windll.uxtheme.SetPreferredAppMode(2)  # Dark
                except Exception as e:
                    self.log_message(f"Failed to set Windows dark mode: {e}", "warning")
        else:  # Light theme
            qtmodern.styles.light(app)
            if platform.system() == "Windows":
                try:
                    ctypes.windll.uxtheme.SetPreferredAppMode(1)  # Light
                except Exception as e:
                    self.log_message(f"Failed to set Windows light mode: {e}", "warning")

        # Reload and reapply the global QSS stylesheet AFTER qtmodern style
        try:
            qss_path = resource_path("assets/style.qss")
            if os.path.exists(qss_path):
                with open(qss_path, "r") as f:
                    stylesheet = f.read()
                app.setStyleSheet(stylesheet)
                self.log_message(f"Global QSS re-applied after theme toggle.", "info")
            else:
                self.log_message(f"Global stylesheet 'assets/style.qss' not found at '{qss_path}' during theme toggle.", "warning")
        except Exception as e:
            self.log_message(f"Error reloading global stylesheet during theme toggle: {e}", "error")

        # Force a repaint of all widgets
        for widget in QApplication.allWidgets():
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

        QMessageBox.information(self, "Theme Changed", 
                              f"Theme changed to {new_theme}. Most changes should apply immediately. "
                              "Some elements might require an application restart to fully reflect the new theme.")

    def _toggle_multi_kml_mode(self):
        """Toggle between single and multi KML editing modes"""
        if self.multi_kml_view_button.isChecked():
            # Enable multi KML mode
            self.multi_kml_handler.enable_multi_kml_mode()
            # Load selected KMLs if any are checked
            # This might need a dedicated button like "Load Selected for Multi-View"
            # For now, let's assume it loads automatically or is triggered by another action.
            if not self.multi_kml_handler.load_selected_kmls():
                 # If loading failed (e.g. no selection), uncheck the button
                 self.multi_kml_view_button.setChecked(False)
                 # And revert to single KML mode UI by calling enable_single_kml_mode
                 self.multi_kml_handler.enable_single_kml_mode()
                 return # Exit early
        else:
            # Switch back to single KML mode
            self.multi_kml_handler.enable_single_kml_mode()
        
        self.log_message(f"Multi-KML mode {'enabled' if self.multi_kml_view_button.isChecked() else 'disabled'}.", "info")

    def on_multi_kml_saved(self):
        self.log_message("Multi-KML edits saved successfully.", "info")
        # After saving, typically we might want to refresh data and revert to a non-editing state.
        # This could involve going back to single KML mode or just refreshing the multi-KML view.
        # For now, just log. The MultiKmlViewEdit class handles UI state post-save.
        self.load_data_into_table() # Refresh table data

    def _setup_multi_kml_operations_panel(self):
        """Creates the GroupBox for Multi-KML operations."""
        multi_kml_group = QGroupBox("Multi-KML Operations")
        multi_kml_layout = QHBoxLayout(multi_kml_group)
        multi_kml_layout.setContentsMargins(5, 10, 5, 5)
        multi_kml_layout.setSpacing(10)

        # Multi-KML View button (blue)
        self.multi_kml_view_button = QPushButton("Multi-KML View")
        self.multi_kml_view_button.setCheckable(True)
        self.multi_kml_view_button.setStyleSheet("background-color: #0078D7; color: white; padding: 4px 8px;")
        multi_kml_layout.addWidget(self.multi_kml_view_button)
        
        # Multi-KML Editor button
        self.multi_kml_editor_button = QPushButton("Multi-KML Editor")
        multi_kml_layout.addWidget(self.multi_kml_editor_button)
        
        # Single-KML Editor button (to exit multi-KML mode)
        self.single_kml_editor_button = QPushButton("Exit Multi-KML Mode") # Renamed for clarity
        multi_kml_layout.addWidget(self.single_kml_editor_button)
        
        # Multi-KML Save button
        self.multi_kml_save_button = QPushButton("Save All Edits") # Renamed for clarity
        multi_kml_layout.addWidget(self.multi_kml_save_button)
        
        # Multi-KML Cancel button
        self.multi_kml_cancel_button = QPushButton("Cancel All Edits") # Renamed for clarity
        multi_kml_layout.addWidget(self.multi_kml_cancel_button)
        
        multi_kml_layout.addStretch()
        
        # Set initial visibility and enabled state in enable_single_kml_mode / enable_multi_kml_mode
        return multi_kml_group
