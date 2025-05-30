**Project Update Report: KML-Editor-Advance - Transition to Beta V5.0 Dev-ADas (Detailed Version)**

---
**Glossary of Terms and References**
---

* **CA1 (Change Area 1):** Refers to the planned "Overhaul of the Online Fetch System & KML File Handling." This includes the shift to a KML-first data approach where KML files are generated and stored persistently upon data acquisition, with the database primarily storing metadata.
* **CA2 (Change Area 2):** Refers to the planned "Table System, Filters, and CSV Import/Export Enhancements." This covers updates to the main data table, its filtering capabilities, and CSV functionalities to align with v5 data structures.
* **CA3 (Change Area 3):** Refers to the planned "Viewport Updates (Standard Map & KML Editor)." This focuses on enhancing the map display and introducing a visual KML editor, with OpenLayers being the chosen technology for the editor.
* **CA4 (Change Area 4):** Refers to the planned "Central Data Management System (Central vs. Connected App Mode)." This introduces dual operating modes, shared data access over LAN, and associated locking mechanisms for database and KML files.
* **CA5 (Change Area 5):** Refers to the planned "App Launcher / Loading Screen." This involves creating a new application entry point with an informative loading screen.
* **CA6 (Change Area 6):** Refers to the planned "Modern UI Design and Styling for PySide6." This focuses on updating the application's visual appearance using themes like Fusion, `qtmodern`, and custom QSS.
* **Part X (e.g., "CA4 Part 1"):** Refers to a specific sub-task or component within the broader plan for the referenced Change Area, as detailed in our discussions and the reorganized plan.
* **KML-first:** An architectural approach where the KML file is treated as the primary source of truth for geographic data (geometry, description) once created, with the database storing metadata and a reference (filename) to this KML file.
* **CredentialManager:** A new core component responsible for managing device identity (UUID, nickname), application mode (Central/Connected), and paths to the main database and KML storage folder. It uses a local secondary database (`device_config.db`).
* **Locking Mechanism:** Refers to the application-level file-based locking system (for both the main database and individual KML files) to manage concurrent access in the Central/Connected App setup.
* **OpenLayers:** A JavaScript library chosen for implementing the advanced KML visual editor within a `QWebEngineView`.
* **QWebChannel:** A PySide6 module for bidirectional communication between Python and JavaScript running in `QWebEngineView`.


---
**1. Introduction**
---
This report provides an in-depth, task-by-task breakdown for updating the "KML-Editor-Advance" application from Beta v4.001.Dv-A.Das to the new "Beta V5.0 Dev-ADas." It builds upon our collaborative planning sessions, incorporating all decisions regarding functionality, architecture, UI, and risk mitigation. The goal is to create a KML-first application with advanced editing, shared access capabilities, an improved launcher, and a modern UI.

---
**Phase 0: Project Setup & Foundational UI**
---

**Task 1: Initial Styling & Project Setup (from CA6)**

* **Task Prompt:**
    * "In this initial task, we'll lay the visual and structural groundwork for the entire v5 application. We'll set up modern styling defaults, ensure high-DPI compatibility, and prepare for a consistent look and feel across all new and existing components."
* **Detailed Description:**
    * **Functionality:** Establishes the base visual theme and application-level display settings for v5. Ensures the application looks crisp on high-resolution displays and adopts a more modern aesthetic from the outset.
    * **Alignment with v4 Modules & Modifications:**
        * **`main_app.py`**: This file's role will evolve. For v5, its direct execution will be superseded by `launcher_app.py` (Task 2). The `QApplication` setup logic within it will be adapted and called by `launcher_app.py`.
            * **Addition (in `launcher_app.py` or adapted `main_app.py` logic):** Code to set `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)` will be added *before* the `QApplication` instance is fully initialized.
            * **Addition (in `launcher_app.py` or adapted `main_app.py` logic):** Code to `app.setStyle('Fusion')` will be added after the `QApplication` instance is created.
            * **Addition (Conditional for Windows, in `launcher_app.py` or adapted `main_app.py` logic):** Import `ctypes` and add code to call `ctypes.windll.uxtheme.SetPreferredAppMode(2)` (forcing dark mode for consistency with `qtmodern.styles.dark`) to enable Windows native dark mode awareness. This should be done very early.
            * **Addition (in `launcher_app.py` or adapted `main_app.py` logic):** Code to load a global QSS stylesheet (from `assets/style.qss`).
        * **`qtmodern` Integration (New Library):**
            * Calls like `qtmodern.styles.dark(app)` will be added after `app.setStyle('Fusion')`. The main window instance will be wrapped with `qtmodern.windows.ModernWindow`.
    * **Folder and File Structure:**
        * **New File:** `assets/style.qss`. This file will contain the global Qt StyleSheet rules, to be developed iteratively.
    * **UI Structure:**
        * No new direct UI elements are created in this task, but the settings applied here will affect the rendering of *all* subsequent UI elements across the entire application.
    * **Libraries Structure & Connections:**
        * **`PySide6`**: Its core `QApplication` and widget rendering will be influenced by these settings.
        * **`qtmodern`** (Python package, to be added to `requirements_new.txt`): Provides pre-built modern themes and window frames.
        * **`ctypes`** (Python built-in): Used for OS-level integration on Windows for dark mode.
    * **Connections of Modules and UI Elements:** The `QApplication` instance, configured in `launcher_app.py`, will globally affect how all `QWidget`-based classes and their elements are styled and scaled.

---
**Task 2: App Launcher Implementation (Basic) (from CA5)**

* **Task Prompt:**
    * "We will now create the new entry point for our application: a dedicated App Launcher. This launcher will display an informative loading screen while the main application initializes, providing users with feedback and important startup diagnostics."
* **Detailed Description:**
    * **Functionality:** Provides an immediate visual feedback (loading screen) upon application start. Manages and displays the progress of the main application's initialization. Shows logs and error messages if startup issues occur.
    * **Alignment with v4 Modules & Modifications:**
        * **`main_app.py`**:
            * **Refactor:** The `CustomSplashScreen` class within `main_app.py` and its associated `QTimer` logic for showing the main window will be *deleted*. The core logic for creating the `MainWindow` and the application instance will be refactored, likely into a main application controller class or a set of functions, to be invoked and managed by the new `launcher_app.py`. The `main()` function in `main_app.py` as an entry point will be removed.
        * **`ui/splash_screen.py`**:
            * **Retire as UI Component:** This file will be *retired* as a directly used UI component for the splash screen.
            * **Adapt Visuals/Constants:** Its visual design elements (logo placement, text arrangement from `CustomSplashScreen` in `main_app.py`, and constants like `INFO_COLOR_CONST_SPLASH` from `ui/splash_screen.py`) *can be reused or adapted* by the new `LoadingScreenWidget` for visual consistency.
    * **Folder and File Structure:**
        * **New File:** `launcher_app.py` (becomes the main executable Python script for the project).
        * **New File:** `ui/loading_screen_widget.py` (defines the UI class for the loading screen).
    * **UI Structure:**
        * **`LoadingScreenWidget` (e.g., a class inheriting `QWidget` or `QDialog`, configured to be modal, frameless, and always-on-top):**
            * `QLabel` elements for: App Name, Company Name, Tagline, Version Code (v5), Developer Name, Support Email.
            * `QProgressBar` widget.
            * Collapsible section (e.g., `QGroupBox` with a checkable title or a `QPushButton` toggling visibility of a `QWidget` container) holding a read-only `QTextEdit` for logs.
            * This widget will be styled according to the global styles established in Task 1.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtCore`, `QtGui`):** Used to build `LoadingScreenWidget` and manage its event loop.
        * **`QThread` (from `PySide6.QtCore`):** Essential for running the main application's initialization tasks in a background thread, ensuring the `LoadingScreenWidget` UI remains responsive.
    * **Connections of Modules and UI Elements:**
        * `launcher_app.py` will:
            1.  Perform the early `QApplication` setup (HighDPI, Fusion style, Windows dark mode hook, global QSS from Task 1).
            2.  Create and display the `LoadingScreenWidget` instance.
            3.  Instantiate and start a `QThread`. The thread's `run()` method will execute the main application's initialization sequence (including logic from the refactored `main_app.py` and new components like `CredentialManager`).
            4.  The main application's initialization code will emit signals (or use a direct callback mechanism suitable for thread communication) to the `LoadingScreenWidget` instance to update logs (`append_log(message, level)`) and progress (`update_progress(value, text_status)`).
            5.  Upon completion (success or failure) of the initialization sequence, the thread will signal `launcher_app.py`.
            6.  `launcher_app.py` will then either hide/close the `LoadingScreenWidget` and show the fully initialized `MainWindow` (on success) or keep the launcher visible, displaying error messages from the logs (on failure).

---
**Phase 1: Core Architectural Changes (Data Model & Application Mode)**
---

**Task 3: CredentialManager & First Run Setup (from CA4 Part 1)**

* **Task Prompt:**
    * "This task establishes the application's identity and operational mode. We'll create a system to give each installation a unique ID and nickname, allow the user to choose if it's a Central or Connected app, and configure the necessary data paths accordingly. This is a one-time setup on first launch."
* **Detailed Description:**
    * **Functionality:**
        * On the application's first ever launch on a machine (detected by the absence or state of `device_config.db`):
            * Prompts the user for a device nickname.
            * Generates and stores a unique 8-digit alphanumeric device UUID.
            * Allows the user to select the application mode: "Central App" or "Connected App."
            * Guides the user to configure paths for the main database file and the KML files folder. For "Central App" mode, these are local paths where new data will be created/managed. For "Connected App" mode, these are the network/shared paths pointing to an existing Central App's data.
        * Persistently stores these settings in the local `device_config.db`.
        * Provides methods for other parts of the application to access these critical settings (device ID, nickname, app mode, main data paths).
    * **Alignment with v4 Modules & Modifications:**
        * This functionality is entirely **new** for v5. V4 used a fixed AppData path for its database (`DB_FOLDER_NAME_CONST`, `DB_FILE_NAME_CONST` in `database/db_manager.py`). This hardcoded path logic will be *deleted* from `db_manager.py`.
    * **Folder and File Structure:**
        * **New File:** `core/credential_manager.py`. This module will define the `CredentialManager` class.
        * **New File:** `ui/first_run_setup_dialogs.py`. This module will define the various `QDialog` subclasses used in the setup sequence.
        * **New Database File (Secondary DB - always local):** `device_config.db`. This SQLite database will be created by `CredentialManager` in a standard local application data directory (e.g., using `platformdirs` library for robust cross-platform path determination, or `os.getenv('APPDATA')/DilasaKMLTool_V5_Config/` as a fallback).
    * **UI Structure:**
        * A sequence of modal `QDialog`s (defined in `ui/first_run_setup_dialogs.py`), all styled by the global theme (Task 1):
            1.  **Nickname Dialog:** `QLabel` instruction, `QLineEdit` for nickname, "Next" `QPushButton`.
            2.  **Mode Selection Dialog:** `QLabel` instruction, two `QRadioButton`s ("Central App", "Connected App"), "Next" `QPushButton`.
            3.  **Path Configuration Dialog (dynamic content):**
                * **If "Central App" mode:** `QLabel`s for "Main Database File Path" and "KML Files Folder Path", `QLineEdit`s (read-only) to display selected paths, "Browse" `QPushButton`s using `QFileDialog.getSaveFileName` (for DB) and `QFileDialog.getExistingDirectory` (for KML folder).
                * **If "Connected App" mode:** `QLabel`s for "Central App's Database File Path (Network Path)" and "Central App's KML Files Folder Path (Network Path)", two `QLineEdit`s for user to type/paste these shared paths.
                * "Finish Setup" `QPushButton` (triggers validation and saving).
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtCore`):** For all dialogs and UI elements.
        * **`sqlite3`** (Python built-in): Used by `CredentialManager` to interact with `device_config.db`.
        * **`os`** (Python built-in): For path manipulations, creating directories.
        * **`uuid`** (Python built-in): `uuid.uuid4().hex[:8]` for generating device ID.
        * **(Consider) `platformdirs`** (Python package, new): For robustly determining the local app data directory for `device_config.db`.
    * **Connections of Modules and UI Elements:**
        * `launcher_app.py` (during its initialization phase, via the background thread) will instantiate `CredentialManager`.
        * `CredentialManager.is_first_run()` is called. If true, `launcher_app.py` (or `CredentialManager`) will instantiate and execute the sequence of `FirstRunSetupDialogs`.
        * User input is collected by these dialogs and passed to `CredentialManager` to be saved into `device_config.db`.
        * On subsequent launches, `CredentialManager` loads settings from `device_config.db`. Other modules query `CredentialManager` for these settings.

---
**Task 4: New DB Schema & KML Storage Setup (from CA1 Part 1 & DB aspects of CA4)**

* **Task Prompt:**
    * "With the application mode and primary data paths defined, we now need to set up the main v5 database structure and establish where KML files will be physically stored. This involves defining new tables/columns and ensuring our database manager can work with user-defined paths."
* **Detailed Description:**
    * **Functionality:**
        * Defines the complete SQL schema for the main `polygon_data` table in the v5 database.
        * Modifies `DatabaseManager` to connect to and manage a database file at a path provided by `CredentialManager`.
        * Establishes the root folder (path from `CredentialManager`) where KML files will be stored.
    * **Alignment with v4 Modules & Modifications:**
        * **`database/db_manager.py`**: Significantly modified.
            * **Modification (Constructor):** Changed from `__init__(self, db_folder_name=None, db_file_name=None)` to `__init__(self, db_path)`. Logic for constructing AppData paths is *deleted*.
            * **Modification (`_create_tables` method):** Defines the v5 `polygon_data` table schema:
                * Retained/Adapted from v4 schema: `id` (PK), `uuid` (UNIQUE), `response_code` (UNIQUE), `farmer_name`, `village_name`, `block`, `district`, `proposed_area_acre`, `p1_utm_str`...`p4_substituted` (now for *initial* 4-point import data only), `error_messages`, `kml_export_count`, `last_kml_export_date`, `date_added`, `last_modified`, `evaluation_status`.
                * **New Columns for v5:** `device_code` (TEXT), `kml_file_name` (TEXT NOT NULL), `kml_file_status` (TEXT: "Created", "Errored", "Edited", "File Deleted", "Pending Deletion"), `edit_count` (INT DEFAULT 0), `last_edit_date` (TIMESTAMP), `editor_device_id` (TEXT), `editor_device_nickname` (TEXT).
                * The v4 `status` column is effectively replaced by `kml_file_status` and the validity implied by having a non-errored KML.
            * **Decision on Migration (`_migrate_schema` method):** For this v5 plan, a **fresh v5 database setup is assumed**. The `_create_tables` method in `db_manager.py` will establish the complete v5 schema if the database file is new or empty. The existing `_migrate_schema` function for `evaluation_status` is noted but a full v4->v5 migration utility is out of scope for this initial v5 feature plan.
            * **Modification (Data Access Methods):** All CRUD methods (`add_or_update_polygon_data`, `get_all_polygon_data_for_display`, etc.) will be updated for the new v5 columns.
    * **Folder and File Structure:**
        * Main SQLite database (e.g., `dilasa_main_data_v5.db`) at path from `CredentialManager`.
        * KML storage folder (e.g., `kml_files/`) at path from `CredentialManager`, containing `[UUID].kml` files.
    * **UI Structure:** No direct UI changes, but defines the data backend for UI tables.
    * **Libraries Structure & Connections:**
        * **`sqlite3`** (Python built-in): Used by `DatabaseManager`.
    * **Connections of Modules and UI Elements:**
        * `CredentialManager` provides `db_path` and `kml_root_path`.
        * `DatabaseManager` is instantiated with `db_path`.
        * This `DatabaseManager` instance is used by modules needing DB access (e.g., `MainWindow`).
        * KML handling logic uses `kml_root_path` + `kml_file_name`.

---
**Phase 2: Core Data Ingestion & Basic Display (KML-First)**
---

**Task 5: API Fetch & KML Generation/Storage (from CA1 Part 2)**

* **Task Prompt:**
    * "Implement the new data fetching mechanism. When data is retrieved from an API, we will immediately generate a KML file for each record, store it persistently, and save associated metadata (including the KML filename) to our new v5 database."
* **Detailed Description:**
    * **Functionality:** Fetches data from mWater APIs. For each valid record, it generates a KML file with a dynamic description, saves this KML to the designated KML storage folder, and then writes a comprehensive metadata record (including KML filename and initial status) to the main SQLite database. Handles duplicate checking based on `response_code`.
    * **Alignment with v4 Modules & Modifications:**
        * **`core/api_handler.py`**: The `fetch_data_from_mwater_api` function will be retained for fetching raw data. Its return (list of dicts) will be consumed by new logic in `MainWindow`.
        * **`core/data_processor.py`**: The `process_csv_row_data` function will be adapted. While its primary role is for CSVs, its logic for parsing UTM, handling point data, and structuring data into a dictionary will be influential. For API data, a similar processing step will be needed to map API fields to the v5 DB schema and prepare data for KML generation.
        * **`core/kml_generator.py`**:
            * **Modification:** `create_kml_description_for_placemark` will be significantly changed. It will receive the full data record (from API/CSV). It will iterate through its items, excluding a predefined list of keys (e.g., UUID, response_code, internal DB fields, p1_utm_str, etc.), and format the rest as "Key: Value" or "Key: N/A" for the KML description.
            * **Modification:** `add_polygon_to_kml_object` will be used to generate the KML structure. It should correctly use the (potentially 4) initial points.
        * **`ui/main_window.py`** (`handle_fetch_from_api` and new helper methods):
            * **Major Refactor:** The `handle_fetch_from_api` method will orchestrate the new KML-first workflow:
                1.  Call `api_handler.fetch_data_from_mwater_api`.
                2.  For each returned row (record):
                    a.  Process the raw record to map fields to v5 DB structure and prepare data for KML description (similar to `core/data_processor.py` logic).
                    b.  Generate a UUID if not present (though API data should have it).
                    c.  Check for duplicate `response_code` in DB (using `db_manager.check_duplicate_response_code`). If duplicate, skip or handle as per definitive duplicate strategy (current plan: skip and log).
                    d.  Call `kml_generator` to create a `simplekml.Kml` object.
                    e.  Construct KML filename (e.g., `f"{uuid_value}.kml"`).
                    f.  Determine full path using `kml_root_path` from `CredentialManager`.
                    g.  Attempt to save the KML file (this write needs KML file lock - Task 9).
                    h.  If KML save successful:
                        i.  Prepare metadata dictionary for DB insertion (UUID, response\_code, `kml_file_name`, `kml_file_status`="Created", `date_added`, `device_code` if available from API, `editor_device_id` and `editor_device_nickname` from `CredentialManager` as the creator).
                        j.  Call `db_manager.add_or_update_polygon_data` (this write needs DB lock - Task 8).
                    k.  If KML save fails: Log error, prepare metadata with `kml_file_name`=NULL, `kml_file_status`="Errored", and save to DB.
            * Uses `APIImportProgressDialog` for user feedback.
    * **Folder and File Structure:** Uses existing core modules, but KML files are now saved to the folder configured in Task 4 (e.g., `[main_kml_folder_path]/[UUID].kml`).
    * **UI Structure:**
        * User interaction is via the existing "Fetch from API" button and `APISourcesDialog`.
        * `APIImportProgressDialog` provides feedback.
        * The main table will refresh, showing newly added records.
    * **Libraries Structure & Connections:**
        * **`requests`**: For HTTP calls.
        * **`simplekml`**: For KML object creation and saving.
        * **`sqlite3`**: Via `DatabaseManager`.
        * **`csv`, `io.StringIO`**: If API returns CSV formatted text data.
    * **Connections of Modules and UI Elements:**
        * `MainWindow` (UI) -> `api_handler` (core) -> `kml_generator` (core) -> `CredentialManager` (for paths/IDs) -> `DatabaseManager` (database) -> `MainWindow` (update table UI).
        * Locking mechanisms from `core/sync_manager.py` will be called before KML file saves and DB writes.

---
**Task 6: Update Table Model & Display (from CA2 Part 1)**

* **Task Prompt:**
    * "Now that our database schema is updated for v5 and data ingestion populates these new fields, we need to ensure our main UI table correctly displays all this new information, such as KML filenames, statuses, and edit history."
* **Detailed Description:**
    * **Functionality:** The main data table in the `MainWindow` will display all relevant metadata columns from the v5 `polygon_data` table, providing users with comprehensive information about each record and its associated KML file.
    * **Alignment with v4 Modules & Modifications:**
        * **`ui/main_window.py`**:
            * **`PolygonTableModel` class**:
                * **Modification (`_headers` list):** This list will be significantly expanded to include user-friendly names for all new v5 columns: `Device Code`, `KML File Name`, `KML File Status`, `Times Edited`, `Last Edit Date`, `Editor Device ID`, `Editor Nickname`, in addition to adapted v4 columns like `UUID`, `Response Code`, `Evaluation Status`, `Farmer Name`, `Village`, `Date Added`, `Export Count`, `Last Exported`. Column order to be determined for best UX.
                * **Modification (`data()` method):** Logic will be updated to fetch and return data for these new columns from the `self._data` list (which holds tuples from the DB query). Correct mapping of tuple indices to columns is critical.
                * **Modification (`columnCount()` method):** Will return the new total number of columns.
                * The existing logic for checkbox column (`CHECKBOX_COL`), ID column, evaluation status display and background role will be maintained and correctly indexed.
            * **`QTableView` Setup (`_setup_main_content_area`):**
                * Column widths (`table_view.setColumnWidth`) will need to be adjusted for the new columns.
                * The `EvaluationStatusDelegate` will continue to be set for the `evaluation_status` column.
    * **Folder and File Structure:** Primarily modifications within `ui/main_window.py`.
    * **UI Structure:**
        * The `QTableView` in the `MainWindow`'s right pane is the main UI element affected. Its appearance will change due to the new columns.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtCore`, `QtGui`):** For `QTableView`, `QAbstractTableModel`, delegates.
    * **Connections of Modules and UI Elements:**
        * `DatabaseManager.get_all_polygon_data_for_display()` (modified in Task 4 to fetch new columns) provides data to `PolygonTableModel.update_data()`.
        * `PolygonTableModel` then provides data (including for new columns) to the `QTableView` for display.
        * User interactions with the table (sorting, selection) are handled by `QTableView` and its model.

---
**Task 7: Basic KML Loading & Description Display in MapView (from CA1 Part 3 & CA3 Part 1)**

* **Task Prompt:**
    * "With KML files being central to v5, our map view needs to display polygons by loading these files directly. We'll also implement a way to show the KML's description alongside the map."
* **Detailed Description:**
    * **Functionality:** When a user selects a row in the main data table, the map view (`MapViewWidget` or its successor) will load the associated KML file (identified by `kml_file_name` from the database). It will parse this KML to display the polygon on the map and show its embedded description in a read-only view.
    * **Alignment with v4 Modules & Modifications:**
        * **`ui/widgets/map_view_widget.py`**: This widget will be significantly modified or potentially replaced by a new `KMLEditorViewWidget` if the editing functionality (Task 11) is integrated directly into it. For this task, we assume modifications to the existing `MapViewWidget` to support KML loading for display.
            * **New Method (e.g., `load_kml_for_display(kml_file_path)`):**
                1.  Takes the full path to a KML file.
                2.  Uses `simplekml` (or another KML parsing library if `simplekml` is only for writing) to parse the KML file. If `simplekml` cannot easily parse, a library like `lxml` or Python's built-in `xml.etree.ElementTree` could be used to extract coordinates and description.
                3.  Extracts the polygon coordinates (outer boundary).
                4.  Extracts the KML placemark's description content.
                5.  Clears any previous polygons from the Folium map.
                6.  Uses `folium.Polygon` (or similar) to draw the new polygon on the map, centering/zooming appropriately. This reuses logic from v4's `display_polygon` but data source is now KML.
                7.  Updates a dedicated UI element (see UI Structure below) to display the extracted KML description.
            * The existing `_initialize_map` and `update_map` methods for handling Folium will be used.
        * **`ui/main_window.py` (`on_table_selection_changed` method)**:
            * **Modification:** When a table row is selected:
                1.  Get the `kml_file_name` for the selected record from `PolygonTableModel`.
                2.  Get the `main_kml_folder_path` from `CredentialManager`.
                3.  Construct the full path to the KML file.
                4.  If the path is valid and file exists:
                    * Call `map_view_widget.load_kml_for_display(full_kml_path)`.
                    * Update `kml_file_status` in DB to "File Deleted" (with DB lock) if file does not exist, then refresh table row.
                5.  If KML is invalid or file doesn't exist, clear map and description panel.
    * **Folder and File Structure:** Primarily modifications to `ui/widgets/map_view_widget.py` and `ui/main_window.py`.
    * **UI Structure:**
        * **Within `MapViewWidget` or an adjacent panel in `MainWindow`:**
            * A `QTextEdit` (read-only, styled) will be added to display the KML description. This could be part of the map view widget's layout or a separate widget that `MainWindow` manages and updates.
        * The `QWebEngineView` within `MapViewWidget` continues to display the Folium map.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtWebEngineWidgets`, `QtCore`):** For UI elements and map display.
        * **`folium`**: To generate the map with the polygon.
        * **`simplekml`** (or `lxml`/`xml.etree.ElementTree`): For parsing KML file content to extract coordinates and description.
        * **`core/utils.py` (`resource_path`)**: Used by `MapViewWidget` if loading local HTML/JS assets, and by `MainWindow` to construct paths.
    * **Connections of Modules and UI Elements:**
        * `MainWindow` (table selection event) -> gets `kml_file_name` from `PolygonTableModel` and `kml_root_path` from `CredentialManager`.
        * `MainWindow` -> calls method in `MapViewWidget` instance, passing the KML file path.
        * `MapViewWidget` -> parses KML -> uses `folium` to update `QWebEngineView` content -> updates its internal description display UI element.

---
**Phase 3: Implementing Shared Access & Locking**
---

**Task 8: Database Locking Mechanism (from CA4 Part 2)**

* **Task Prompt:**
    * "To enable safe concurrent use of the main database in our Central/Connected App model, we must implement a robust locking mechanism. This task involves creating a system that prevents simultaneous write operations to the shared SQLite database, using a file-based lock."
* **Detailed Description:**
    * **Functionality:** Implements an application-level distributed mutex for the main SQLite database file. Before any write operation, an app must acquire a lock by creating a `.db.lock` file. If the lock is already held, the app waits and informs the user. The lock file contains information about the current holder and expected duration, with mechanisms for heartbeats during long operations and stale lock detection/override.
    * **Alignment with v4 Modules & Modifications:** This is entirely **new** functionality. V4 had no shared access or locking.
    * **Folder and File Structure:**
        * **New Module (Recommended):** `core/sync_manager.py`. This module will contain classes/functions for `DatabaseLockManager` and later `KMLFileLockManager`.
        * **Lock File:** A file named e.g., `[main_db_filename].lock` (e.g., `dilasa_main_data_v5.db.lock`) will be created/deleted in the *same directory* as the main database file (path from `CredentialManager`).
    * **UI Structure:**
        * Non-modal popups or status bar messages in `MainWindow` (e.g., "Database is in use by [nickname], trying again in X_s...") when waiting for a lock.
        * A modal `QMessageBox` prompt for the user if a stale lock is detected and an override is being offered.
    * **Libraries Structure & Connections:**
        * **`os`**: For file existence checks, creation, deletion of lock files.
        * **`json`** (or simple text I/O): For reading/writing metadata to the lock file (locking device ID/nickname, start time, expected duration, heartbeat, operation description).
        * **`datetime`, `time`**: For timestamps, calculating durations, and timeouts.
        * **`PySide6.QtCore.QTimer`**: For periodically re-checking the lock status when an app is waiting, without freezing the UI.
    * **Connections of Modules and UI Elements:**
        * The `DatabaseLockManager` in `core/sync_manager.py` will provide methods like `acquire_db_lock(expected_duration, operation_description, current_device_id, current_device_nickname)` and `release_db_lock()`.
        * **All modules performing database write operations** (e.g., `MainWindow` methods for API fetch, CSV import, saving evaluation status, and the KML editor save function when it updates DB metadata) **MUST** call `acquire_db_lock()` before the DB transaction and `release_db_lock()` in a `finally` block after the transaction (or on error).
        * If `acquire_db_lock()` indicates the lock is held, the calling function in `MainWindow` will update the UI (status bar/popup) and start a `QTimer` to retry.
        * `CredentialManager` provides the current app's device ID and nickname to be written into the lock file.

---
**Task 9: KML File Locking Mechanism (from CA4 Part 3)**

* **Task Prompt:**
    * "Similar to database locking, we need to protect individual KML files from concurrent modification or deletion when an application is actively working on them, especially during editing or initial creation in the shared KML folder."
* **Detailed Description:**
    * **Functionality:** Implements an application-level lock for individual KML files. Before creating a new KML file or opening an existing KML for editing (which implies a future save/overwrite), an app must acquire a lock specific to that KML file (e.g., `[UUID].kml.lock`). This prevents other apps (especially the Central App during delete operations) from interfering with an active KML file operation.
    * **Alignment with v4 Modules & Modifications:** This is entirely **new** functionality.
    * **Folder and File Structure:**
        * The `KMLFileLockManager` logic will reside in `core/sync_manager.py` (alongside `DatabaseLockManager`).
        * **Lock Files:** For a KML file `[UUID].kml`, a corresponding lock file `[UUID].kml.lock` will be created/deleted in the *same shared KML folder* (path from `CredentialManager`).
    * **UI Structure:**
        * If a user tries to edit a KML and the `.kml.lock` file already exists (and is held by another user), `MainWindow` will show a `QMessageBox` or status message: "KML file [filename] is currently locked by [nickname]. Cannot edit now."
        * Central App: If a delete operation (single or bulk) encounters a locked KML file, a summary message at the end of the operation will inform the user which files were skipped due to locks.
        * Prompts for stale KML lock overrides, similar to DB stale locks but potentially with shorter timeout considerations.
    * **Libraries Structure & Connections:**
        * **`os`, `json` (or simple text I/O), `datetime`, `time`**: For lock file operations.
        * **`PySide6.QtCore.QTimer`**: If waiting for a KML file lock.
    * **Connections of Modules and UI Elements:**
        * The `KMLFileLockManager` in `core/sync_manager.py` will provide methods like `acquire_kml_lock(kml_filename, current_device_id, current_device_nickname)` and `release_kml_lock(kml_filename)`.
        * **KML Creation (Task 5 - API Fetch, Task 10 - CSV Import):** Before `simplekml.save()`, `acquire_kml_lock()` is called. `release_kml_lock()` is called after successful save or on error.
        * **KML Editing (Task 11 - KML Editor):**
            * When "Edit" button is clicked, `acquire_kml_lock()` for the target KML. If it fails, disallow editing.
            * Lock is held during the editing session.
            * `release_kml_lock()` is called when "Save" (after file write) or "Cancel" is clicked.
        * **KML Deletion (Central App only, in `MainWindow` methods like `handle_delete_checked_rows`):** Before attempting to delete a KML file, the Central App calls a method like `can_delete_kml(kml_filename)` which checks for the presence of `[kml_filename].lock`. If locked, deletion of that file is skipped.

---
**Phase 4: Enhanced Features & UI Refinements**
---

**Task 10: Enhanced CSV Import & Template Export (from CA2 Part 2)**

* **Task Prompt:**
    * "Update our CSV import functionality to align with the new v5 data requirements, including KML generation and storage. Also, add a feature allowing users to export a CSV template to guide their data preparation."
* **Detailed Description:**
    * **Functionality (Enhanced CSV Import):**
        * Imports data from user-selected CSV files.
        * Validates that CSV rows contain all new mandatory v5 metadata columns (defined in `core/data_processor.py`).
        * For each valid row:
            1.  Processes data (UTM parsing, etc.) using `core/data_processor.py`.
            2.  Generates a KML file with dynamic description based on other columns in the CSV.
            3.  Saves the KML file to the designated KML folder (using KML file lock).
            4.  Saves all relevant metadata (including KML filename, creator's device ID/nickname from `CredentialManager`, "Created" status) to the database (using DB lock).
        * Handles duplicates based on `response_code` (skip and log).
        * Provides user feedback via `APIImportProgressDialog`.
    * **Functionality (Template Export CSV):**
        * Allows users to save a blank CSV file containing only the header row.
        * Headers include all mandatory v5 metadata columns, 4-corner point data columns, and a few example columns for data that would go into the KML description.
    * **Alignment with v4 Modules & Modifications:**
        * **`core/data_processor.py`**:
            * **Modification (`CSV_HEADERS` constant):** Update to include all new v5 mandatory headers.
            * **Modification (`process_csv_row_data` function):** Revise to validate for new mandatory columns. Its output dictionary must align with the v5 DB schema and provide enough info for KML generation.
        * **`ui/main_window.py` (`handle_import_csv` method)**:
            * **Major Refactor:** This method will now mirror the complexity of `handle_fetch_from_api` (Task 5), orchestrating CSV row reading -> `data_processor` -> KML generation (`kml_generator`) -> KML save (with KML lock) -> DB save (with DB lock).
            * **New Method (e.g., `handle_export_csv_template`):** This new method will define the header list and use `QFileDialog.getSaveFileName` to allow the user to save the template.
        * **`core/kml_generator.py`**: Used as in Task 5 for KML generation.
    * **Folder and File Structure:** Modifications to existing core and UI modules.
    * **UI Structure:**
        * Existing "Import CSV" action (`QAction` and toolbar button) in `MainWindow` triggers the enhanced import.
        * **New UI Element:** A new `QAction` (e.g., "Export CSV Template...") added to the "File" or "Data" menu in `MainWindow`.
        * `APIImportProgressDialog` reused for CSV import.
    * **Libraries Structure & Connections:**
        * **`csv`** (Python built-in): For reading user CSVs and writing the template CSV.
        * **`simplekml`**: For KML generation.
        * **`PySide6`**: For `QFileDialog` and UI elements.
    * **Connections of Modules and UI Elements:**
        * `MainWindow` (UI "Import CSV") -> reads CSV -> calls `data_processor` for each row -> `kml_generator` -> saves KML (using `CredentialManager` for path, `sync_manager` for KML lock) -> `DatabaseManager` (using `sync_manager` for DB lock).
        * `MainWindow` (UI "Export CSV Template") -> defines headers -> writes CSV file via `QFileDialog`.

---
**Task 11: KML Visual Editor (OpenLayers) (from CA3 Part 2)**

* **Task Prompt:**
    * "This is a major feature: implement the visual KML editor using OpenLayers within a web view. Users should be able to load a KML, see its polygon on an interactive map, visually modify its boundary points (drag, add, delete vertices), edit its description, and save these changes back to the KML file and database."
* **Detailed Description:**
    * **Functionality:**
        * Loads the KML associated with the selected table row into an OpenLayers map embedded in `QWebEngineView`.
        * Allows user to toggle an "Edit Mode."
        * In Edit Mode:
            * Displays polygon vertices, allowing them to be dragged.
            * Allows new vertices to be added to polygon segments.
            * Allows existing vertices to be deleted.
            * A separate panel allows editing of the KML placemark's name and description fields (potentially key-value pairs or rich text).
        * "Save" action:
            * Retrieves modified geometry from OpenLayers and description from Qt panel.
            * Re-generates the KML file content (now potentially with a different number of points).
            * Overwrites the KML file in the KML storage folder (acquiring/releasing KML file lock).
            * Updates DB metadata (`last_edit_date`, `edit_count`, `editor_device_id/nickname`, `kml_file_status` to "Edited") (acquiring/releasing DB lock).
        * "Cancel" action: Discards all changes.
    * **Alignment with v4 Modules & Modifications:**
        * **`ui/widgets/map_view_widget.py`**: This widget will likely be heavily refactored or replaced by a new, dedicated `KMLEditorViewWidget` to encapsulate the `QWebEngineView` and the OpenLayers integration logic. The Folium-based display logic will be superseded by OpenLayers for this view when editing.
        * **`core/kml_generator.py`**: Its functions (`add_polygon_to_kml_object`, `create_kml_description_for_placemark`) will be crucial for re-generating the KML content after edits. `add_polygon_to_kml_object` must be enhanced to handle a list of coordinates with a variable number of points, not just fixed P1-P4.
    * **Folder and File Structure:**
        * **New/Modified Widget:** `ui/widgets/kml_editor_view_widget.py` (or heavily modified `map_view_widget.py`).
        * **New Web Assets Folder:** `assets/js_libs/openlayers/` (to store downloaded OpenLayers `ol.js`, `ol.css`, etc.). (Task discussed previously for bundling)
        * **New HTML/JS/CSS for Editor:**
            * `ui/web_content/kml_editor/kml_editor.html` (or similar path): The HTML page loaded into `QWebEngineView`, which hosts the OpenLayers map `div`.
            * `ui/web_content/kml_editor/kml_editor_map.js`: Custom JavaScript for OpenLayers map setup, KML loading, editing interactions (`ol.interaction.Select`, `ol.interaction.Modify`), and communication with Python via `QWebChannel`.
            * `ui/web_content/kml_editor/kml_editor_styles.css`: Custom CSS for the `kml_editor.html` page if needed.
    * **UI Structure:**
        * **Within `KMLEditorViewWidget` (or equivalent):**
            * The `QWebEngineView` displaying `kml_editor.html` (which contains the OpenLayers map).
            * `QPushButton` "Edit KML" (toggles edit mode).
            * `QPushButton` "Save Changes" (visible in edit mode).
            * `QPushButton` "Cancel Edit" (visible in edit mode).
            * A panel (e.g., `QDockWidget` or `QFrame` alongside/below the map view) containing:
                * `QLineEdit` for KML Placemark Name.
                * `QTextEdit` (or a more structured editor if KML description is key-value) for KML Description.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtWebEngineWidgets`, `QtWebEngineCore`, `QtCore.QWebChannel`):** For the widget, web view, and Python-JS bridge.
        * **`OpenLayers`** (JavaScript library): Bundled in `assets/js_libs/openlayers/` and referenced by `kml_editor.html`. Used for all map display and visual geometry editing within the HTML page.
        * **`simplekml`**: Used by the Python side to parse the initial KML (if needed beyond what OpenLayers JS handles for loading) and, crucially, to re-generate and save the KML file from the (potentially modified) geometry and description data.
        * **`json`** (Python built-in): Likely used by `QWebChannel` or custom JS-Python communication to pass geometry data (e.g., as GeoJSON).
    * **Connections of Modules and UI Elements:**
        1.  `MainWindow` (on table selection) tells `KMLEditorViewWidget` the path to the KML file to load.
        2.  `KMLEditorViewWidget` (Python) calls JS function `loadKmlToMap(kml_content_or_path)` via `QWebChannel`. It also loads KML name/description into Qt input widgets.
        3.  User clicks "Edit KML" button (Qt).
        4.  `KMLEditorViewWidget` (Python) calls JS function `enableMapEditing()` via `QWebChannel`.
        5.  User edits geometry on the OpenLayers map (JS). JS uses OpenLayers interactions. Changes to geometry are communicated back to Python via `QWebChannel` (e.g., JS calls `pythonInterface.updateEditedGeometry(new_coords_geojson)`). Python stores this in a temporary "edited state" object.
        6.  User edits name/description in Qt input widgets. Python updates the "edited state" object.
        7.  User clicks "Save Changes" button (Qt).
        8.  `KMLEditorViewWidget` (Python):
            a.  Acquires KML file lock (via `sync_manager`).
            b.  Acquires DB lock (via `sync_manager`).
            c.  Uses `simplekml` and the "edited state" (geometry from JS, description from Qt) to generate new KML content.
            d.  Saves the KML file.
            e.  Updates database metadata (`edit_count`, `last_edit_date`, `editor_device_id/nickname` from `CredentialManager`, `kml_file_status`="Edited") via `DatabaseManager`.
            f.  Releases DB lock, then KML file lock.
            g.  Calls JS function `disableMapEditing()` and reloads the map with the saved KML.
            h.  Refreshes relevant row in `MainWindow`'s table.
        9.  User clicks "Cancel Edit": Python discards "edited state", calls JS `disableMapEditing()`, reloads original KML in map. Releases KML file lock if acquired for edit mode initiation.

---
**Task 12: Refine Table Filters & Evaluation Status (from CA2 Part 3)**

* **Task Prompt:**
    * "Ensure our table's filtering capabilities are fully functional with the new v5 data columns, particularly the new 'KML File Status'. Also, confirm the existing 'Evaluation Status' dropdown and its associated row coloring still work correctly."
* **Detailed Description:**
    * **Functionality:** Allows users to effectively filter the main data table based on the new v5 metadata, especially the `kml_file_status`. Ensures the `evaluation_status` feature (dropdown and row coloring) remains operational and accurate.
    * **Alignment with v4 Modules & Modifications:**
        * **`ui/main_window.py`**:
            * **`PolygonFilterProxyModel` class**:
                * **Modification (`filterAcceptsRow` method):** The logic for filtering by "Record Status" (v4) will be adapted/replaced to filter by the new `kml_file_status` column from the source model (`PolygonTableModel`). Users will select from "Created", "Errored", "Edited", "File Deleted" in the filter dropdown.
                * Other filters (UUID, Date Added, Export Status) will be checked to ensure they correctly access data from the v5 `PolygonTableModel` structure.
            * **`EvaluationStatusDelegate` and `PolygonTableModel.data()` for `BackgroundRole`**: This functionality is intended to be preserved. Ensure that the column index for `evaluation_status` is correctly used by the delegate and the `data()` method for background coloring, matching the updated `PolygonTableModel`.
    * **Folder and File Structure:** Primarily modifications within `ui/main_window.py`.
    * **UI Structure:**
        * The "Filter Panel" `QGroupBox` in `MainWindow`.
        * The `QComboBox` for "Record Status" filter will now be populated with the values of `kml_file_status` (e.g., "All", "Created", "Errored", "Edited", "File Deleted").
        * The `QComboBox` for `evaluation_status` within the table (via `EvaluationStatusDelegate`) and the row background colors remain key UI aspects.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtCore.QSortFilterProxyModel`, `QtWidgets`):** For the filter model and UI elements.
    * **Connections of Modules and UI Elements:**
        * User changes filter criteria in the Filter Panel UI.
        * Signals from these UI elements (e.g., `QLineEdit.textChanged`, `QComboBox.currentIndexChanged`) trigger methods in `MainWindow` like `apply_filters()`.
        * `apply_filters()` calls setter methods on the `PolygonFilterProxyModel` instance (e.g., `set_kml_file_status_filter(text)`).
        * `PolygonFilterProxyModel` re-evaluates its filter, causing the `QTableView` to update.
        * Changes to `evaluation_status` via the delegate in the table trigger `PolygonTableModel.setData()`, which updates the DB (with DB lock) and emits `dataChanged` to refresh the view (including background color).

---
**Task 13: Revised KML Download/Export (from CA1 Part 4)**

* **Task Prompt:**
    * "Update the KML export functionality ('Generate KML for Checked Rows') to work with our new KML-first approach. Instead of generating KMLs from database coordinates on-the-fly, it will now use the persistently stored KML files."
* **Detailed Description:**
    * **Functionality:** Allows users to export KML data for selected rows from the main table.
        * **"Single Consolidated KML File" mode:** Reads the individual KML files (associated with checked table rows) from the KML storage folder, parses them, and merges all their placemarks into a single new KML object/file for the user to save.
        * **"Multiple Individual KML Files" mode:** Copies the individual KML files (associated with checked table rows) directly from the KML storage folder to a user-selected output directory.
        * Updates the `kml_export_count` and `last_kml_export_date` in the database for each successfully exported record (requires DB lock).
    * **Alignment with v4 Modules & Modifications:**
        * **`ui/main_window.py` (`handle_generate_kml` method)**:
            * **Major Refactor:**
                1.  Get list of checked item `db_id`s from `PolygonTableModel`.
                2.  For each `db_id`, fetch the corresponding `kml_file_name` from the database (via `DatabaseManager.get_polygon_data_by_id()`).
                3.  Construct the full path to each KML file using `kml_root_path` from `CredentialManager`.
                4.  Filter out records where KML file doesn't exist or `kml_file_status` is "Errored" or "File Deleted".
                5.  Prompt user for output folder and KML output mode (using `OutputModeDialog`).
                6.  **If "Single" mode:**
                    a.  Create a new `simplekml.Kml` object for the consolidated output.
                    b.  For each valid source KML file: Parse it (e.g., using `simplekml` if it supports robust parsing of its own files, or `lxml`), extract its placemarks (name, description, geometry), and add them as new placemarks to the consolidated KML object. This is more complex than simply merging KML text. The easiest way if using `simplekml` might be to re-create each placemark's geometry and description in the new KML object.
                    c.  Save the consolidated KML file.
                7.  **If "Multiple" mode:**
                    a.  For each valid source KML file, copy it (using `shutil.copy()`) to the user's output folder.
                8.  For each record successfully included in the export, update its `kml_export_count` and `last_kml_export_date` in the database (this requires acquiring DB lock once for all updates).
                9.  Refresh table to show updated export counts.
        * **`core/kml_generator.py`**: Its role in *direct* KML generation during export is diminished, as KMLs already exist. However, its methods for creating placemark descriptions or structuring KML features might be reused if reconstructing placemarks for the "Single Consolidated" mode.
    * **Folder and File Structure:** Reads KMLs from the configured KML storage folder. Writes exported KMLs to user-chosen location.
    * **UI Structure:**
        * Existing "Generate KML for Checked Rows..." action and `OutputModeDialog` are used.
    * **Libraries Structure & Connections:**
        * **`simplekml`**: Potentially for parsing source KMLs (if it has good parsing features) and for creating the new consolidated KML object in "Single" mode.
        * **`lxml` or `xml.etree.ElementTree`** (Python built-in): Alternative/supplement for parsing KML files if `simplekml` is insufficient for reading placemark details from existing files.
        * **`shutil`** (Python built-in): For file copying in "Multiple" mode.
        * **`PySide6`**: For `QFileDialog`.
    * **Connections of Modules and UI Elements:**
        * `MainWindow` (UI action) -> `PolygonTableModel` (get checked IDs) -> `DatabaseManager` (get `kml_file_name`s) -> `CredentialManager` (get KML root path).
        * Logic in `MainWindow` handles KML file operations (parsing/copying) and then calls `DatabaseManager` (with DB lock) to update export statuses.

---
**Task 14: Central App Path Sharing UI & Connected App Network Checks (from CA4 Part 4)**

* **Task Prompt:**
    * "To help users set up 'Connected Apps,' the 'Central App' needs an easy way to display its shared data paths. Additionally, 'Connected Apps' should perform checks upon startup to ensure they can reach the central resources and inform the user if not."
* **Detailed Description:**
    * **Functionality (Central App Path Sharing UI):**
        * A new dialog or information panel within the Central App that clearly displays its currently configured main database file path and KML files folder path.
        * Provides "Copy to Clipboard" buttons for each path to make it easy for users to transfer these paths when configuring a Connected App.
    * **Functionality (Connected App Network Checks):**
        * During the startup sequence of a Connected App (managed by `launcher_app.py` after initial configuration):
            * Attempt to verify access to the configured network path for the Central App's database file (e.g., check if parent directory exists, perhaps try a non-locking connection test if feasible without full DB init).
            * Attempt to verify access to the configured network path for the Central App's KML files folder (e.g., check if directory exists).
            * If any path is inaccessible, the launcher screen will display a clear error message guiding the user (e.g., "Cannot connect to Central App at [path]. Please ensure the Central App ([Central_Nickname]) is running, folders are shared correctly, and network is available."). The main application might not fully load or operate in a degraded mode.
    * **Alignment with v4 Modules & Modifications:** This is entirely **new** functionality.
    * **Folder and File Structure:**
        * **New Dialog (Potential):** `ui/sharing_info_dialog.py` (for Central App to display paths).
        * Path checking logic will be in `launcher_app.py`'s initialization sequence for Connected Apps, using paths from `CredentialManager`.
    * **UI Structure:**
        * **Central App:**
            * New `QAction` (e.g., "Sharing Information" or "View Data Paths") in a menu (e.g., "Settings" or "File").
            * This action opens the `SharingInfoDialog` (modal) containing:
                * `QLabel`s: "Central App Data Paths:"
                * `QLabel`: "Database File Path:", `QLineEdit` (read-only, displaying path), `QPushButton` ("Copy").
                * `QLabel`: "KML Files Folder Path:", `QLineEdit` (read-only, displaying path), `QPushButton` ("Copy").
                * `QPushButton` ("Close").
        * **Connected App (Launcher Screen):**
            * The log panel of the `LoadingScreenWidget` (Task 2) will display status messages like "Connecting to Central Database at [path]..." and error messages if connection fails.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets`, `QtCore.QClipboard`):** For the dialog, UI elements, and copying paths to clipboard.
        * **`os.path`**: For checking path existence/accessibility (with caution for network paths, as permissions can also be an issue).
    * **Connections of Modules and UI Elements:**
        * **Central App:** Menu Action -> opens `SharingInfoDialog`. Dialog reads current paths from `CredentialManager` instance. "Copy" buttons use `QApplication.clipboard()`.
        * **Connected App:** `launcher_app.py` -> `CredentialManager` (get paths) -> OS/network checks. Results update `LoadingScreenWidget` logs. If checks fail critically, `launcher_app.py` may prevent `MainWindow` from showing or show `MainWindow` in a limited state.

---
**Task 15: Full Launcher Integration & Logging (from CA5 Part 2)**

* **Task Prompt:**
    * "Fully integrate the App Launcher with all stages of the application's startup. Ensure it provides comprehensive and accurate progress updates and logs, especially reflecting the complexities of initializing in Central or Connected mode and handling potential startup errors."
* **Detailed Description:**
    * **Functionality:** The `LoadingScreenWidget` (created in Task 2) will now be actively updated throughout the entire application initialization sequence. It will display detailed status messages and reflect progress through key startup stages such as:
        * Loading basic configuration.
        * Executing First-Run Setup (if applicable).
        * Initializing `CredentialManager` and determining app mode/paths.
        * If Connected App: Attempting to connect to Central resources, checking network paths, initial handshake with DB/KML lock files if implemented.
        * Initializing `DatabaseManager` with the correct DB path.
        * Creating the `MainWindow` instance.
        * Populating initial data in `MainWindow` (e.g., loading data into the table).
        * Reporting any errors encountered during these steps in its log panel.
    * **Alignment with v4 Modules & Modifications:** This task ensures the new launcher (Task 2) properly replaces the v4 splash screen functionality from `main_app.py` and `ui/splash_screen.py` with a much more interactive and informative process.
    * **Folder and File Structure:** Primarily involves `launcher_app.py` and `ui/loading_screen_widget.py`, and the refactored main application initialization logic (which might be a class instantiated by the launcher).
    * **UI Structure:** The `LoadingScreenWidget` UI (progress bar, log panel) will be actively updated.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtCore.QThread`, signals/slots):** For communication between the background initialization thread and the `LoadingScreenWidget` on the main UI thread.
    * **Connections of Modules and UI Elements:**
        * The main application initialization sequence (running in a `QThread` started by `launcher_app.py`) will be broken down into logical stages.
        * After each stage, or for important sub-steps, the initialization logic will emit signals (or use another thread-safe callback mechanism) with status messages, log messages (and log levels), and progress values.
        * Slots in `LoadingScreenWidget` (or methods called via `QMetaObject.invokeMethod` for thread safety) will receive these signals/calls and update the progress bar and `QTextEdit` log panel accordingly.
        * If a critical error is emitted, the `LoadingScreenWidget` might change its state (e.g., show an error icon, halt progress bar) and ensure error logs are visible.

---
**Task 16: Finalize Styling & Theming (from CA6 Part 2)**

* **Task Prompt:**
    * "With all functional components and new UI elements in place, perform a final pass on the application's styling. Ensure the chosen modern theme (Fusion + `qtmodern` + custom QSS) is consistently and correctly applied across the entire application for a polished, professional look and feel."
* **Detailed Description:**
    * **Functionality:** Ensures all UI components, including main window, all dialogs (first-run setup, API sources, output mode, sharing info, KML editor panels, message boxes), all widgets (buttons, tables, input fields, labels, progress bars, etc.) consistently adhere to the v5 modern visual theme.
    * **Alignment with v4 Modules & Modifications:**
        * Any remaining widget-specific `setStyleSheet` calls within v4 modules (e.g., in `ui/main_window.py`, `ui/dialogs/*`) should be reviewed and likely *removed* if they conflict with the global `style.qss` or `qtmodern` theme. The goal is a single source of truth for styling.
    * **Folder and File Structure:**
        * **`assets/style.qss`:** This file will be extensively developed and refined to cover all application elements.
    * **UI Structure:** Affects the visual appearance of *every* UI element in the application.
    * **Libraries Structure & Connections:**
        * **`PySide6` (`QtWidgets.QApplication.setStyleSheet`):** Used to apply the global QSS.
        * **`qtmodern`**: If used, its theme provides the base styling. Custom QSS will refine this.
    * **Connections of Modules and UI Elements:**
        * The global stylesheet set in `launcher_app.py` (Task 1) will apply to all subsequently created widgets and dialogs.
        * Iterative testing and refinement of `assets/style.qss` will be needed by visually inspecting all parts of the application. Tools like Qt Designer (for previewing QSS on widgets) or in-app QSS editors (for advanced debugging) can be helpful.

---
**5. Key Technologies & Libraries Summary (Consolidated for v5)**
---
* **Core Framework:** `PySide6` (QtWidgets, QtCore, QtGui, QtWebEngineWidgets, QtWebChannel)
* **Styling & UI Enhancement:** `qtmodern` (Python package), `ctypes` (Python built-in for Windows), Custom QSS.
* **Database:** `sqlite3` (Python built-in).
* **Data Handling & KML:**
    * `requests` (for API calls).
    * `simplekml` (for KML generation and potentially parsing).
    * `lxml` or `xml.etree.ElementTree` (Python built-in, alternative for KML parsing if needed).
    * `utm` (for UTM conversions).
    * `folium` (primarily for the existing Google Earth view's KML import guide context; its direct map display role in the main map view is superseded by OpenLayers for KML editing).
    * `csv`, `json` (Python built-ins).
* **KML Visual Editor:** `OpenLayers` (JavaScript library, to be bundled as assets).
* **File/OS Operations & Utilities:** `os`, `uuid`, `shutil`, `datetime`, `time`, `io.StringIO` (Python built-ins).
* **(Considered) Path Management:** `platformdirs` (Python package, for robust local app data paths).

---
**6. Critical Considerations & Risks Highlighted (Consolidated for v5)**
---
* **Shared SQLite & Locking Mechanism:** The custom file-based locking for both the database (`.db.lock`) and individual KML files (`.kml.lock`) is the most critical and complex part of the Central/Connected app model. Robust implementation, especially for stale lock detection (heartbeats, timeouts, user overrides), is paramount to prevent data corruption or deadlocks. This remains the highest risk area.
* **KML Visual Editor (OpenLayers & QWebChannel):** Implementing a feature-rich visual KML editor using OpenLayers within `QWebEngineView`, complete with reliable Python-JavaScript communication via `QWebChannel`, is a significant development effort and technical challenge.
* **Error Handling & User Feedback:** Comprehensive error handling and clear, informative user feedback are essential across all new features, particularly for network operations (Connected App mode), file operations (KML saving/loading, lock files), data parsing/validation, and during the KML editing process.
* **Performance:**
    * KML parsing and rendering (especially for large or numerous KMLs loaded into OpenLayers).
    * Bulk operations (API fetch, CSV import) involving iterative KML generation, file saving, and DB writes, all while managing locks.
    * Network latency affecting Connected App responsiveness.
    These aspects need to be monitored and optimized if they lead to poor user experience.
* **Scope of KML Editor:** While aiming for a "Google-like" experience, the initial v5 visual editor will focus on core geometry (vertex move/add/delete) and description editing. Advanced features (complex styling UI within editor, multi-geometry, etc.) would be post-v5.
* **First-Run Setup & Configuration:** Making the initial setup intuitive for both Central and Connected app modes, especially path configuration for shared resources, is key to user adoption of this feature.
* **Data Migration from v4:** This plan assumes a fresh v5 database. Migrating existing v4 data to the new v5 schema and KML-first structure is a separate, non-trivial task not included in this feature development plan.

---
This highly detailed report now outlines each task with specific actions, impacts on existing code, new components, and their interconnections, keeping your feedback in mind. It should serve as a comprehensive blueprint for the development of Beta V5.0 Dev-ADas of the Dilasa Advance KML Tool.

This concludes my role as the "v5 Updater and Planner" for this planning session. I have done my best to consolidate all our discussions and decisions into this final detailed plan.
