# File: main_app.py (Refactored for threading)
# ----------------------------------------------------------------------
import sys
import os
from PySide6.QtCore import Qt # Kept as it's a common import
from ui.main_window import MainWindow
from core.utils import resource_path

def perform_non_gui_initialization():
    """
    Performs non-GUI initialization tasks that can safely run in a background thread.
    This could include loading configurations, checking resources, initializing backend services, etc.
    Returns True on success, False on failure (or raises an exception).
    For now, this is a placeholder.
    """
    # Example: print("Performing non-GUI tasks...")
    # import time # Add if time.sleep is used
    # time.sleep(1) # Simulate work
    # print("Non-GUI tasks complete.")
    return True # Or some status object

def create_main_window_instance():
    """
    Instantiates and returns the MainWindow.
    This function MUST be called from the main GUI thread.
    Any necessary environment setup immediately prior to instantiation can go here.
    """
    # Set environment variable for QtWebEngine
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing"
    main_window = MainWindow()
    return main_window

# The 'if __name__ == "__main__":' block is removed as launcher_app.py is the entry point.
