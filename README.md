# Dilasa Advance KML Tool

## Overview

The **Dilasa Advance KML Tool** is a Windows desktop application developed for Dilasa Janvikash Pratishthan. It's designed to simplify the management of farmer field data, facilitate KML polygon generation, and integrate with Google Earth for enhanced data visualization and verification.

## Core Features

*   **Data Management:**
    *   Import farmer and plot data via CSV files or directly from mWater APIs.
    *   Store and manage data in a local SQLite database.
*   **KML Generation:**
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

## Key Technologies

*   **Language:** Python
*   **GUI:** PySide6 (Qt) - *Theming enhanced with Fusion style and `qtmodern` for a modern dark look.*
*   **Application Launcher & Startup:** `launcher_app.py` with `ui/loading_screen_widget.py` for threaded initialization.
*   **UI Styling:** `qtmodern` *(for modern themes and window frames)*, Custom QSS via `assets/style.qss`
*   **Database:** SQLite
*   **Mapping & KML:** Folium, simplekml
*   **APIs:** mWater (for data import), Google Earth Engine (upcoming for historical imagery processing)

## Current Status

The application is undergoing a significant update to **Version 5 (v5)**.
This includes a modernized UI with High DPI support, a new application launcher, and foundational styling improvements (Fusion, qtmodern dark theme).
The core data management, KML generation, and manual Google Earth KML import features from v4 remain functional. Development is actively focused on integrating Google Earth Engine for advanced historical imagery analysis and further v5 enhancements.

## Setup

1.  Ensure Python (3.9+) is installed.
2.  Clone the repository.
3.  Create a virtual environment and activate it.
4.  Install dependencies: `pip install -r requirements.txt`
5.  Run: `python launcher_app.py`

## Project Documentation & Development Insights

For more detailed information on the project's v5 transition, architecture, and ongoing development tasks, please refer to the following documents:

*   **`v5_task_and_Concept.md`**: Provides a comprehensive overview of the v5 project plan, architectural changes, glossary of terms, and detailed task breakdowns.
*   **`Project_Logfile.md`**: Contains a log of development progress, detailing the changes and objectives for each completed task.

These documents offer deeper insights into the development process and the evolution of the application.
