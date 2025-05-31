import os
import sys

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This function is crucial for finding assets (like images, icons)
    when the application is bundled by PyInstaller.
    """
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    # For development, use the directory of the script that calls this function.
    # If utils.py is in core/, and assets are in ../assets/ relative to core/
    # then the project root is one level up from core.
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))
    
    # Assets are expected to be in an 'assets' subdirectory of the project root
    return os.path.join(base_path, "assets", relative_path)
