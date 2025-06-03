import os
import sys

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This function is crucial for finding assets and UI files
    when the application is bundled by PyInstaller.
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # For development, use the directory of the script that calls this function.
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    
    # Check if the path starts with 'assets/' or 'ui/'
    if relative_path.startswith(('assets/', 'ui/')):
        # Remove 'assets/' or 'ui/' prefix as base_path already points to project root
        relative_path = relative_path
    
    return os.path.normpath(os.path.join(base_path, relative_path))
