import os
import sys

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    This function is crucial for finding assets (like images, icons)
    when the application is bundled by PyInstaller.
    """
    # Determine the base path.
    # If running in a PyInstaller bundle, _MEIPASS will be set.
    # Otherwise, determine path for development environment.
    default_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    base_path = getattr(sys, '_MEIPASS', default_base_path)
    
    # Assets are expected to be in an 'assets' subdirectory of the base_path.
    # relative_path is the name of the file within that 'assets' directory.
    return os.path.join(base_path, "assets", relative_path)
