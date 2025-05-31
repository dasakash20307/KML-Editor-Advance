# File: launcher_app.py (Modified)
# ----------------------------------------------------------------------
import sys
import os
import platform
import time # For demonstration of progress

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QThread, Signal

# Assuming qtmodern is still used for the main window
import qtmodern.styles
import qtmodern.windows

if platform.system() == "Windows":
    import ctypes

# Updated import from main_app
# from main_app import prepare_main_window # Old import
from main_app import perform_non_gui_initialization, create_main_window_instance # New imports
# Import the new loading screen widget
from ui.loading_screen_widget import LoadingScreenWidget
from ui.first_run_setup_dialogs import NicknameDialog, ModeSelectionDialog, PathConfigurationDialog
from core.credential_manager import CredentialManager
from core.utils import resource_path # For QSS path
from PySide6.QtWidgets import QApplication, QMessageBox # Added QMessageBox

# Define constants for loading screen - these could be moved to a config file or core module
APP_NAME_LAUNCHER = "Dilasa Advance KML Tool"
COMPANY_NAME_LAUNCHER = "Dilasa Janvikash Pratishthan"
TAGLINE_LAUNCHER = "Empowering communities with geospatial solutions"
# Version will be taken from app.applicationVersion()
DEVELOPER_NAME_LAUNCHER = "A.Das"
SUPPORT_EMAIL_LAUNCHER = "support@dilasa.org" # Or your actual support email

class InitializationThread(QThread):
    # Signals: progress_value, status_text
    progress_updated = Signal(int, str)
    # Signals: message, level (e.g., "INFO", "ERROR")
    log_message = Signal(str, str)
    # Signal: success_status, data_from_non_gui_init (can be None or a dict/object)
    initialization_complete = Signal(bool, object)

    def run(self):
        try:
            self.log_message.emit("Starting application initialization...", "INFO")
            self.progress_updated.emit(10, "Initializing core components...")
            time.sleep(0.2) # Simulate some work

            self.log_message.emit("Performing non-GUI setup...", "INFO")
            self.progress_updated.emit(30, "Loading configurations & core services...")

            init_result = perform_non_gui_initialization() # from main_app.py
            success_non_gui = init_result.get("success", False)
            status_non_gui = init_result.get("status")

            if status_non_gui == "CORRUPT_CONFIG":
                error_msg = init_result.get("error", "Configuration is corrupted or incomplete.")
                config_path = init_result.get("config_path", "Unknown location")
                self.log_message.emit(f"Config Issue: {error_msg} (File: {config_path})", "ERROR")
                self.log_message.emit("Attempting to re-run setup...", "INFO")
                self.progress_updated.emit(75, "Configuration issue detected...") # Indicate something is happening
                # Signal that thread completed its check, but main init failed in a specific way
                self.initialization_complete.emit(True, init_result) # Pass init_result
                return # Important: exit thread run method here

            if not success_non_gui: # Handles other errors like true first_run from main_app, or DB connection issues
                error_msg = init_result.get("error", "Unknown non-GUI initialization failure.")
                detailed_error = init_result.get("detailed_error") # Keep this if detailed_error is part of init_result for other errors
                # Log messages are already printed by perform_non_gui_initialization,
                # but we can add a summary here for the launcher log.
                self.log_message.emit(f"Non-GUI Initialization Summary: {error_msg}", "ERROR")
                if detailed_error: # Check if detailed_error exists for this error type
                     # This might be too verbose for loading screen log, better for console/file log
                     # self.log_message.emit(f"Detailed Error (Non-GUI): {detailed_error}", "DEBUG")
                     pass
                raise RuntimeError(f"Non-GUI init failed: {error_msg}") # This will be caught by the outer except

            # If successful, init_result contains db_manager and credential_manager
            self.log_message.emit("Non-GUI initialization successful.", "SUCCESS")
            self.progress_updated.emit(70, "Ready to create main window...")
            time.sleep(0.2)

            self.progress_updated.emit(100, "Initialization tasks complete!") # Thread tasks are done
            self.initialization_complete.emit(True, init_result) # Pass the dictionary

        except Exception as e:
            e_str = str(e) # Capture string representation of original error first

            # Prepare the main error message
            error_message_main = f"Initialization thread failed: {e_str}"

            # Attempt to log this main failure.
            try:
                self.log_message.emit(error_message_main, "ERROR")
            except Exception as log_emit_ex:
                # Fallback to print if emitting to UI log fails
                print(f"CRITICAL LAUNCHER ERROR: Failed to emit primary error to UI log. UI Log emitter error: {log_emit_ex}")
                print(f"Original error in thread was: {e_str}")

            # Optionally, log detailed traceback to console (not to UI log to avoid clutter / further errors)
            # This was previously commented out but is useful for debugging.
            # We are not emitting this detailed_error to self.log_message to avoid recursion
            # if the error 'e' itself was related to self.log_message.
            try:
                import traceback
                detailed_traceback_str = traceback.format_exc()
                print(f"LAUNCHER THREAD TRACEBACK:\n{detailed_traceback_str}")
            except Exception:
                print("LAUNCHER THREAD: Failed to get detailed traceback.")

            # Update progress and signal completion with the original error
            try:
                self.progress_updated.emit(0, "Error during startup!")
            except Exception as progress_emit_ex:
                print(f"CRITICAL LAUNCHER ERROR: Failed to emit progress update in thread's except block: {progress_emit_ex}")

            try:
                self.initialization_complete.emit(False, e) # Emit original exception 'e'
            except Exception as complete_emit_ex:
                print(f"CRITICAL LAUNCHER ERROR: Failed to emit initialization_complete in thread's except block: {complete_emit_ex}")


# Global reference to keep ModernWindow alive if needed, or manage within launch
_main_modern_window = None

def launch():
    global _main_modern_window # To keep ModernWindow instance alive

    # --- Early settings (before QApplication instantiation) ---
    if platform.system() == "Windows":
        try:
            # ctypes.windll.uxtheme.SetPreferredAppMode(2) # 2 = Dark # Commented out for Phase 1 Theming
            pass # Keep the try-except structure in case it's re-enabled later
        except Exception as e:
            print(f"Warning (launcher_app): Could not set Windows dark mode: {e}")

    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) # Removed: Deprecated in Qt6, HighDPI is on by default

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME_LAUNCHER)
    app.setApplicationVersion("Beta.v5.0.1.Dev-ADas") # Updated version for v5

    # --- Post-QApplication instantiation settings ---
    app.setStyle('Fusion')
    # qtmodern.styles.dark(app) # Apply qtmodern dark style first # Commented out for Phase 1 Theming

    # Load global QSS stylesheet
    try:
        qss_path = resource_path("style.qss") # Corrected: removed "assets" argument
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                stylesheet = f.read()
            # Append to existing stylesheet (e.g., from qtmodern)
            current_stylesheet = app.styleSheet()
            app.setStyleSheet(current_stylesheet + "\n" + stylesheet)
            print(f"Successfully loaded and appended global stylesheet from {qss_path}")
        else:
            print(f"Warning (launcher_app): Global stylesheet 'assets/style.qss' not found at '{qss_path}'. Skipping.")
    except Exception as e:
        print(f"Warning (launcher_app): Error loading global stylesheet: {e}")

    # --- Create and Show Loading Screen ---
    loading_screen = LoadingScreenWidget(
        app_name=app.applicationName(),
        company_name=COMPANY_NAME_LAUNCHER,
        tagline=TAGLINE_LAUNCHER,
        version_code=app.applicationVersion(),
        developer_name=DEVELOPER_NAME_LAUNCHER,
        support_email=SUPPORT_EMAIL_LAUNCHER
    )
    loading_screen.center_on_screen()
    loading_screen.show()
    QApplication.processEvents() # Ensure loading screen is displayed before thread starts

    # --- Setup and Start Initialization Thread ---
    thread = InitializationThread()

    # Connect signals from thread to loading screen slots
    thread.progress_updated.connect(loading_screen.update_progress)
    thread.log_message.connect(loading_screen.append_log)

    def _execute_first_run_setup_flow(current_loading_screen, cm_instance: CredentialManager):
        current_loading_screen.append_log("Starting first-time setup / configuration recovery...", "INFO")
        QApplication.processEvents()

        nickname_dialog = NicknameDialog(parent=current_loading_screen) # Parent to loading screen
        if not nickname_dialog.exec():
            current_loading_screen.append_log("Setup aborted by user at Nickname selection.", "WARNING")
            return False
        nickname = nickname_dialog.get_nickname()

        mode_dialog = ModeSelectionDialog(parent=current_loading_screen)
        if not mode_dialog.exec():
            current_loading_screen.append_log("Setup aborted by user at Mode selection.", "WARNING")
            return False
        app_mode = mode_dialog.get_app_mode()

        path_dialog = PathConfigurationDialog(app_mode=app_mode, parent=current_loading_screen)
        if not path_dialog.exec():
            current_loading_screen.append_log("Setup aborted by user at Path configuration.", "WARNING")
            return False
        db_path, kml_path = path_dialog.get_paths()

        try:
            cm_instance.save_settings(nickname, app_mode, db_path, kml_path)
            current_loading_screen.append_log(f"Configuration saved. Device ID: {cm_instance.get_device_id()}", "SUCCESS")
            current_loading_screen.append_log("Please restart the application for changes to take full effect.", "INFO")
            # Update progress to indicate setup is done.
            current_loading_screen.update_progress(100, "Setup Complete. Please Restart.")
            QMessageBox.information(current_loading_screen, "Setup Complete", "Initial configuration is complete. Please restart the application.")
            QApplication.instance().quit() # Add this line to exit
            return True # Though the quit() might make this return not strictly necessary for flow.
        except Exception as e_save:
            error_msg_save = f"Failed to save settings: {e_save}"
            current_loading_screen.append_log(error_msg_save, "ERROR")
            QMessageBox.critical(current_loading_screen, "Setup Error", error_msg_save)
            return False

    # --- Handle Initialization Completion ---
    def handle_initialization_finished(success_thread, data_from_thread):
        global _main_modern_window

        if not success_thread: # Thread itself crashed
            loading_screen.append_log(f"Startup aborted due to thread crash: {str(data_from_thread)}", "ERROR")
            loading_screen.update_progress(0, "Critical Startup Failed!")
            print(f"Critical error from thread (exception object): {data_from_thread}")
            return # Keep loading screen open

        # If thread didn't crash, data_from_thread is init_result dict
        init_data = data_from_thread
        actual_init_success = init_data.get("success", False)
        status_from_init = init_data.get("status")
        credential_manager_instance = init_data.get("credential_manager")

        if status_from_init == "CORRUPT_CONFIG":
            loading_screen.append_log(f"Config Error: {init_data.get('error', 'Corrupted configuration.')}", "ERROR")
            loading_screen.append_log(f"Config file: {init_data.get('config_path', 'N/A')}", "INFO")
            loading_screen.append_log("Initiating setup process...", "INFO")
            QApplication.processEvents()

            if credential_manager_instance:
                # Pass the loading_screen and the credential_manager instance
                setup_completed = _execute_first_run_setup_flow(loading_screen, credential_manager_instance)
                if setup_completed:
                    # Message to restart is shown by _execute_first_run_setup_flow
                    # Loading screen can be kept open with the restart message.
                    pass
                else:
                    loading_screen.append_log("Setup process was not completed. Application cannot continue.", "ERROR")
                    loading_screen.update_progress(0, "Setup Incomplete.")
            else:
                loading_screen.append_log("Cannot re-run setup: CredentialManager instance not available.", "CRITICAL")
                loading_screen.update_progress(0, "Internal Error.")
            return # Halt further normal startup flow

        # Handle other cases (true first run that wasn't caught by launcher, other non-GUI errors)
        if not actual_init_success:
            error_msg = init_data.get("error", "Unknown non-GUI initialization failure.")
            loading_screen.append_log(f"Startup aborted: {error_msg}", "ERROR")
            loading_screen.update_progress(0, "Startup Failed!")
            print(f"Non-GUI initialization failed (error from init_data): {error_msg}")
            return # Keep loading screen open

        # Proceed with normal MainWindow creation if everything was successful
        # (Inside handle_initialization_finished, after CORRUPT_CONFIG and other initial error checks)
        # This means actual_init_success was True from perform_non_gui_initialization

        db_manager = init_data.get("db_manager")
        # Credential_manager already fetched: credential_manager_instance

        if not db_manager or not credential_manager_instance:
            error_msg = "Critical components (DBManager or CredentialManager) instance not found after non-GUI init."
            loading_screen.append_log(error_msg, "CRITICAL")
            loading_screen.update_progress(0, "Internal Error!")
            return

        # --- Attempt to connect the DatabaseManager on the main thread ---
        loading_screen.append_log("Connecting to the main database...", "INFO")
        # You might want a different progress step, e.g., 80, if 70 was "Ready to create main window"
        # and 85 is "Creating user interface"
        loading_screen.update_progress(80, "Connecting database...")
        QApplication.processEvents()

        if not db_manager.connect(): # Call connect() here
            # DatabaseManager.connect() should print its own detailed errors to console.
            # Here, we update the UI.
            db_conn_error_msg = f"Failed to connect to or initialize the main database. Check console logs for details."
            loading_screen.append_log(db_conn_error_msg, "CRITICAL")
            loading_screen.update_progress(0, "DB Setup Failed!")
            # Ensure loading_screen stays open with the error.
            return # Halt further execution

        loading_screen.append_log("Database connected and schema verified successfully.", "SUCCESS")
        # Now proceed to create the main window, db_manager is connected.
        # ---- End of new DB connection block ----

        loading_screen.update_progress(85, "Creating user interface...")
        QApplication.processEvents()
        try:
            # Step 2: Create MainWindow instance in the main thread
            main_window_instance = create_main_window_instance(
                db_manager=db_manager,
                credential_manager=credential_manager_instance # Use the fetched instance
            ) # from main_app.py

            if not main_window_instance:
                # This should ideally not happen if create_main_window_instance is robust
                raise RuntimeError("Failed to create MainWindow instance (returned None).")

            loading_screen.append_log("Main window created successfully.", "SUCCESS")
            loading_screen.update_progress(95, "Finalizing UI...")
            QApplication.processEvents()

            # Close loading screen before showing main window to avoid overlap/flicker
            loading_screen.close()

            _main_modern_window = qtmodern.windows.ModernWindow(main_window_instance)
            _main_modern_window.show()

        except Exception as e:
            # Handle errors during main window creation or display
            error_message = f"Failed to create or show main window: {str(e)}"
            import traceback
            detailed_error = traceback.format_exc()
            loading_screen.append_log(error_message, "ERROR")
            loading_screen.append_log(f"Details: {detailed_error}", "DEBUG")
            loading_screen.update_progress(0, "UI Creation Failed!")
            # Keep loading_screen open to show the error

    thread.initialization_complete.connect(handle_initialization_finished)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
