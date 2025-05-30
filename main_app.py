# File: DilasaKMLTool_v4/main_app.py
# ----------------------------------------------------------------------
import sys
import os # Import the os module
# QApplication is removed from this import line as it's instantiated in launcher_app.py
from PySide6.QtWidgets import QSplashScreen
# QApplication might still be needed for type hinting (e.g. QApplication.instance())
# For now, we'll import it inside create_and_show_main_window where it's used.
from PySide6.QtGui import QPixmap, QFont, QPainter, QColor
from PySide6.QtCore import QTimer, Qt

from ui.main_window import MainWindow
from core.utils import resource_path

APP_NAME_MAIN = "Dilasa Advance KML Tool"
APP_VERSION_MAIN = "Beta.v4.001.Dv-A.Das"
ORGANIZATION_TAGLINE_MAIN = "Developed by Dilasa Janvikash Pratishthan to support community upliftment"
LOGO_FILE_NAME_MAIN = "dilasa_logo.jpg"
INFO_COLOR_CONST_MAIN = "#0078D7"

class CustomSplashScreen(QSplashScreen):
    def __init__(self, app_name, app_version, tagline, logo_path):
        splash_width = 550
        splash_height = 480

        base_pixmap = QPixmap(splash_width, splash_height)
        base_pixmap.fill(Qt.GlobalColor.white)

        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        logo_pixmap_orig = QPixmap(logo_path)
        if not logo_pixmap_orig.isNull():
            logo_scaled = logo_pixmap_orig.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_x = (splash_width - logo_scaled.width()) // 2
            painter.drawPixmap(logo_x, 30, logo_scaled)
        else:
            painter.setFont(QFont("Segoe UI", 12)); painter.drawText(0, 30, splash_width, 200, Qt.AlignmentFlag.AlignCenter, "[Logo Not Found]")

        current_y = 30 + (200 if not logo_pixmap_orig.isNull() else 200) + 20

        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold)); painter.setPen(QColor("#202020"))
        text_rect_app_name = painter.boundingRect(0,0, splash_width - 40, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, app_name)
        painter.drawText(20, current_y, splash_width - 40, text_rect_app_name.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap , app_name)
        current_y += text_rect_app_name.height() + 15

        painter.setFont(QFont("Segoe UI", 11)); painter.setPen(QColor("#333333"))
        text_rect_tagline = painter.boundingRect(0,0, splash_width - 60, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, tagline)
        painter.drawText(30, current_y, splash_width - 60, text_rect_tagline.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, tagline)
        current_y += text_rect_tagline.height() + 25

        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal, False))
        painter.setPen(QColor(INFO_COLOR_CONST_MAIN))
        text_rect_version = painter.boundingRect(0,0, splash_width - 40, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, app_version)
        painter.drawText(20, current_y, splash_width - 40, text_rect_version.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, app_version)

        painter.end()
        super().__init__(base_pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

# New function to encapsulate UI creation and display
def create_and_show_main_window():
    # Set environment variable to pass Chromium flags (This could also be in launcher_app.py,
    # but keeping it here if it's closely tied to MainWindow's web components)
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing"

    # QApplication instance is now created in launcher_app.py
    # App details like name and version will be set in launcher_app.py

    logo_full_path = resource_path(LOGO_FILE_NAME_MAIN)
    main_window = MainWindow()
    splash = CustomSplashScreen(APP_NAME_MAIN, APP_VERSION_MAIN, ORGANIZATION_TAGLINE_MAIN, logo_full_path)

    # Access QApplication instance for screen geometry.
    # This assumes QApplication is already instantiated in launcher_app.py.
    from PySide6.QtWidgets import QApplication # Import for QApplication.instance()
    app_instance = QApplication.instance()
    if app_instance:
        current_screen = splash.screen() # Use splash.screen() to get QScreen
        if current_screen:
            screen_geo = current_screen.geometry()
            splash.move((screen_geo.width() - splash.width()) // 2,
                        (screen_geo.height() - splash.height()) // 2)

    splash.show()

    def show_main_window_after_splash():
        splash.close()
        main_window.show()
        main_window.activateWindow()
        main_window.raise_()
        # ModernWindow wrapping will be handled in launcher_app.py if used.

    QTimer.singleShot(4000, show_main_window_after_splash)

    # sys.exit(app.exec()) # REMOVE THIS LINE. app.exec() is called in launcher_app.py

    return main_window # Return the main_window instance so launcher_app can wrap it

# The old main() function is effectively replaced by create_and_show_main_window()
# and the updated __main__ block below.

if __name__ == "__main__":
    # This block is for testing main_app.py directly.
    # The actual application entry point is launcher_app.py.
    print("Running main_app.py directly for testing UI components.")
    print("For full application launch, run launcher_app.py.")

    # To test main_app.py independently, a QApplication instance would be needed here:
    # from PySide6.QtWidgets import QApplication # Already imported above for .instance()
    # import sys
    # test_app = QApplication(sys.argv) # Create a temporary app for testing
    # APP_NAME_MAIN and APP_VERSION_MAIN would be used by CustomSplashScreen
    # test_app.setApplicationName(APP_NAME_MAIN) # Optional for testing
    # test_app.setApplicationVersion(APP_VERSION_MAIN) # Optional for testing
    # main_window_instance = create_and_show_main_window()
    # sys.exit(test_app.exec()) # Run the app's event loop for testing

    # For now, just a print statement. The main execution is handled by launcher_app.py.
    pass
