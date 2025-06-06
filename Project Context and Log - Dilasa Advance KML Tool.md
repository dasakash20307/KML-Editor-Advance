**Updated Project Context and Log**

**Date:** May 24, 2025 (Reflecting current project status and recent GE integration changes)

**1. Application Details:**

*   **Project Name:** Dilasa Advance KML Tool
*   **User Goal:** The primary user, representing Dilasa Janvikash Pratishthan, aims to develop a Windows desktop application. This tool is intended to streamline the process of managing and verifying farmer field data. Key functionalities include generating KML polygon files from various data inputs (manual, CSV, API) for visualization. A critical upcoming feature is the integration of historical satellite imagery to verify land use and farming continuity.
*   **Project Evolution & Shape:**
    *   The project initiated with a simple Tkinter-based KML generator.
    *   It evolved through stages: enhanced data input (CSV, UTM), advanced KML features (styling, descriptions), and planning for data persistence (SQLite) and API integration (mWater).
    *   **Shift to Qt (PySide6) and Modular Design (Current Major Phase):** The application was refactored to Qt (PySide6) for a modern UI and better scalability, adopting a modular structure (`ui/`, `core/`, `database/`). This phase included a new main window, advanced `QTableView` for data display with filtering and sorting, custom dialogs, splash screen, and branding.
    *   **Basic Mapping Implemented:** An initial map viewport using `QWebEngineView` and `Folium` was added to display selected farmer polygons from the database.
    *   **Google Earth Integration Refined:** The method for viewing polygons in Google Earth was changed from an AHK-based automation to a manual KML import workflow, guided by an in-app instructional popup.
    *   **Next Major Feature - Historical Imagery Integration (Current Development Focus):** The immediate next goal is to develop a "Historical Map Builder" feature. This will involve allowing users to define areas of interest (e.g., via Shapefiles), using the Google Earth Engine (GEE) Python API to fetch and process historical satellite imagery for these areas, storing these images and their geographic bounds locally, and then enabling users to view these cached historical images in the main map viewport, overlaid with specific farmer polygons.

**2. Application Road Map:**

*   **a. Tkinter Versions (Conceptual Precursors):** (As previously described - basic KML, CSV input, advanced Tkinter features leading to Qt decision)
*   **b. Qt Version (Current - Beta.v4.001.Dv-A.Das - Pre-Historical Imagery):**
    *   **Added (So Far):**
        *   Complete UI rewrite from Tkinter to PySide6.
        *   Modular project structure (`ui/`, `core/`, `database/`).
        *   Qt UI elements: `QMainWindow`, custom header, `QToolBar`, `QMenuBar`, `QStatusBar`.
        *   `QTableView` with `PolygonTableModel` and `PolygonFilterProxyModel` for DB data display, filtering, and sorting.
        *   Checkboxes in table for bulk actions ("Select/Deselect All").
        *   Qt Dialogs: `APISourcesDialog`, `DuplicateDialog`, `OutputModeDialog`.
        *   Custom `QSplashScreen` (via `main_app.py`'s `CustomSplashScreen`).
        *   Map Viewport: `MapViewWidget` using `QWebEngineView` + `folium` to display selected polygons (defaulting to Esri Satellite).
        *   Google Earth View: A `GoogleEarthWebViewWidget` for displaying Google Earth.
        *   Interaction with Google Earth:
            *   Removed previous AHK-based automation for KML uploading.
            *   Implemented a new workflow: when a polygon is selected while Google Earth View is active, a temporary KML file is generated, its path is copied to the clipboard, and an instructional popup appears.
            *   The popup guides the user through manual steps in Google Earth (Ctrl+I, Ctrl+V, Enter, Ctrl+H).
            *   The popup includes a "Do not show this popup again" option for the current session.
            *   These instructions are also accessible via a "GE Instructions" action in the Help menu.
        *   Fully functional CSV and mWater API data import with DB persistence and duplicate handling.
        *   KML generation (single/multiple file modes) from checked table items, with DB export status updates.
        *   "Export Displayed Data as CSV", "Clear All Data", "Delete Checked Rows" features.
    *   **Removed/Changed:** All Tkinter UI code. Removed AHK script (`google_earth_upload.ahk`) and associated direct process invocation.
    *   **How it works (Current):** Application launches with splash. Main window displays data from SQLite in a sortable/filterable table. Users can import data via CSV or mWater API, with duplicates handled. KML files are generated for checked items. The map view (either Folium or Google Earth) shows the currently selected valid polygon. If Google Earth view is active and a polygon is selected, a temporary KML is created, its path is copied, and a popup guides the user for manual import into Google Earth.
    *   **Upcoming:** The "Historical Map Builder" feature will be added to download and manage historical GEE imagery, and the map view will be enhanced to display these historical layers.

**3. Log File (Major Achievements & Milestones):**

*   Initial Tkinter KML generator.
*   CSV input, styling, UTM/altitude handling.
*   Decision to refactor to Qt and modular design.
*   **Project Restarted/Refactored with Qt (PySide6) and Modular Structure.**
*   `DatabaseManager` for SQLite.
*   Core modules: `data_processor.py`, `kml_generator.py`, `api_handler.py`, `utils.py`.
*   Qt `MainWindow` shell, `QSplashScreen`, header, menus, toolbar, status bar.
*   `QTableView` with `PolygonTableModel`, `PolygonFilterProxyModel`.
*   Dialogs ported to Qt: `APISourcesDialog`, `DuplicateDialog`, `OutputModeDialog`.
*   CSV and mWater API import functional with DB persistence.
*   KML generation from Qt UI with DB export tracking.
*   Advanced table filtering, sorting, bulk actions via checkboxes.
*   Integrated `MapViewWidget` using `QWebEngineView` and `folium` to display selected polygons.
*   Implemented `GoogleEarthWebViewWidget` for an alternative map view.
*   **Refined Google Earth Integration:**
    *   Removed AHK-based automation for uploading KMLs to Google Earth.
    *   Introduced a manual KML import workflow: on polygon selection in GE view, a temporary KML is generated, its path is copied to clipboard.
    *   An instructional `QMessageBox` guides the user on how to load this KML into Google Earth (Ctrl+I, Ctrl+V, etc.).
    *   Added a "Do not show again" checkbox to the instruction popup.
    *   Added a "GE Instructions" item to the Help menu to re-display the popup.
*   **Current Stage:** The core application with data management, KML generation, and dual map views (Folium & Google Earth with manual KML import) is stable. The next major development phase is the implementation of the "Historical Imagery" feature.

**4. Libraries Used Currently (Beta v4.x - Pre-Historical Imagery):**

*   **PySide6:** (QtWidgets, QtGui, QtCore, QtWebEngineWidgets, QtWebEngineCore)
*   **sqlite3:** (Python built-in)
*   **requests:** For mWater API calls.
*   **simplekml:** For KML generation.
*   **utm:** For UTM to Latitude/Longitude conversions.
*   **Pillow:** For logo image handling.
*   **folium:** For generating Leaflet.js maps (HTML).
*   **Standard Python libraries:** `os`, `sys`, `re`, `datetime`, `csv`, `io.StringIO`, `json`, `tempfile`.

**5. Current Version Structure (DilasaKMLTool_v4 - Based on provided code):**
```
DilasaKMLTool_v4/
├── main_app.py
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── splash_screen.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── api_sources_dialog.py
│   │   ├── duplicate_dialog.py
│   │   └── output_mode_dialog.py
│   └── widgets/
│       ├── __init__.py
│       ├── map_view_widget.py
│       └── google_earth_webview_widget.py # Added
├── core/
│   ├── __init__.py
│   ├── data_processor.py
│   ├── kml_generator.py
│   ├── api_handler.py
│   └── utils.py
├── database/
│   ├── __init__.py
│   └── db_manager.py
├── assets/
│   ├── dilasa_logo.jpg
│   └── app_icon.ico
├── .gitignore
├── requirements.txt
└── README.md
```
*(Note: `scripts/` directory and `google_earth_upload.ahk` removed from structure if previously listed)*

**6. Current Goal: Implement the "Historical Imagery" Feature**

*   **Develop the "Historical Map Builder" functionality:**
    *   Create a new dialog (`HistoricalMapBuilderDialog`):
        *   Allow users to upload a Shapefile to define administrative boundaries or areas of interest (AOIs).
        *   Enable selection of a specific feature/area from the Shapefile to process.
        *   Provide inputs for selecting a range of years and potentially GEE image collections/parameters.
    *   Create a new core module (`core/gee_handler.py`):
        *   Implement Google Earth Engine (GEE) authentication.
        *   Include functions to process satellite imagery:
            *   Fetch imagery for the selected AOI geometry and year(s).
            *   Perform operations like cloud masking and temporal compositing (e.g., median annual composite).
            *   Obtain a download URL for the processed raster image.
            *   Extract and retrieve the geographic bounds (e.g., `[[lat_min, lon_min], [lat_max, lon_max]]`) of the final processed image for the AOI.
    *   Integrate GEE processing with the dialog, likely using a `QThread` (`GEEProcessingThread`) for non-blocking background operations.
    *   Implement local caching:
        *   Download the processed images (e.g., PNG or GeoTIFF).
        *   Store images in a structured local directory, e.g., `local_historical_imagery/{AreaName}/{Year}/image.png`.
        *   Save the corresponding geographic bounds metadata alongside each image (e.g., `local_historical_imagery/{AreaName}/{Year}/bounds.json`).
*   **Integrate Historical Imagery Viewing in `MainWindow` and `MapViewWidget`:**
    *   Add UI elements to `MainWindow` (e.g., a checkable "Enable Historical View" group box, a "Year" `QComboBox`) to control historical imagery display.
    *   When a farmer's polygon is selected in the main table:
        *   Develop logic to link this polygon to a cached "Area Name" (e.g., using `polygon_data.block` or a similar field that corresponds to the `AreaName` used by the builder).
        *   Scan the `local_historical_imagery/{AreaName}/` directory to find available years (where both image and bounds.json exist) and populate the "Year" `QComboBox`.
    *   When a year is selected:
        *   `MapViewWidget` must be enhanced with a method (e.g., `display_local_image_overlay`) to:
            *   Load the specified local historical image.
            *   Read its geographic bounds from the corresponding `.json` file.
            *   Display this image as a raster overlay on the map (using `folium.raster_layers.ImageOverlay` or similar).
            *   Ensure the selected farmer's polygon is drawn on top of the historical image.
*   **General Considerations:**
    *   Ensure robust error handling for GEE operations, file I/O, and network requests.
    *   Provide user feedback during long GEE processing and download tasks.

**7. Future Aspects and Possible Features:**
*   Advanced Polygon Editor, more sophisticated historical imagery display (sliders, NDVI), user settings, reporting, batch KML, GIS analysis, improved error handling, installer.

**8. Self Prompt (AI - Instructions for Starting Historical Imagery Feature):**

*   **Project Initialization:**
    *   Add `geopandas` and `earthengine-api` to `requirements.txt` and install them.
    *   Create empty files: `core/gee_handler.py` and `ui/dialogs/historical_map_builder_dialog.py`.
    *   Create a directory: `local_historical_imagery/` (and add to `.gitignore` if contents are large/dynamic).
*   **Phase 1: GEE Handler Basics & Authentication (`core/gee_handler.py`)**
    *   Implement `authenticate_ee()` and `initialize_ee()` functions.
    *   Test basic GEE connection.
*   **Phase 2: Historical Map Builder Dialog - UI Shell (`ui/dialogs/historical_map_builder_dialog.py`)**
    *   Design and implement the basic UI layout:
        *   `QPushButton` for "Select Shapefile".
        *   `QLineEdit` (read-only) to display Shapefile path.
        *   `QComboBox` or `QListWidget` to display features/attributes from Shapefile (e.g., "Block Name").
        *   `QSpinBox` or `QLineEdit` for "Start Year" and "End Year".
        *   (Optional) `QComboBox` for GEE image collection (e.g., "Sentinel-2", "Landsat 8").
        *   `QPushButton` "Start Building Cache".
        *   `QTextEdit` for progress logging.
    *   Implement the "Select Shapefile" functionality using `QFileDialog`.
    *   Connect the dialog launch from `MainWindow` (e.g., via a new menu action/toolbar button).
*   **Phase 3: Shapefile Processing & Area Selection (in `historical_map_builder_dialog.py`)**
    *   Use `geopandas` to read the selected Shapefile.
    *   Populate the `QComboBox`/`QListWidget` with a chosen attribute field from the Shapefile so the user can select a specific area/feature.
    *   Store the geometry of the selected area.
*   **Next Steps (following Feature Pipeline):** Proceed with GEE image processing logic in `gee_handler.py`, thread implementation in the dialog, local image/bounds saving, and then integration into `MainWindow` and `MapViewWidget` for display. Focus on robustly saving and then reading the geographic bounds for `ImageOverlay`.


## Development Log - Evaluation Status, API Dialog, Build Prep, and Bug Fixes - May 24, 2025

This log covers a period of significant feature additions, bug fixing, and preparation for broader deployment.

**1. Initial Feature Implementation & Enhancements:**

*   **Evaluation Status Feature:**
    *   Added an "Evaluation Status" column to the `PolygonTableModel` and `QTableView`.
    *   Implemented a `QComboBox` delegate (`EvaluationStatusDelegate`) for this column, allowing users to select from "Not Evaluated Yet", "Eligible", or "Not Eligible".
    *   The selected status is now persisted in the SQLite database (new `evaluation_status` column in the `polygons` table).
    *   Row-wide background coloring logic was implemented in `PolygonTableModel.data()` based on the `evaluation_status` to visually distinguish records.
*   **API Import Progress Dialog:**
    *   A new `APIImportProgressDialog` was created to provide users with feedback (total records, processed, skipped, new) during mWater API data imports. This dialog includes a progress bar and a cancel button.
*   **Build Preparation:**
    *   Initial steps were taken to prepare for x86 and x64 Windows builds, including considerations for `requirements.txt` and potential platform-specific issues (though no specific build scripts were created in this phase).
*   **UI & UX Refinements:**
    *   Added "Select/Deselect All" checkbox functionality for the main table.
    *   Improved logging within the application for better debugging and status tracking.

**2. Key Bugs Encountered & Resolved:**

*   **Database Schema Migration:**
    *   **Issue:** The `evaluation_status` column was not being added to already existing databases, causing "no such column: evaluation_status" errors upon application start or when interacting with the new feature.
    *   **Resolution:** A schema migration step was implemented in `DatabaseManager.create_tables()` to check for the existence of the `evaluation_status` column and add it if missing, ensuring backward compatibility.
*   **Model/Database Interaction (`PolygonTableModel` & `db_manager`):**
    *   **Issue:** The `PolygonTableModel` was initially unable to access the `db_manager` instance to save changes made to the "Evaluation Status" via the delegate.
    *   **Resolution:** The `MainWindow` now correctly passes its `db_manager` instance to the `PolygonTableModel` during initialization. The model's `setData` method now uses this passed instance to call `db_manager.update_evaluation_status()`.
*   **Application Startup `SyntaxError`:**
    *   **Issue:** A persistent `SyntaxError: ("('[ ', 999)"` (or similar line number near EoF) was encountered when attempting to run the application, caused by extraneous `[start of <filename>]` and `[end of <filename>]` markers being repeatedly appended to `ui/main_window.py` by the `read_files` and `overwrite_file_with_block` tool interactions.
    *   **Resolution:** The file `ui/main_window.py` was manually cleaned by reading its content, stripping all non-Python markers after the true end of the Python code (the `super().closeEvent(event)` line), and then overwriting the file with this cleaned content.
*   **Pylance Static Analysis Warnings:**
    *   **`statusBar` Naming Conflict:** Renamed `self.statusBar` to `self._main_status_bar` in `MainWindow`'s `_create_status_bar` and `log_message` methods to avoid potential conflicts with `QMainWindow.statusBar()` and resolve Pylance warnings.
    *   **Missing `cleanup` method:** Added a placeholder `cleanup(self): pass` method to `GoogleEarthWebViewWidget` to satisfy calls from `MainWindow.closeEvent()`.
    *   **Model Type Assertion:** Added `assert isinstance(source_model, PolygonTableModel)` in `PolygonFilterProxyModel.filterAcceptsRow` for type safety and to aid static analysis.
*   **QTableView Background Color Update Issue:**
    *   **Issue:** Despite the model providing the correct background color via its `data()` method for the `BackgroundRole`, and the `dataChanged` signal being emitted for the entire row, the `QTableView` was not visually updating the background color of the row's cells when the "Evaluation Status" was changed. The text values in other cells of the row updated correctly, but the background color specifically remained unchanged.
    *   **Resolution:** The issue was resolved by ensuring proper signal emission and view refresh mechanisms. The `QTableView` now correctly updates row background colors when the evaluation status changes, providing the intended visual feedback to distinguish between different evaluation states.

**3. Current Status & Outstanding Issue (as of May 24, 2025):**

*   **Application Functionality:**
    *   The application now successfully starts and loads data from the database.
    *   The "Evaluation Status" for polygons can be changed using the `QComboBox` in the table.
    *   These status changes are correctly saved to the database.
    *   The `PolygonTableModel`'s internal data (`self._data`) is updated correctly when the status changes.
    *   The `PolygonTableModel.data()` method returns the appropriate `QColor` for the `BackgroundRole` based on the updated `evaluation_status`.
    *   The `dataChanged` signal is emitted for the entire row (using `self.index(row, 0)` to `self.index(row, self.columnCount() - 1)`) after a status update, which is intended to signal the view to re-fetch data for all roles for that row.
    *   **RESOLVED:** The `QTableView` now properly displays row background colors that update in real-time when evaluation status changes. The background color issue has been successfully fixed, and the view correctly processes the `dataChanged` signal for `BackgroundRole` updates, providing proper visual feedback to users.