# File: main_app.py (Refactored)
# ----------------------------------------------------------------------
import sys
import os

from PySide6.QtCore import Qt # Kept as it's a common import

from ui.main_window import MainWindow
# resource_path might still be needed by MainWindow or its components, so we keep the import
from core.utils import resource_path

# Renamed function, simplified to only create and return the main window instance
def prepare_main_window():
    """
    Prepares and returns an instance of the MainWindow.
    This function is intended to be called during the application startup sequence,
    typically by a background thread managed by the launcher.
    It configures necessary environment settings and instantiates the main window.
    Any long-running initialization specific to MainWindow should ideally be
    handled within MainWindow.__init__ or methods called from there, potentially
    emitting signals for progress updates.
    """
    # Set environment variable for QtWebEngine
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing"

    # Create the main window instance
    main_window = MainWindow()

    return main_window

# The 'if __name__ == "__main__":' block is removed as launcher_app.py is the entry point.
