# Dilasa Advance KML Tool

## Overview

The **Dilasa Advance KML Tool** is a Windows desktop application developed for Dilasa Janvikash Pratishthan. It's designed to simplify the management of farmer field data, facilitate KML polygon generation (now with a KML-first approach in v5), and integrate with Google Earth for enhanced data visualization and verification.

## Core Features

*   **Data Management:**
    *   Import farmer and plot data via CSV files or directly from mWater APIs, generating persistent KML files for each valid record.
    *   Store and manage metadata in a user-configurable SQLite database, linked to these KML files. The database tracks KML status, edit history, and device information.
*   **KML Generation:**
    *   KML files are automatically generated and stored upon data import (API/CSV) as part of the KML-first workflow.
    *   Create KML polygon files from selected records for use in GIS software.
*   **Map Visualization & Google Earth Integration:**
    *   View selected polygons on an integrated map (Folium-based with OpenStreetMap/Esri Satellite).
    *   Switch to an embedded Google Earth Web View.
    *   When a polygon is selected in the Google Earth View:
        *   A temporary KML file is automatically created.
        *   The path to this KML file is copied to the clipboard.
        *   A popup provides clear, step-by-step instructions for manual import into Google Earth (Ctrl+I, Ctrl+V, Enter, Ctrl+H for historical view).
    *   The instruction popup includes a "Do not show this popup again" option.
    *   Instructions are also accessible from the "Help" menu ("GE Instructions").
*   **Upcoming - Advanced Historical Imagery Analysis:**
    *   Integration with Google Earth Engine (GEE) to fetch, process, and cache historical satellite imagery for specified areas of interest.
    *   Tools to view these GEE-processed historical images overlaid with farmer polygons within the application.

## Main UI Components & Functions

*   **Main Window:**
    *   **Menu Bar:** Access to File (Export CSV), Data (Import CSV, Fetch from API, Manage API Sources, Delete Data), KML (Generate), View (Toggle Google Earth View), and Help (About, GE Instructions).
    *   **Toolbar:** Quick access buttons for common actions like Import CSV, API Fetch, Toggle GE View, Generate KML, and Delete Checked Rows.
    *   **Map/Google Earth View Pane:** Displays either the Folium map or the Google Earth Web View.
    *   **Data Table Pane:**
        *   Displays all polygon records from the database with details like ID, Status, UUID, Farmer Name, Village, etc.
        *   Supports selection of multiple rows using checkboxes.
        *   "Select/Deselect All" checkbox for bulk actions.
    *   **Filter Panel:** Allows filtering of the data table by UUID, date added, KML export status, and record error status.
    *   **Log Panel:** Shows status messages, errors, and logs of application activity.
*   **Startup Sequence:**
    *   **`launcher_app.py`**: Main application entry point. Manages application setup, styling, and initiates the loading sequence.
    *   **`ui/loading_screen_widget.py`**: Provides an initial UI with progress indication and logs during application startup. Ensures a responsive user experience while core components are initialized in a background thread.
*   **Dialogs:**
    *   **API Sources Dialog:** Manage mWater API source URLs.
    *   **Duplicate Dialog:** Handle duplicate record imports.
    *   **Output Mode Dialog:** Choose between single or multiple KML file generation.
    *   **Instruction Popup:** Provides manual steps for Google Earth KML import.

## Key v5 Architectural Changes

The ongoing update to Version 5 introduces significant architectural improvements:

*   **KML-First Data Model:** The application now employs a KML-first approach. When data is imported (via API or CSV), a KML file is immediately generated and stored persistently for each valid record. This KML file becomes the primary source of truth for the geographic data and its description. The SQLite database primarily stores metadata, including a reference to the KML filename (`kml_file_name`), its status (`kml_file_status` e.g., "Created", "Edited", "Errored"), edit history (`edit_count`, `last_edit_date`), and information about the device that created/edited the record (`device_code`, `editor_device_id`, `editor_device_nickname`).

*   **User-Defined Configuration (`CredentialManager`):**
    *   A new `CredentialManager` component manages application configuration, which is set by the user on the first run:
        *   **Device Nickname:** A user-chosen nickname for the device.
        *   **Application Mode:** Choice between "Central App" or "Connected App" (to support future shared data access over LAN).
        *   **Data Paths:** User-defined paths for storing the main SQLite database file (e.g., `dilasa_main_data_v5.db`) and the root folder for KML files (e.g., `kml_files/`).
    *   This configuration is stored locally in a `device_config.db` file, typically located in a user-specific application data directory (path determined using the `platformdirs` library). This replaces previous hardcoded or fixed data storage locations.

## Key Technologies

*   **Language:** Python
*   **GUI:** PySide6 (Qt) - *Theming enhanced with Fusion style and `qtmodern` for a modern dark look.*
*   **Application Launcher & Startup:** `launcher_app.py` with `ui/loading_screen_widget.py` for threaded initialization.
*   **UI Styling:** `qtmodern` *(for modern themes and window frames)*, Custom QSS via `assets/style.qss`
*   **Database:** SQLite
*   **Path Management:** `platformdirs` (for user-specific configuration paths)
*   **Mapping & KML:** Folium, simplekml
*   **APIs:** mWater (for data import), Google Earth Engine (upcoming for historical imagery processing)

## Current Status

The application is undergoing a significant update to **Version 5 (v5)**. Key architectural changes, including a KML-first data model and user-defined configurations via `CredentialManager`, have been implemented. See 'Key v5 Architectural Changes' for more details. The UI has also been modernized with High DPI support and a new application launcher. Development continues on further v5 enhancements and Google Earth Engine integration.

## Setup

1.  Ensure Python (3.9+) is installed.
2.  Clone the repository.
3.  Create a virtual environment and activate it.
4.  Install dependencies: `pip install -r requirements.txt`
5.  Run: `python launcher_app.py`
6.  **First-Time Setup:** On the first launch, you will be guided through a setup process to configure your device nickname, application mode (Central/Connected), and specific paths for storing the main database and KML files.

## Project Documentation & Development Insights

For more detailed information on the project's v5 transition, architecture, and ongoing development tasks, please refer to the following documents:

*   **`v5_task_and_Concept.md`**: Provides a comprehensive overview of the v5 project plan, architectural changes, glossary of terms, and detailed task breakdowns.
*   **`Project_Logfile.md`**: Contains a log of development progress, detailing the changes and objectives for each completed task.

These documents offer deeper insights into the development process and the evolution of the application.
