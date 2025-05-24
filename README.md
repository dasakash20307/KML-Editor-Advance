# Dilasa Advance KML Tool (Version: Beta.v4.001.Dv-A.Das)

## 1. Project Overview

The **Dilasa Advance KML Tool** is a Windows desktop application developed for **Dilasa Janvikash Pratishthan**. Its primary purpose is to streamline the management, processing, and verification of farmer field data, ultimately aiding in community development and agricultural support programs.

The tool enables users to:
*   Import geospatial data from various sources (CSV files, mWater API).
*   Manage and store this data persistently in a local SQLite database.
*   Process and validate coordinate data, including UTM to Latitude/Longitude conversions.
*   Generate KML (Keyhole Markup Language) polygon files from the data for visualization in GIS software like Google Earth.
*   View selected farmer polygons on an integrated map display.
*   **(Upcoming Feature)** Integrate and visualize historical satellite imagery (from Google Earth Engine) to verify land use patterns and farming continuity over time for specific areas.

This application has evolved from a basic KML generator into a more comprehensive geospatial data utility, tailored to the specific operational needs of Dilasa.

## 2. Core Functionalities

*   **Data Import:**
    *   **CSV Import:** Upload CSV files containing farmer and plot details, including UTM coordinates for plot boundaries.
    *   **mWater API Integration:** Fetch data directly from configured mWater API endpoints.
    *   **Data Validation & Processing:** Incoming data is processed to parse coordinates, handle missing points (with substitution logic), and check for data integrity.
*   **Database Management:**
    *   All imported and processed data is stored in a local SQLite database.
    *   Supports management of mWater API source URLs.
    *   Handles duplicate record detection based on a "Response Code."
*   **Data Display and Filtering:**
    *   A feature-rich table displays all polygon records from the database.
    *   Advanced filtering capabilities: by UUID, date added, KML export status, and record error status.
    *   Column sorting and selection via checkboxes for bulk operations.
*   **KML Generation:**
    *   Generate KML files for selected valid polygon records.
    *   Supports outputting a single consolidated KML file or multiple individual KML files (named by UUID).
    *   KML polygons are styled with a yellow outline and no fill, including detailed descriptions derived from farmer data.
    *   Tracks KML export count and last export date for each record.
*   **Map Visualization:**
    *   An integrated map view (using Folium and QtWebEngine) displays the geometry of the currently selected valid farmer polygon.
    *   Default base map is Esri Satellite, with options for OpenStreetMap and others.
*   **User Interface:**
    *   Modern, intuitive GUI built with Qt (PySide6).
    *   Includes a custom application header, toolbar, menu bar, and status bar.
    *   Custom splash screen for application startup.

## 3. Technology Stack

*   **Programming Language:** Python 3.11+
*   **GUI Framework:** PySide6 (Qt6)
*   **Database:** SQLite (via Python's `sqlite3` module)
*   **Key Python Libraries:**
    *   `requests`: For HTTP API calls.
    *   `simplekml`: For KML file generation.
    *   `utm`: For UTM to Latitude/Longitude coordinate conversions.
    *   `Pillow`: For image handling (e.g., logos).
    *   `folium`: For generating interactive Leaflet.js maps.
    *   *(Upcoming)* `geopandas`: For reading and processing Shapefiles.
    *   *(Upcoming)* `earthengine-api`: For interacting with Google Earth Engine.
*   **Development Environment:** Windows

## 4. Project Structure

The project follows a modular structure:

```DilasaKMLTool_v4/
├── main_app.py                 # Main application entry point & splash screen
├── ui/                         # User Interface package
│   ├── main_window.py          # Main application window logic
│   ├── splash_screen.py        # (Currently splash logic is in main_app.py, can be refactored)
│   ├── dialogs/                # Dialog windows (API sources, duplicates, etc.)
│   └── widgets/                # Custom UI widgets (e.g., MapViewWidget)
├── core/                       # Core application logic package
│   ├── data_processor.py       # Logic for processing CSV/API row data
│   ├── kml_generator.py        # Logic for creating KML files
│   ├── api_handler.py          # Logic for fetching data from mWater APIs
│   ├── utils.py                # Utility functions (e.g., resource_path)
│   └── (gee_handler.py)        # (To be added for GEE interactions)
├── database/                   # Database management package
│   └── db_manager.py           # SQLite database interaction logic
├── assets/                     # Static assets (images, icons)
│   ├── dilasa_logo.jpg
│   └── app_icon.ico
├── (local_historical_imagery/) # (To be added for storing GEE images)
├── .gitignore
├── requirements.txt            # Python package dependencies
└── README.md                   # This file
```

## 5. Setup and Installation

1.  **Prerequisites:**
    *   Python 3.11 or higher installed.
    *   Git (for cloning the repository).
2.  **Clone the Repository (if applicable):**
    ```bash
    git clone https://github.com/dasakash20307/KML-Editor-Advance.git
    cd DilasaKMLTool_v4
    ```
3.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Ensure Assets:**
    *   Place `dilasa_logo.jpg` and `app_icon.ico` into the `assets/` directory if not already present.
6.  **Run the Application:**
    ```bash
    python main_app.py
    ```

## 6. Current Development Focus: Historical Imagery Integration

The immediate next major feature under development is the "Historical Map Builder." This will allow users to:
1.  Define Areas of Interest (AOIs), potentially using administrative boundary Shapefiles.
2.  Use Google Earth Engine (GEE) to fetch and process historical satellite imagery (e.g., yearly median composites of Sentinel-2 or Landsat data) for these AOIs.
3.  Download and cache these processed images and their geographic bounds locally.
4.  View these cached historical images within the application's map view, overlaid with specific farmer polygons, to aid in land use verification over time.

This feature will involve creating new modules for GEE interaction (`core/gee_handler.py`) and a new dialog for managing the historical imagery building process (`ui/dialogs/historical_map_builder_dialog.py`).

## 7. Contribution & Feedback

This tool is being actively developed. For bugs, feature requests, or contributions:
*   Please refer to the project's issue tracker on GitHub (if public).
*   Direct feedback can be provided to the development team at Dilasa Janvikash Pratishthan.

---

This README aims to provide a clear understanding of the Dilasa Advance KML Tool, its purpose, functionalities, and current development direction.
