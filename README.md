# Dilasa Advance KML Tool v4

## Description
Application for processing geographic data from mWater/CSVs, managing polygon records, generating KML files, and visualizing selected polygons. Built with Python and Qt (PySide6).

## Project Structure
(A brief overview of the main directories: ui/, core/, database/, assets/)

## Setup Instructions
1.  Ensure Python 3.8+ is installed.
2.  Clone this repository (if applicable) or extract the project files.
3.  Navigate to the project root directory (DilasaKMLTool_v4).
4.  **Create and activate a virtual environment (recommended):**
    `ash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    `
5.  **Install dependencies:**
    `ash
    pip install -r requirements.txt
    `
6.  Place dilasa_logo.jpg and pp_icon.ico into the ssets/ directory.
7.  **Run the application:**
    `ash
    python main_app.py
    `

## Building Executable (using PyInstaller)
(Instructions to be added once the application is developed, e.g.,)
\\\ash
pyinstaller --noconfirm --onefile --windowed --icon=assets/app_icon.ico --name "DilasaKMLTool" --add-data "assets/dilasa_logo.jpg:assets" main_app.py
\\\
This command might need adjustments based on how assets are handled (e.g., using Qt Resource system vs. direct file access with esource_path).