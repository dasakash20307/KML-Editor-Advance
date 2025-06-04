from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QFrame, QApplication) # Added QApplication for icon fallback
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
# It's good practice to import VERSION from main_app.py
# However, to keep the dialog self-contained or if main_app.py is complex to parse for just VERSION,
# it can be passed as an argument during dialog instantiation.
# For this subtask, VERSION is passed during instantiation.

class AboutDialog(QDialog):
    def __init__(self, version, parent=None):
        super().__init__(parent)

        self.setWindowTitle("About Advanced KML Editor")

        # Set window icon for the dialog itself
        # Attempt to load assets/logo.png, then fallback to a standard icon
        logo_icon = QIcon("assets/logo.png") # Adjust path if assets is not in root or use resource_path
        if logo_icon.isNull():
            # Try app_icon.ico as another common option if logo.png fails
            app_icon_ico = QIcon("assets/app_icon.ico") # Adjust path
            if not app_icon_ico.isNull():
                self.setWindowIcon(app_icon_ico)
            else: # Fallback to standard icon if both fail
                if QApplication.instance(): # Check if QApplication exists
                    self.setWindowIcon(QApplication.style().standardIcon(QApplication.style().StandardPixmap.SP_ComputerIcon))
        else:
            self.setWindowIcon(logo_icon)


        layout = QVBoxLayout(self)
        layout.setSpacing(15) # Add some spacing

        # 1. Application Name (as title or large label)
        title_label = QLabel("Advanced KML Editor")
        title_font = title_label.font()
        title_font.setPointSize(title_font.pointSize() + 4) # Make it larger
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Horizontal layout for Logo and Info
        h_layout = QHBoxLayout()
        h_layout.setSpacing(15)


        # Optional: Application Logo
        logo_display_label = QLabel()
        # Try loading logo.png, then app_icon.ico for the display
        pixmap_path = "assets/logo.png" # Adjust if needed, or use resource_path
        pixmap = QPixmap(pixmap_path)
        if pixmap.isNull():
            pixmap_path_ico = "assets/app_icon.ico" # Adjust if needed
            pixmap = QPixmap(pixmap_path_ico)

        if not pixmap.isNull():
            logo_display_label.setPixmap(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            h_layout.addWidget(logo_display_label, 0, Qt.AlignmentFlag.AlignTop) # Align logo to top

        info_layout = QVBoxLayout() # Layout for text details
        info_layout.setSpacing(8)

        # 2. Version
        version_label = QLabel(f"<b>Version:</b> {version}")
        info_layout.addWidget(version_label)

        # 3. Developer Name
        developer_label = QLabel("<b>Developed by:</b> Dilasa Janvikash Pratishthan")
        info_layout.addWidget(developer_label)

        # 4. Organizational Contact Email (Clickable)
        email = "systems.dilasa@gmail.com"
        contact_label = QLabel(f"<b>Contact:</b> <a href='mailto:{email}'>{email}</a>")
        contact_label.setOpenExternalLinks(True) # Makes the mailto link work
        info_layout.addWidget(contact_label)

        # 5. Copyright Information
        copyright_label = QLabel("© 2024 Dilasa Janvikash Pratishthan")
        info_layout.addWidget(copyright_label)

        # 6. Brief Application Description
        description_text = (
            "This application facilitates advanced KML file creation, editing, and management, "
            "offering tools for GIS data visualization, manipulation, and integration with field data. "
            "It is designed to support community development and land resource management efforts."
        )
        description_label = QLabel(description_text)
        description_label.setWordWrap(True)
        info_layout.addWidget(description_label)

        info_layout.addStretch() # Pushes content up if space allows

        h_layout.addLayout(info_layout, 1) # Give info layout more stretch factor
        layout.addLayout(h_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # OK Button
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True) # Makes it the default button (e.g., for Enter key)
        self.ok_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setMinimumWidth(450) # Set a reasonable minimum width
        # self.setFixedSize(self.sizeHint()) # Optional: make dialog non-resizable

if __name__ == '__main__':
    # For testing the dialog independently
    # from PySide6.QtWidgets import QApplication # Already imported
    import sys
    # Ensure QApplication instance exists for icon testing
    app = QApplication.instance()
    if not app: # Create if it doesn't exist
        app = QApplication(sys.argv)

    dialog = AboutDialog(version="TEST.1.0")
    dialog.exec()
    sys.exit(app.exec())
