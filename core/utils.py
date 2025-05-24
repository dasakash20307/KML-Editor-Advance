import os
import sys

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This function is crucial for finding assets (like images, icons)
    when the application is bundled by PyInstaller.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:  # Catch AttributeError specifically for _MEIPASS
        # For development, determine the project root.
        # Assuming utils.py is in 'core/', and project root is one level up.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    
    # Assets are expected to be in an 'assets' subdirectory of the base_path.
    # relative_path is the name of the file within that 'assets' directory.
    return os.path.join(base_path, "assets", relative_path)
