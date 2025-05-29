# File: DilasaKMLTool_v4/main_app.py
# ----------------------------------------------------------------------
import sys
import os # Import the os module
from PySide6.QtWidgets import QApplication, QSplashScreen 
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


def main():
    # Set environment variable to pass Chromium flags
    # Disable GPU acceleration to prevent rendering issues
    # Attempt to resolve rendering issues by disabling GPU compositing, while keeping WebGL enabled.
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu-compositing"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME_MAIN)
    app.setApplicationVersion(APP_VERSION_MAIN)

    logo_full_path = resource_path(LOGO_FILE_NAME_MAIN)
    main_window = MainWindow() 
    splash = CustomSplashScreen(APP_NAME_MAIN, APP_VERSION_MAIN, ORGANIZATION_TAGLINE_MAIN, logo_full_path)
    splash.show()
    
    if splash.screen(): 
        screen_geo = splash.screen().geometry()
        splash.move((screen_geo.width() - splash.width()) // 2,
                    (screen_geo.height() - splash.height()) // 2)

    def show_main_window_after_splash():
        splash.close()
        main_window.show() 
        main_window.activateWindow() 
        main_window.raise_()         

    QTimer.singleShot(4000, show_main_window_after_splash) 
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
