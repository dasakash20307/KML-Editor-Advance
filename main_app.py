# File: main_app.py (Refactored for threading)
# ----------------------------------------------------------------------
VERSION = "5.1.2"

import sys
import os
from PySide6.QtCore import Qt # Kept as it's a common import
from ui.main_window import MainWindow
from core.utils import resource_path
from core.credential_manager import CredentialManager
from database.db_manager import DatabaseManager

def perform_non_gui_initialization():
    """
    Performs non-GUI initialization tasks.
    Initializes CredentialManager and DatabaseManager.
    Returns a dictionary with 'success': bool and 'db_manager': instance or 'error': str.
    """
    try:
        print("MainApp: Performing non-GUI initialization...") # For console logging
        credential_manager = CredentialManager()

        if credential_manager.is_first_run():
            # This state should ideally be caught by the launcher before calling this.
            # The launcher is responsible for running the first-time setup dialogs.
            # If we reach here and it's still a first run, it means setup wasn't completed.
            error_msg = "First-run setup not completed. Please restart and complete the setup."
            print(f"MainApp ERROR: {error_msg}")
            return {"success": False, "error": error_msg, "db_manager": None, "credential_manager": credential_manager}

        db_path = credential_manager.get_db_path()
        if not db_path: # This implies not first_run but essential path is missing
            error_msg = "Critical setting (Database path) not found in configuration. The configuration may be incomplete or corrupted."
            config_file_location = credential_manager.get_config_file_path()
            detailed_error_msg = f"{error_msg} Expected location: {config_file_location}"
            print(f"MainApp ERROR: {detailed_error_msg}")
            return {
                "success": False,
                "status": "CORRUPT_CONFIG", # New status flag
                "error": error_msg, # User-friendly error
                "config_path": config_file_location, # Path to config file
                "db_manager": None,
                "credential_manager": credential_manager # Pass credential_manager for re-setup
            }

        print(f"MainApp: Initializing DatabaseManager instance with path: {db_path}") # Message changed slightly
        db_manager = DatabaseManager(db_path=db_path)
        # The db_manager is now instantiated but not yet connected. Connection will be handled by launcher.

        print("MainApp: Non-GUI initialization successful (CredentialManager and DBManager instance created).") # Message changed slightly
        return {"success": True, "db_manager": db_manager, "credential_manager": credential_manager, "error": None}

    except Exception as e:
        import traceback
        detailed_error = traceback.format_exc()
        print(f"MainApp ERROR: Exception during non-GUI initialization: {e}\n{detailed_error}")
        return {"success": False, "error": str(e), "detailed_error": detailed_error, "db_manager": None, "credential_manager": None}

def create_main_window_instance(db_manager, credential_manager): # Added credential_manager
    """
    Instantiates and returns the MainWindow.
    Requires db_manager and credential_manager instances.
    """
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing"
    # MainWindow will need to be updated to accept credential_manager too
    main_window = MainWindow(db_manager=db_manager, credential_manager=credential_manager)
    return main_window

# The 'if __name__ == "__main__":' block is removed as launcher_app.py is the entry point.
