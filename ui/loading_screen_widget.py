# File: ui/loading_screen_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QProgressBar,
                             QGroupBox, QTextEdit, QApplication, QPushButton,
                             QSpacerItem, QSizePolicy, QHBoxLayout)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QColor

# Try to reuse or adapt constants if they were defined in the old splash screen
# For example, colors or specific font sizes.
# INFO_COLOR_CONST_SPLASH = "#0078D7" # Example from old splash

class LoadingScreenWidget(QWidget):
    # Define signals if this widget needs to communicate status changes
    # For example, if a close button on the widget should signal the launcher
    # Or if the launcher needs to know about internal state changes not covered by slots.

    def __init__(self, app_name="App Name", company_name="Company Name",
                 tagline="Tagline", version_code="v0.0.0",
                 developer_name="Developer", support_email="support@example.com",
                 parent=None):
        super().__init__(parent)

        self.setWindowTitle("Initializing...")
        # Configure to be modal, frameless, and always-on-top
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog) # Qt.Dialog helps with modality and appearance

        # Define initial size - this can be adjusted
        self.setFixedSize(600, 450) # Or use dynamic sizing based on content

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # Add some padding

        # --- Information Labels ---
        self.app_name_label = QLabel(app_name)
        self.app_name_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.app_name_label)

        self.tagline_label = QLabel(tagline)
        self.tagline_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.tagline_label)

        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))


        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100) # Default range, can be updated
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Initializing...")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Collapsible Log Section ---
        self.log_group_box = QGroupBox("Details")
        self.log_group_box.setCheckable(True) # Makes the title a checkbox to toggle
        self.log_group_box.setChecked(False) # Start collapsed

        log_layout = QVBoxLayout()
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setFont(QFont("Consolas", 8)) # Monospaced font for logs
        self.log_text_edit.setFixedHeight(100) # Initial height for log area
        log_layout.addWidget(self.log_text_edit)
        self.log_group_box.setLayout(log_layout)

        # Toggle visibility based on checkbox
        self.log_group_box.toggled.connect(self.log_text_edit.setVisible)
        self.log_text_edit.setVisible(False) # Ensure it respects the initial collapsed state

        main_layout.addWidget(self.log_group_box)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # --- Footer Labels ---
        footer_layout = QHBoxLayout()
        self.version_label = QLabel(f"Version: {version_code}")
        self.version_label.setFont(QFont("Segoe UI", 8))

        self.developer_label = QLabel(f"Developer: {developer_name}")
        self.developer_label.setFont(QFont("Segoe UI", 8))

        footer_layout.addWidget(self.version_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.developer_label)
        main_layout.addLayout(footer_layout)

        # Apply some basic styling (can be enhanced with QSS)
        self.setStyleSheet("""
            QWidget {
                /* General font for the widget if not overridden */
                /* font-family: "Segoe UI"; */ /* Already set by individual labels */
            }
            LoadingScreenWidget {
                background-color: #FFFFFF; /* White background */
                border: 1px solid #CCCCCC; /* Subtle border */
            }
            QLabel {
                color: #333333; /* Dark gray text */
            }
            QProgressBar {
                min-height: 20px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078D7; /* Blue progress chunk */
                width: 10px; /* Width of the progress segments */
                margin: 0.5px;
            }
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }
            QTextEdit {
                background-color: #F0F0F0; /* Light gray for log background */
                color: #000000; /* Black text for logs */
                border: 1px solid #B0B0B0;
            }
        """)

    @Slot(str, str) # level can be 'INFO', 'WARNING', 'ERROR'
    def append_log(self, message, level="INFO"):
        level_color_map = {
            "INFO": "black",
            "WARNING": "orange",
            "ERROR": "red",
            "DEBUG": "gray",
            "SUCCESS": "green"
        }
        color = level_color_map.get(level.upper(), "black")

        formatted_message = f"<font color='{color}'>[{level.upper()}] {message}</font>"
        self.log_text_edit.append(formatted_message)

        # Optional: Auto-expand log if an error occurs
        if level.upper() == "ERROR" and not self.log_group_box.isChecked():
            self.log_group_box.setChecked(True)

    @Slot(int, str)
    def update_progress(self, value, text_status):
        self.progress_bar.setValue(value)
        if text_status:
            self.status_label.setText(text_status)
        else:
            self.status_label.setText("")

    def center_on_screen(self):
        parent_widget = self.parent()
        if isinstance(parent_widget, QWidget): # Check if parent is a QWidget
            parent_geo = parent_widget.geometry()
            self.move(parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                      parent_geo.y() + (parent_geo.height() - self.height()) // 2)
        else:
            # Fallback if no parent or parent is not a QWidget
            screen = QApplication.primaryScreen()
            if screen:
                screen_geo = screen.geometry()
                self.move((screen_geo.width() - self.width()) // 2,
                          (screen_geo.height() - self.height()) // 2)

# Example Usage (for testing this widget independently)
if __name__ == '__main__':
    import sys

    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()

    app.setStyle("Fusion")

    APP_NAME_TEST = "KML Editor Advance"
    COMPANY_NAME_TEST = "Dilasa Janvikash Pratishthan"
    TAGLINE_TEST = "Empowering Communities with Geospatial Tools"
    VERSION_CODE_TEST = "v5.0.0-alpha"
    DEVELOPER_TEST = "A.Das"
    SUPPORT_EMAIL_TEST = "support@dilasa.org"

    loading_screen = LoadingScreenWidget(
        app_name=APP_NAME_TEST,
        company_name=COMPANY_NAME_TEST,
        tagline=TAGLINE_TEST,
        version_code=VERSION_CODE_TEST,
        developer_name=DEVELOPER_TEST,
        support_email=SUPPORT_EMAIL_TEST
    )
    loading_screen.center_on_screen()
    loading_screen.show()

    from PySide6.QtCore import QTimer
    timer = QTimer()
    progress_tracker = [0] # Changed from progress_value = 0

    def simulate_loading():
        # nonlocal progress_value # Removed
        progress_tracker[0] += 10 # Modified
        if progress_tracker[0] <= 100: # Modified
            loading_screen.update_progress(progress_tracker[0], f"Loading component {progress_tracker[0]//10}...") # Modified
            if progress_tracker[0] == 20: # Modified
                loading_screen.append_log("Initializing core modules...", "INFO")
            elif progress_tracker[0] == 50: # Modified
                loading_screen.append_log("Configuration loaded.", "SUCCESS")
            elif progress_tracker[0] == 70: # Modified
                loading_screen.append_log("Network check failed, retrying...", "WARNING")
            elif progress_tracker[0] == 90: # Modified
                loading_screen.append_log("Critical component missing!", "ERROR")
        else:
            timer.stop()
            loading_screen.update_progress(100, "Almost done!")
            loading_screen.append_log("All tasks simulated.", "DEBUG")
            # QTimer.singleShot(2000, loading_screen.close)

    timer.timeout.connect(simulate_loading)
    timer.start(300) # ms interval

    sys.exit(app.exec())
