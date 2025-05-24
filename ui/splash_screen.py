# File: DilasaKMLTool_v4/ui/splash_screen.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QSplashScreen, QLabel, QVBoxLayout, QWidget
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QTimer

# Define constants used by this module if not passed or imported globally
# This is for robustness if this file is ever handled separately.
INFO_COLOR_CONST_SPLASH = "#0078D7" # Blue for version

class SplashScreen(QSplashScreen):
    def __init__(self, app_name, app_version, tagline, logo_path):
        # Create a base pixmap for the splash screen (e.g., background color or main logo)
        # For a more controlled layout, we'll render everything onto this pixmap.
        splash_width = 550
        splash_height = 450
        
        # Create a QPixmap to draw on
        base_pixmap = QPixmap(splash_width, splash_height)
        base_pixmap.fill(Qt.GlobalColor.white) # White background

        # Painter to draw on the base_pixmap
        from PySide6.QtGui import QPainter # Import here to avoid circular if this file is imported early
        painter = QPainter(base_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw Logo
        logo_pixmap_orig = QPixmap(logo_path)
        if not logo_pixmap_orig.isNull():
            logo_scaled = logo_pixmap_orig.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_x = (splash_width - logo_scaled.width()) // 2
            painter.drawPixmap(logo_x, 30, logo_scaled) # Position logo
        else:
            print(f"Warning: Splash logo not found at {logo_path}")
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(0, 30, splash_width, 200, Qt.AlignmentFlag.AlignCenter, "[Logo Not Found]")


        # Draw App Name
        painter.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        painter.setPen(Qt.GlobalColor.black) # Or your FG_COLOR
        text_rect_app_name = painter.boundingRect(0, 0, splash_width - 40, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, app_name)
        painter.drawText(20, 230, splash_width - 40, text_rect_app_name.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap , app_name)
        
        # Draw Tagline
        painter.setFont(QFont("Segoe UI", 11))
        text_rect_tagline = painter.boundingRect(0, 0, splash_width - 60, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, tagline)
        painter.drawText(30, 230 + text_rect_app_name.height() + 10, splash_width - 60, text_rect_tagline.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, tagline)

        # Draw Version
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal, True)) # Italic
        painter.setPen(Qt.GlobalColor.darkBlue) # Using a standard color, or parse INFO_COLOR_CONST_SPLASH
        text_rect_version = painter.boundingRect(0, 0, splash_width - 40, 0, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter, app_version)
        painter.drawText(20, 230 + text_rect_app_name.height() + text_rect_tagline.height() + 25, splash_width - 40, text_rect_version.height(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, app_version)

        painter.end() # IMPORTANT to end painting

        super().__init__(base_pixmap) # Initialize QSplashScreen with the fully rendered pixmap
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # No need for self.label or complex layouts on QSplashScreen if everything is pre-rendered.
        # self.showMessage can still be used for simple messages if desired, but it draws on top.

    # show_message is inherited and can be used if needed, but we rendered text onto pixmap
    # def show_message(self, message, alignment=Qt.AlignmentFlag.AlignBottom, color=Qt.GlobalColor.black):
    #     super().showMessage(message, alignment, color)

