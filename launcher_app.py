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
from main_app import prepare_main_window
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
    # Signals: success_status, main_window_instance_or_error
    initialization_complete = Signal(bool, object)

    def run(self):
        try:
            self.log_message.emit("Starting application initialization...", "INFO")
            self.progress_updated.emit(10, "Initializing core components...")
            # Simulate some work
            time.sleep(0.5) # Placeholder for actual init steps

            # In a real app, CredentialManager and other core services would be initialized here.
            # For now, we just call prepare_main_window.
            # More granular progress updates would involve prepare_main_window (or MainWindow itself)
            # emitting signals that this thread could catch and re-emit.

            self.log_message.emit("Creating main window...", "INFO")
            self.progress_updated.emit(30, "Loading main user interface...")
            main_window = prepare_main_window() # This is the refactored function
            time.sleep(1) # Simulate main window setup

            if not main_window: # Basic check
                raise RuntimeError("Main window preparation failed.")

            # Simulate further loading steps
            self.progress_updated.emit(70, "Finalizing setup...")
            # Example: if main_window has a method to do more setup and report progress:
            # main_window.perform_final_setup(progress_callback=self.progress_updated, log_callback=self.log_message)
            time.sleep(1)

            self.log_message.emit("Initialization successful.", "SUCCESS")
            self.progress_updated.emit(100, "Done!")
            self.initialization_complete.emit(True, main_window)

        except Exception as e:
            error_message = f"Initialization failed: {str(e)}"
            import traceback
            detailed_error = traceback.format_exc()
            self.log_message.emit(error_message, "ERROR")
            self.log_message.emit(f"Details: {detailed_error}", "DEBUG") # DEBUG for detailed traceback
            self.progress_updated.emit(0, "Error during startup!") # Reset progress or show error status
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

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

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
    def handle_initialization_finished(success, result):
        global _main_modern_window # Ensure we assign to the global var

        loading_screen.update_progress(100, "Finalizing..." if success else "Startup Failed!")
        QApplication.processEvents() # Update UI one last time

        if success:
            main_window_instance = result
            if main_window_instance:
                # Close loading screen *before* showing main window to avoid flicker
                loading_screen.close()

                _main_modern_window = qtmodern.windows.ModernWindow(main_window_instance)
                _main_modern_window.show()
                # main_window_instance.show() # If not using ModernWindow or if it handles it
            else:
                # This case should ideally be caught by the thread's error handling
                loading_screen.append_log("Critical error: Main window not created, but thread reported success.", "ERROR")
                # Keep loading screen open to show the error
        else:
            # Error already logged by the thread.
            # Keep loading screen open to show error messages.
            # Optionally, add a close button or retry mechanism here.
            print(f"Error during initialization: {result}")
            # loading_screen.enable_close_button() # If such a feature exists

    thread.initialization_complete.connect(handle_initialization_finished)
    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
