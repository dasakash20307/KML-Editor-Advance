# File: launcher_app.py
# ----------------------------------------------------------------------
import sys
import os
import platform  # For OS detection

# PySide6 imports will be added as needed
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

import qtmodern.styles # ADD THIS
import qtmodern.windows # ADD THIS

# ctypes import for Windows dark mode
# This import is fine here, it's conditional.
if platform.system() == "Windows":
    import ctypes

# Import from main_app
from main_app import create_and_show_main_window # ADD THIS
from core.utils import resource_path # ADD THIS

def launch():
    # --- Early settings (before QApplication instantiation) ---

    # 2. Windows Dark Mode Awareness (Conditional)
    if platform.system() == "Windows":
        try:
            # Force dark mode for Windows 10/11 title bars
            # 2 = Dark, 1 = Light, 0 = System default
            # This needs to be called before QApplication is instantiated or high DPI scaling is set.
            ctypes.windll.uxtheme.SetPreferredAppMode(2)
        except AttributeError:
            # This might fail on older Windows versions or if uxtheme isn't available
            print("Warning: Could not set Windows dark mode preference. May be an older Windows version.")
        except Exception as e:
            print(f"Warning: An unexpected error occurred while setting Windows dark mode: {e}")

    # 1. High DPI Scaling (Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Dilasa Advance KML Tool") # Set App Name
    app.setApplicationVersion("Beta.v5.000") # Set App Version for v5

    # --- Post-QApplication instantiation settings ---

    # 3. Set Application Style (Fusion)
    app.setStyle('Fusion')
    qtmodern.styles.dark(app) # ADD THIS - Apply qtmodern dark style

    # 4. qtmodern styling (e.g., qtmodern.styles.dark(app))
    # This is done above now. Placeholder comment can be removed or updated.
    # No, this was step 4, now done.

    # 5. Load global QSS stylesheet (assets/style.qss)
    try:
        qss_file_name = "style.qss"
        qss_folder = "assets"
        # Construct the path using resource_path from core.utils
        qss_path = resource_path(qss_file_name, qss_folder)

        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                stylesheet = f.read()

            # Append new stylesheet to any existing stylesheet (e.g., from qtmodern)
            current_stylesheet = app.styleSheet()
            app.setStyleSheet(current_stylesheet + "\n" + stylesheet)
            print(f"Successfully loaded and appended global stylesheet from {qss_path}")
        else:
            # This path is for user understanding, might not be the true base_path if bundled
            user_friendly_path = os.path.join(qss_folder, qss_file_name)
            print(f"Warning: Global stylesheet '{user_friendly_path}' not found resolved to '{qss_path}'. Skipping.")

    except Exception as e:
        # General exception catch for any other issues during file loading or processing
        print(f"Warning: Error loading global stylesheet 'assets/style.qss': {e}")

    # --- Launch main application ---
    main_window_instance = create_and_show_main_window() # Call the refactored function

    if main_window_instance:
        mw = qtmodern.windows.ModernWindow(main_window_instance)
        mw.show()
    else:
        print("Error: Main window instance was not created.")
        sys.exit(1) # Exit if main window creation failed

    sys.exit(app.exec())

if __name__ == "__main__":
    launch()
