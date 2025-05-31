# Project Log

## Task 1: Initial Styling & Project Setup (from CA6)

**Objective:** Lay the visual and structural groundwork for the v5 application, including modern styling defaults, high-DPI compatibility, and a consistent look and feel.

**Summary of Changes:**

1.  **`launcher_app.py` (New File):**
    *   Created as the new primary entry point for the application (`python launcher_app.py`).
    *   Handles `QApplication` instantiation and lifecycle.
    *   Sets application name and version (e.g., "Dilasa Advance KML Tool", "Beta.v5.000").
    *   **High DPI Scaling:** Enabled `QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)` before `QApplication` instantiation for crisp display on high-resolution screens.
    *   **Windows Dark Mode Awareness:** Conditionally (for Windows OS) calls `ctypes.windll.uxtheme.SetPreferredAppMode(2)` to enable native dark mode for window title bars, ensuring consistency with dark themes. This is done very early in startup.
    *   **Application Style:** Set to `app.setStyle('Fusion')` for a modern base look.
    *   **`qtmodern` Integration:**
        *   `qtmodern.styles.dark(app)` applied after 'Fusion' to implement a dark theme.
        *   The main window instance (from `main_app.py`) is wrapped with `qtmodern.windows.ModernWindow` for a modern window frame and appearance.
    *   **Global Stylesheet Loading:** Loads `assets/style.qss` and appends its content to the application's stylesheet, allowing for iterative custom styling. Includes error handling for missing file.
    *   Imports `create_and_show_main_window` from `main_app.py` to launch the UI.

2.  **`main_app.py` (Modified):**
    *   Refactored to separate UI creation from `QApplication` lifecycle management.
    *   `QApplication` instantiation and `app.exec()` calls were removed from its direct execution flow.
    *   A new function, `create_and_show_main_window()`, was created. This function encapsulates the logic for:
        *   Setting the `QTWEBENGINE_CHROMIUM_FLAGS` environment variable.
        *   Creating and showing the `CustomSplashScreen`.
        *   Creating the `MainWindow` instance.
        *   Using a `QTimer` to display the `MainWindow` after the splash screen.
    *   `create_and_show_main_window()` now returns the `main_window` instance to `launcher_app.py` for wrapping with `ModernWindow`.
    *   The `if __name__ == "__main__":` block was updated to reflect that `launcher_app.py` is the new entry point.

3.  **`assets/style.qss` (New File):**
    *   Created as an empty file. This file is intended to hold global Qt StyleSheet (QSS) rules that will be developed iteratively to customize the application's appearance beyond the `qtmodern` theme.

4.  **`requirements_new.txt` (Modified):**
    *   Added `qtmodern` to the list of project dependencies.

**Outcome:**
The application now starts with a modern dark theme, supports high-DPI displays, and has a clear separation between application setup/styling (`launcher_app.py`) and UI creation (`main_app.py`). The foundation for further v5 development is established.
---
**Update Date:** 2025-05-30
**Version:** Beta.v5.0.1.Dev-ADas
**Author:** AI Assistant (Jules)
**Task Reference:** CA5 - App Launcher Implementation (Task 2)

**Changes Implemented:**

1.  **New App Launcher (`launcher_app.py`):**
    *   Established `launcher_app.py` as the primary executable for the application.
    *   Implemented a new `LoadingScreenWidget` (`ui/loading_screen_widget.py`) that displays initialization progress, logs, and application information (App Name, Version, Developer, etc.).
    *   The loading screen is modal, frameless, and stays on top during startup.
    *   It features a progress bar and a collapsible section for detailed log messages.

2.  **Threaded Initialization:**
    *   Main application initialization, including the creation of `MainWindow`, is now performed in a background `QThread` (`InitializationThread` in `launcher_app.py`).
    *   This ensures the loading screen UI remains responsive.
    *   The thread emits signals to update the loading screen's progress bar and log view.

3.  **Refactoring of `main_app.py`:**
    *   The `CustomSplashScreen` class and its associated `QTimer` logic have been removed.
    *   The `main()` function and direct script execution capabilities were removed.
    *   Core `MainWindow` creation logic was refactored into a `prepare_main_window()` function, which is now called by the `InitializationThread`.

4.  **Retirement of `ui/splash_screen.py`:**
    *   The old splash screen UI file (`ui/splash_screen.py`) has been retired as a directly used component. Its visual elements can be adapted if needed in the future.

5.  **Application Entry and Flow:**
    *   The application now starts with `python launcher_app.py`.
    *   The `LoadingScreenWidget` provides immediate feedback.
    *   On successful initialization, the loading screen closes, and the main application window (`MainWindow`) is displayed.
    *   If initialization fails, the loading screen remains visible, displaying error messages from the logs.

**Impact:**
*   Improved user experience by providing immediate feedback and startup diagnostics.
*   More robust startup sequence by handling initialization in a separate thread.
*   Modernized application entry point aligning with v5 architecture goals.
---
---
**Update Date:** 2025-05-30
**Version:** Beta.v5.0.1.Dev-ADas (as per last launcher update)
**Author:** AI Assistant (Jules)
**Task Reference:** CA5 - App Launcher Implementation (Task 2) - Detailed Implementation & Debugging Summary

**Changes Implemented & Critical Analysis for Task 2:**

This entry provides a detailed look at the implementation of the App Launcher, including crucial debugging steps that refined the initial approach.

1.  **Core Goal:** The primary objective of Task 2 was to replace the previous startup mechanism with a dedicated App Launcher (`launcher_app.py`) featuring an informative `LoadingScreenWidget` (`ui/loading_screen_widget.py`). This launcher manages the main application initialization in a background `QThread` to keep the UI responsive. This core goal was achieved.

2.  **Initial Implementation Steps:**
    *   `launcher_app.py` was created as the new entry point.
    *   `ui/loading_screen_widget.py` was developed with `QLabel`s for app information, a `QProgressBar`, and a collapsible `QTextEdit` for logs, along with `update_progress` and `append_log` slots.
    *   `main_app.py` was refactored: `CustomSplashScreen` and its `QTimer` were removed, and `MainWindow` creation logic was initially encapsulated in a `prepare_main_window` function.
    *   An `InitializationThread` was implemented in `launcher_app.py` to call `prepare_main_window` and emit signals for progress and logs to the `LoadingScreenWidget`.

3.  **Significant Debugging and Refinement Journey:**

    *   **Runtime Error (`SyntaxError` for `nonlocal`):** An early `SyntaxError` ("no binding for nonlocal 'progress_value' found") occurred in the test block of `loading_screen_widget.py`.
        *   **Solution:** Modified the test variable `progress_value` to be a mutable list (`progress_tracker = [0]`), allowing the nested test function `simulate_loading` to modify it without `nonlocal`, resolving the syntax issue for the test environment.

    *   **Runtime Error (`TypeError` for `resource_path`):** The `resource_path` utility function was incorrectly called with two arguments in `launcher_app.py` instead of the defined one.
        *   **Solution:** Corrected the call to `resource_path("style.qss")`, aligning with its definition in `core/utils.py`.

    *   **Critical Runtime Error (Qt Threading - `QObject::setParent` and `QBasicTimer` errors):** The most significant challenge arose from Qt's GUI threading rules. The initial design involved creating the `MainWindow` instance within the `InitializationThread` and then passing this instance to the main thread. This led to errors like "QObject::setParent: Cannot set parent, new parent is in a different thread" when `ModernWindow` (in the main thread) tried to manage the `MainWindow` instance.
        *   **Debugging Insight:** Realized that all `QWidget`-derived objects (like `MainWindow`) *must* be created and primarily manipulated in the main GUI thread.
        *   **Solution (Major Refactor):**
            1.  `main_app.py` was further refactored:
                *   `prepare_main_window` was split into `perform_non_gui_initialization()` (for background-safe tasks, currently a placeholder) and `create_main_window_instance()` (solely for `MainWindow()` instantiation).
            2.  `InitializationThread` in `launcher_app.py` was changed:
                *   Its `run()` method now executes `perform_non_gui_initialization()`.
                *   The `initialization_complete` signal now indicates success/failure of these non-GUI tasks and does *not* pass the `MainWindow` instance.
            3.  The `handle_initialization_finished` slot in `launcher_app.py` (running in the main thread) was updated: Upon successful completion of non-GUI tasks by the thread, it now calls `create_main_window_instance()` to create `MainWindow` directly in the main thread. This resolved the cross-thread errors.

    *   **Deprecation Warning (`Qt.AA_EnableHighDpiScaling`):** A deprecation warning for this Qt6 attribute was noted.
        *   **Solution:** The attribute `Qt.AA_EnableHighDpiScaling` was removed from `launcher_app.py`, as High DPI is generally enabled by default in Qt6.

    *   **Windows Dark Mode Warning (`SetPreferredAppMode` not found):** An informational warning on some systems.
        *   **Solution:** Confirmed the existing `try-except` block around this Windows-specific call is appropriate. No changes were made as it's non-critical.

4.  **Alignment with Task 2 Description (from `v5_task_and_Concept.md`):**
    *   The final implementation successfully meets all key functional requirements outlined in Task 2.
    *   The crucial adjustment was ensuring `MainWindow` object creation occurs in the main thread, a detail not explicitly specified in the initial task description but vital for Qt application stability. The launcher still offloads initialization work to a thread, but this work is now defined as non-GUI preparatory steps.

**Impact & Conclusion for Task 2:**
*   The App Launcher now provides a responsive loading screen and correctly initializes the main application.
*   The debugging process, especially addressing the Qt threading model for GUI objects, was critical to achieving a stable and correct implementation.
*   The system is now more robust and adheres to Qt's best practices for multi-threaded GUI applications.
---
---
**Update Date:** 2024-05-31
**Version:** Beta.v5.0.x.Dev-ADas (Reflects ongoing V5 development)
**Author:** AI Assistant (Jules)
**Task Reference:** Task 3: CredentialManager & First Run Setup (from CA4 Part 1)

**Objective:**
Establish the application's identity and operational mode. Create a system for unique installation IDs and nicknames, allow user selection of "Central App" or "Connected App" mode, and configure necessary data paths accordingly. This is a one-time setup on first launch, with settings persisted in a local `device_config.db`.

**Core Components Implemented:**

1.  **`core/credential_manager.py` (New File):**
    *   Manages `device_config.db`, a local SQLite database for storing device-specific settings.
    *   Uses the `platformdirs` library to determine a standard, cross-platform user-specific data directory for `device_config.db` (e.g., under `DilasaKMLTool_V5_Config`).
    *   **First Run Detection:** Determines if the application is running for the first time by checking for the existence of `device_config.db`.
    *   **Device Identity:** Generates and stores a unique 8-digit alphanumeric device UUID. Manages a user-provided device nickname.
    *   **Application Mode:** Stores whether the app is configured as "Central App" or "Connected App".
    *   **Data Paths:** Stores paths for the main database file and KML files folder, as configured by the user.
    *   Provides getter methods for all settings and a method `get_config_file_path()` to get the full path to `device_config.db`.

2.  **`ui/first_run_setup_dialogs.py` (New File):**
    *   Defines a sequence of `QDialog` subclasses for the first-run setup process:
        *   `NicknameDialog`: Prompts the user for a device nickname.
        *   `ModeSelectionDialog`: Allows the user to select "Central App" or "Connected App" mode.
        *   `PathConfigurationDialog`: Dynamically adjusts based on the selected mode.
            *   For "Central App": Uses `QFileDialog` for selecting local paths for a new/existing database and KML folder.
            *   For "Connected App": Provides fields for entering network/shared paths to an existing Central App's data.
    *   Includes input validation for the dialogs. Pylance suggested fixes for QMessageBox buttons and layout attribute names were also applied.

3.  **`database/db_manager.py` (Modified):**
    *   Removed hardcoded constants (`DB_FOLDER_NAME_CONST`, `DB_FILE_NAME_CONST`) and associated logic for determining the main database path via AppData.
    *   The `DatabaseManager.__init__` now expects the full `db_path` to be provided externally.
    *   The actual database connection is deferred to an explicit `connect()` method, called by the launcher on the main UI thread, to resolve SQLite threading issues.
    *   Added None-checks for `self.conn` and `self.cursor` in data access methods for robustness, addressing Pylance warnings.


**Debugging Journey & Key Fixes/Enhancements:**

The integration of `CredentialManager` and the deferred database path logic surfaced issues in the application's startup sequence, which required significant debugging:

1.  **Initial Challenge:** The application failed to start correctly after Task 3's initial components were integrated. The loading screen would either freeze or report errors related to `CredentialManager` not finding configured paths (because `device_config.db` was incomplete or missing, and the error handling path itself had a bug).

2.  **`TypeError: native Qt signal instance 'log_message' is not callable`:**
    *   **Diagnosis:** This critical error crashed the initialization thread. User-provided tracebacks pinpointed that a call to `self.log_message` in `launcher_app.py`'s `InitializationThread` (specifically when logging a summary of `perform_non_gui_initialization` failure) was missing `.emit()`.
    *   **Fix:** The specific call `self.log_message(...)` was corrected to `self.log_message.emit(...)` in `launcher_app.py`. The exception handling in the thread was also made more robust.

3.  **SQLite Threading Error (`SQLite objects created in a thread can only be used in that same thread`):**
    *   **Diagnosis:** After fixing the `TypeError`, `MainWindow` would load but immediately fail to fetch data (e.g., API sources, polygon data). This was because the `DatabaseManager`'s connection was established in the background `InitializationThread` but then used by `MainWindow` and its models in the main UI thread.
    *   **Fix:**
        *   `DatabaseManager.__init__` was modified to only store the `db_path` and not connect.
        *   A new `DatabaseManager.connect()` method was created to perform the actual connection, table creation, and schema migration.
        *   `main_app.perform_non_gui_initialization()` now only instantiates `DatabaseManager` (unconnected).
        *   `launcher_app.py`'s `handle_initialization_finished` (on the main thread) now calls `db_manager.connect()` *before* `MainWindow` is created.

4.  **Enhancement: Handling Corrupted/Incomplete Configuration:**
    *   To improve robustness, if `device_config.db` exists (not a first run) but is missing critical settings (like `main_db_path`):
        *   This state is detected by `CredentialManager` and reported by `main_app.py` with a specific status (`CORRUPT_CONFIG`) and the path to `device_config.db`.
        *   `launcher_app.py` now catches this status, informs the user on the loading screen about the issue (including config file location), and automatically triggers the first-run setup dialogs (`_execute_first_run_setup_flow`) to allow the user to reconfigure.
        *   After setup is completed via these dialogs, the application advises a restart and then automatically quits to ensure a clean start with the new configuration.

5.  **Pylance Static Analysis Issues Addressed:**
    *   During the debugging and implementation process, numerous Pylance-reported issues were fixed across several files:
        *   `core/credential_manager.py`: Fixed unreachable `except OSError` in test code.
        *   `core/utils.py`: Refactored `sys._MEIPASS` access using `getattr`.
        *   `ui/loading_screen_widget.py`: Corrected Qt Enum usage for window modality/flags and ensured safer parent geometry access. Loading screen UI was also tweaked (removed always-on-top, made movable by restoring frame, attempted rounded corners). Theming aspects (hardcoded colors) were adjusted for baseline observation.
        *   `ui/main_window.py`: Removed hardcoded header background color.
        *   The Pylance fixes for `ui/first_run_setup_dialogs.py` and `database/db_manager.py` were mentioned above in relation to those components.

**Alignment with Requirements & Current Status:**

*   The implemented `CredentialManager` and first-run setup dialogs fulfill the core requirements of Task 3:
    *   Unique device ID and nickname are handled.
    *   User can select "Central App" or "Connected App" mode.
    *   Data paths are configured based on the selected mode.
    *   All settings are persisted in `device_config.db` in a platform-appropriate user data directory.
    *   `DatabaseManager` is no longer using hardcoded paths and its connection is thread-safe.
*   The debugging journey has made the application startup significantly more robust.
*   The system now gracefully handles scenarios where `device_config.db` is present but incomplete by guiding the user through a reconfiguration process.
*   The application successfully launches and can load `MainWindow` if the configuration is valid.

**Further Considerations (Not part of Task 3 but related):**
*   The actual invocation of the first-run setup dialogs for a *true first run* (i.e., `device_config.db` does not exist at all) is primarily the responsibility of `launcher_app.py` logic that should ideally check `CredentialManager.is_first_run()` very early in the startup sequence. The current "corrupt config" flow reuses the dialogs; ensuring the "true first run" path is equally robust or integrated into this new setup trigger in `handle_initialization_finished` might be beneficial.
---
