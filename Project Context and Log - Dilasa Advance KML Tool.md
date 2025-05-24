## **Artifact 7: Project Context and Log**

**Date:** May 24, 2025 (Based on last interaction context)

### **1\. Application Details:**

Project: Dilasa Advance KML Tool  
User Goal: To create a robust Windows desktop application for Dilasa Janvikash Pratishthan. The primary purpose is to process geographic data, initially from farmer field surveys (via CSV or mWater API), to generate KML polygon files for visualization and verification. A key recent requirement is to integrate historical satellite imagery to verify land use and farming continuity over several years for specific areas.  
Project Evolution & Shape:  
The project began as a request for a simple Tkinter-based Windows application to create KML square polygons from manually entered latitude/longitude points. It has progressively evolved through several stages:

* **Initial Phase (Tkinter \- Conceptual v1.x):** Basic KML generation from 4 Lat/Lon points and a name.  
* **CSV & UTM Input Upgrade (Tkinter \- Conceptual v2.x):** Introduced CSV file uploads, handling of UTM coordinates (requiring conversion), per-point altitude, options for single/multiple KML outputs, detailed KML descriptions, and specific KML styling (yellow outline, no fill).  
* **Advanced Tkinter & Early Qt Planning (Conceptual Beta v3.001.Dv-A.Das):** This version (still Tkinter in its final implementation stage before the Qt decision) focused on dynamic output modes, improved UI for data management, and introduced the idea of persistent storage (SQLite) for API URLs and polygon data. It also included deduplication logic and KML export tracking. The increasing complexity and desire for a more modern UI and advanced features (like mapping) led to the strategic decision to refactor the application using Qt.  
* **Shift to Qt (PySide6) & Modular Design (Current Phase \- Beta v4.001.Dv-A.Das):**  
  * The application's UI was completely rewritten using Qt (PySide6) for a more modern, capable, and maintainable interface.  
  * A modular project structure (ui/, core/, database/ packages) was adopted.  
  * Implemented a QMainWindow with a custom header, detachable QToolBar (with icon+text buttons), QMenuBar, and QStatusBar.  
  * A QTableView with a custom QAbstractTableModel and QSortFilterProxyModel now displays data from the SQLite database, offering advanced filtering (UUID, date added, export status, error status) and column sorting.  
  * Checkboxes were added to the table for bulk actions (delete, KML generation).  
  * Dialogs for API source management, duplicate handling, and KML output mode selection were created/ported to Qt, with improved centering and icon handling.  
  * A custom splash screen and application branding (icon, logo) were integrated.  
  * An embedded map viewport (QWebEngineView \+ folium) was added to display selected polygons (defaulting to Esri Satellite view).  
  * **Current Development Focus:** Implementing the "Historical Map Builder" feature. This involves:  
    * A new dialog (HistoricalMapBuilderDialog) for users to define areas of interest (via Shapefile upload), select years, and choose GEE processing parameters.  
    * A GEEProcessingThread for background interaction with Google Earth Engine (GEE) to fetch, composite, and prepare yearly satellite images for download.  
    * Local storage of these downloaded yearly images and their geographic bounds metadata.  
    * UI elements in the MainWindow (a checkable "Historical View" group box and a "Year" QComboBox) to enable viewing these cached historical images.  
    * Logic in MainWindow and MapViewWidget to display the selected local historical image as an overlay, with the specific farmer's polygon highlighted.

The application is evolving into a comprehensive geospatial data management and visualization tool, tailored to assist in verifying land use and farming continuity over time for specific operational areas.

### **2\. Application Road Map:**

* **a. Conceptual Tkinter Versions (Pre-Beta v4.x):**  
  * **Version Name/Number:** Beta v1.x \- "Simple KML Square Generator"  
    * **Added:** Manual Lat/Lon input, KML generation for single squares.  
    * **Removed/Changed:** N/A.  
    * **How it worked:** Basic Tkinter UI, simplekml for output.  
  * **Version Name/Number:** Beta v2.x \- "CSV-based KML Generator"  
    * **Added:** CSV import, list display of polygons, basic KML styling.  
    * **Removed/Changed:** Manual input became secondary.  
    * **How it worked:** User uploaded CSV, selected items, generated a single KML.  
  * **Version Name/Number:** Beta v3.001.Dv-A.Das (Advanced Tkinter, leading to Qt decision)  
    * **Added:** UTM/Altitude handling, detailed KML descriptions, specific styling, single/multiple KML output modes, API URL management (planned), persistent storage (planned), deduplication (planned), KML export tracking (planned).  
    * **Removed/Changed:** Simple styling, transient data model.  
    * **How it worked (as fully realized in Tkinter, then planned for Qt):** Data from CSV/API stored in SQLite, displayed with error states. Duplicates handled. User selected records and output mode. *The UI was Tkinter, but limitations prompted the Qt shift.*  
* **b. Qt Version (Current Development Track):**  
  * **Version Name/Number:** Beta v4.001.Dv-A.Das \- "Dilasa Advance KML Tool (Qt Edition)"  
    * **Added (So Far):**  
      * Complete UI rewrite from Tkinter to PySide6.  
      * Modular project structure (ui/, core/, database/).  
      * QMainWindow with custom header, detachable toolbar (icon+text), menus, status bar.  
      * SQLite database integration via DatabaseManager.  
      * QTableView with PolygonTableModel and QSortFilterProxyModel for advanced data display, filtering (UUID, date added, export status, error status), and sorting.  
      * Checkbox column and "Select/Deselect All" for bulk actions.  
      * Functional dialogs (API Sources, Duplicates, KML Output Mode) in Qt, centered, with app icon.  
      * Custom splash screen.  
      * CSV and mWater API data import fully functional with DB persistence and duplicate handling.  
      * KML generation (single/multiple) from checked table items, with DB export status updates.  
      * "Export Displayed Data as CSV" feature.  
      * "Clear All Data" and "Delete Checked Rows" with confirmation.  
      * Basic map viewport using QWebEngineView and folium to display a single selected polygon (defaulting to Esri Satellite).  
      * **Currently Integrating:** "Historical Map Builder" dialog UI and GEE processing thread (GEEProcessingThread in historical\_map\_builder\_dialog.py, gee\_handler.py in core/). UI elements for historical view (toggle, year combo) in MainWindow. Logic to display locally cached historical images in MapViewWidget.  
    * **Removed/Changed:** All Tkinter code.  
    * **How it works (Target):** A desktop application. Users manage API sources, import data from CSV or API. Data is stored persistently in SQLite, displayed in a feature-rich table. Users can filter/sort data, perform bulk operations. KMLs are generated for checked items with user-selected output mode. A map view shows selected polygons. The "Historical Map Builder" allows users to download yearly GEE imagery for defined areas (via Shapefile). The main map view can then overlay these cached historical images for selected polygons and years.

### **3\. Log File (Major Achievements & Milestones):**

* Initial Tkinter KML generator created.  
* CSV import and basic KML styling added.  
* Upgraded to handle UTM, altitude, detailed descriptions, specific KML styles.  
* Implemented single/multiple KML output modes.  
* **Decision to refactor to Qt and modular design.**  
* Created DatabaseManager for SQLite persistence.  
* Developed core modules for data processing, KML generation, API handling.  
* Implemented basic Qt MainWindow with splash screen, header, menus.  
* Integrated QTableView with custom models for data display from DB.  
* Ported dialogs (API, Duplicate, Output Mode) to Qt.  
* Achieved functional CSV and mWater API import with DB persistence and duplicate handling in Qt.  
* Implemented KML generation from Qt UI with DB export status tracking.  
* Added advanced table filtering and sorting.  
* Added table checkboxes and bulk actions (delete, KML export).  
* Integrated initial MapViewWidget with Folium for selected polygon display.  
* **Currently:** Implementing "Historical Map Builder" dialog, GEE interaction logic (gee\_handler.py), and integration for displaying cached historical imagery. API data import is now functional.

### **4\. Libraries Used Currently (Beta v4.x with Qt):**

* **PySide6**: (QtWidgets, QtGui, QtCore, QtWebEngineWidgets, QtWebEngineCore)  
* **sqlite3**: (Python built-in)  
* **requests**: For API calls.  
* **simplekml**: For KML generation.  
* **utm**: For UTM to Lat/Lon conversions.  
* **Pillow**: For image handling (logo).  
* **folium**: For generating Leaflet.js maps (HTML).  
* **geopandas**: For reading Shapefiles (Historical Map Builder).  
* **earthengine-api**: For Google Earth Engine interaction (Historical Map Builder).  
* Standard Python: os, sys, re, datetime, csv, io.StringIO, json, tempfile.

### **5\. Current Version Structure (DilasaKMLTool\_v4):**

DilasaKMLTool\_v4/  
├── main\_app.py  
├── ui/  
│   ├── \_\_init\_\_.py  
│   ├── main\_window.py  
│   ├── splash\_screen.py  
│   ├── dialogs/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── api\_sources\_dialog.py  
│   │   ├── duplicate\_dialog.py  
│   │   ├── output\_mode\_dialog.py  
│   │   └── historical\_map\_builder\_dialog.py   
│   └── widgets/  
│       ├── \_\_init\_\_.py  
│       └── map\_view\_widget.py  
├── core/  
│   ├── \_\_init\_\_.py  
│   ├── data\_processor.py  
│   ├── kml\_generator.py  
│   ├── api\_handler.py  
│   ├── gee\_handler.py   
│   └── utils.py  
├── database/  
│   ├── \_\_init\_\_.py  
│   └── db\_manager.py  
├── assets/  
│   ├── dilasa\_logo.jpg  
│   └── app\_icon.ico  
├── local\_historical\_imagery/   
│   └── (Placeholder for {AreaName}/{Year}.{format} and {Year}.json)  
├── .gitignore  
├── requirements.txt  
└── README.md

### **6\. Current Goal:**

* **Fully implement and integrate the "Historical Map Builder" and historical imagery viewing functionality.**  
  * **Builder Dialog (historical\_map\_builder\_dialog.py):**  
    * Ensure robust Shapefile reading and feature selection (using geopandas).  
    * Correctly pass area geometries and parameters to GEEProcessingThread.  
    * Ensure GEEProcessingThread correctly uses gee\_handler.py to:  
      * Fetch/composite yearly imagery from GEE for the selected areas and years.  
      * Obtain download URLs for the processed images.  
      * Crucially, obtain and save the **geographic bounds** of each downloaded image (e.g., as a sidecar .json file like 2023.json next to 2023.png).  
    * Implement the actual download of images from the GEE-provided URL to the local\_historical\_imagery/{AreaName}/{Year}/ directory.  
    * Provide clear progress updates and error handling in the dialog's log.  
  * **Main Window Integration (main\_window.py & map\_view\_widget.py):**  
    * Refine the logic in update\_historical\_year\_combo\_for\_selection() to:  
      * Reliably determine the "Area Name" (e.g., Block Name from polygon\_data.block) for the currently selected farmer's polygon. This name must match the folder names created by the builder.  
      * Scan the local cache (local\_historical\_imagery/{AreaName}/) for available YEAR.png (or .tif) files AND their corresponding YEAR.json (bounds) files. Only list years for which both image and bounds data exist.  
    * Refine on\_historical\_year\_selected():  
      * When a year is selected, construct paths to the local image and its bounds file.  
      * Load the geographic bounds from the .json file.  
      * Call self.map\_view\_widget.display\_local\_image\_overlay() with the image path, its loaded bounds, and the current farmer's polygon coordinates (converted to Lat/Lon).  
    * Ensure MapViewWidget.display\_local\_image\_overlay() correctly uses folium.raster\_layers.ImageOverlay with the provided image path and geographic bounds.

### **7\. Future Aspects and Possible Features:**

* Advanced Polygon Editor on the map.  
* More sophisticated historical imagery comparison tools (side-by-side, sliders).  
* User settings panel (default paths, GEE params, map prefs).  
* Reporting tools (PDF/HTML).  
* Batch KML processing without UI selection.  
* Improved error handling and user guidance throughout the application.  
* Refined installer/packager for Windows distribution.  
* Option to manage (delete, view info about) locally cached historical imagery.

### **8\. Self Prompt (Instructions for AI to Continue):**

* **Current Focus:** Complete the "Historical Map Builder" feature.  
* **Immediate Next Steps for Coding (Artifact 6 \- main\_window.py and map\_view\_widget.py updates):**  
  1. **Modify MapViewWidget (ui/widgets/map\_view\_widget.py):**  
     * Implement display\_local\_image\_overlay(self, image\_path, image\_bounds\_lat\_lon, farmer\_polygon\_coords\_lat\_lon=None, map\_center\_lat\_lon=None, zoom\_level=14). This method should:  
       * Take the path to a locally stored image and its geographic bounds (e.g., \[\[lat\_min, lon\_min\], \[lat\_max, lon\_max\]\]).  
       * Create a new Folium map centered appropriately.  
       * Use folium.raster\_layers.ImageOverlay to display the local image using its path (converted to file:/// URL) and bounds.  
       * If farmer\_polygon\_coords\_lat\_lon are provided, draw this polygon on top of the image overlay (e.g., in a contrasting color).  
       * Include standard base map tile layers (OpenStreetMap, Esri Satellite) in the LayerControl for reference.  
  2. **Update MainWindow (ui/main\_window.py):**  
     * **\_create\_menus\_and\_toolbar():** Ensure the "Build Historical Imagery Cache..." action is present and connected to handle\_build\_historical\_maps().  
     * **\_setup\_main\_content\_area():** Ensure the "Historical View" QGroupBox and "Year" QComboBox are correctly added and laid out.  
     * **handle\_build\_historical\_maps():** Implement this to create and exec() an instance of HistoricalMapBuilderDialog(self).  
     * **on\_historical\_view\_toggled(self, checked):** Implement fully.  
     * **update\_historical\_year\_combo\_for\_selection(self):**  
       * **Crucial:** Add robust logic to get the area\_name\_for\_cache based on the selected polygon\_record (e.g., from its block field, sanitized to match folder names created by the builder).  
       * Scan local\_historical\_imagery/{area\_name\_for\_cache}/ for YEAR.png (or other supported image types) AND corresponding YEAR.json files. Only list years if both exist.  
     * **on\_historical\_year\_selected(self, selected\_year\_str):**  
       * Construct paths to the image and its .json bounds file.  
       * Load bounds from JSON. **Ensure the bounds format saved by the builder matches what folium.ImageOverlay expects (\[\[south\_lat, west\_lon\], \[north\_lat, east\_lon\]\]).** If GEE exports bounds differently (e.g., \[xmin, ymin, xmax, ymax\]), a conversion will be needed here or when saving the JSON.  
       * Convert the current farmer's polygon UTM coordinates to Lat/Lon.  
       * Call self.map\_view\_widget.display\_local\_image\_overlay(...).  
     * **historical\_imagery\_cache\_updated(self):** Implement to refresh the year combo.  
     * **on\_table\_selection\_changed():** Ensure it correctly calls update\_historical\_year\_combo\_for\_selection() or \_display\_current\_selected\_polygon\_on\_map() based on the historical view toggle.  
* **Data Flow for Bounds:** The GEEProcessingThread in historical\_map\_builder\_dialog.py must emit the geographic bounds of the processed GEE image. The dialog's handle\_image\_download\_signal must save these bounds (e.g., as a JSON file like 2023.json) alongside the downloaded image. MainWindow then reads this JSON to get bounds for ImageOverlay.  
* **Error Handling:** Add try-except blocks for file operations (reading bounds JSON, checking image paths) and GEE interactions.  
* **Testing:** After coding, the primary test will be:  
  1. Use the builder to download imagery for a known area/year.  
  2. Select a polygon in MainWindow that falls within that area.  
  3. Enable "Historical View."  
  4. Select the downloaded year.  
  5. Verify the correct local image is displayed as an overlay with the farmer's polygon on top.