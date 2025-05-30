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
from core.utils import resource_path # For QSS path

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

            # Perform non-GUI tasks
            self.log_message.emit("Performing non-GUI setup...", "INFO")
            self.progress_updated.emit(30, "Loading configurations...")

            # Call the new non-GUI initialization function
            success_non_gui = perform_non_gui_initialization() # from main_app.py

            if not success_non_gui:
                # This assumes perform_non_gui_initialization returns False on failure
                # If it raises exceptions, this try-except block will catch them.
                raise RuntimeError("Non-GUI initialization failed.")

            time.sleep(0.3) # Simulate more work

            self.log_message.emit("Non-GUI initialization successful.", "SUCCESS")
            self.progress_updated.emit(70, "Ready to create main window...") # Adjusted progress
            time.sleep(0.2)

            # The actual MainWindow creation is now deferred to the main thread.
            # This thread's job for preparing MainWindow is done.
            self.progress_updated.emit(100, "Initialization tasks complete!") # Thread tasks are done
            self.initialization_complete.emit(True, None) # Emit success, no main_window instance here

        except Exception as e:
            error_message = f"Initialization thread failed: {str(e)}"
            import traceback
            detailed_error = traceback.format_exc()
            self.log_message.emit(error_message, "ERROR")
            self.log_message.emit(f"Details: {detailed_error}", "DEBUG")
            self.progress_updated.emit(0, "Error during startup!")
            self.initialization_complete.emit(False, e)


# Global reference to keep ModernWindow alive if needed, or manage within launch
_main_modern_window = None

def launch():
    global _main_modern_window # To keep ModernWindow instance alive

    # --- Early settings (before QApplication instantiation) ---
    if platform.system() == "Windows":
        try:
            ctypes.windll.uxtheme.SetPreferredAppMode(2) # 2 = Dark
        except Exception as e:
            print(f"Warning (launcher_app): Could not set Windows dark mode: {e}")

    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True) # Removed: Deprecated in Qt6, HighDPI is on by default

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME_LAUNCHER)
    app.setApplicationVersion("Beta.v5.0.1.Dev-ADas") # Updated version for v5

    # --- Post-QApplication instantiation settings ---
    app.setStyle('Fusion')
    qtmodern.styles.dark(app) # Apply qtmodern dark style first

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

    # --- Handle Initialization Completion ---
    def handle_initialization_finished(success, data_or_error): # 'data_or_error' from thread
        global _main_modern_window

        if success: # Non-GUI initialization was successful
            loading_screen.update_progress(85, "Creating user interface...") # New progress step
            QApplication.processEvents()
            try:
                # Step 2: Create MainWindow instance in the main thread
                main_window_instance = create_main_window_instance() # from main_app.py

                if not main_window_instance:
                    # This should ideally not happen if create_main_window_instance is robust
                    raise RuntimeError("Failed to create MainWindow instance (returned None).")

                loading_screen.append_log("Main window created successfully.", "SUCCESS")
                loading_screen.update_progress(95, "Finalizing UI...")
                QApplication.processEvents()

                # Close loading screen before showing main window to avoid overlap/flicker
                # A small delay can ensure messages are visible before close, if necessary.
                # time.sleep(0.5) # Optional: if logs are too quick to read before close
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
        else:
            # Non-GUI Initialization failed, error already logged by the thread.
            # 'data_or_error' here is the exception from the thread.
            loading_screen.append_log(f"Startup aborted due to non-GUI initialization failure: {str(data_or_error)}", "ERROR")
            loading_screen.update_progress(0, "Startup Failed!")
            # Keep loading screen open to show error messages.
            print(f"Error during non-GUI initialization (passed to main thread): {data_or_error}")

    thread.initialization_complete.connect(handle_initialization_finished)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
