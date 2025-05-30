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
