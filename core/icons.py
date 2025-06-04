"""
Icons and Images Manager for the KML Editor Application

This module centralizes all icon, image, and logo resources used throughout the application.
It provides functions to load icons with proper fallbacks and consistent sizing.

Usage:
    from core.icons import get_app_icon, get_logo, get_toolbar_icon, etc.
"""

import os
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QStyle, QApplication
from core.utils import resource_path

# Path constants
ASSETS_DIR = "assets"
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# File name constants
ORGANIZATION_LOGO = "dilasa_logo.jpg"  # Organization logo - recommended size: 128x128px with 1:1 ratio
APP_ICON = "app_icon.ico"              # Application icon - Windows requires .ico format
FALLBACK_LOGO = "logo_placeholder.png"  # Fallback logo if main logo is missing

# Toolbar icons - all recommended 24x24px with 1:1 ratio
TOOLBAR_ICONS = {
    "import_csv": "import_csv.png",
    "export_csv": "export_csv.png",
    "fetch_api": "fetch_api.png",
    "manage_api": "manage_api.png",
    "generate_kml": "generate_kml.png",
    "delete_rows": "delete_rows.png",
    "edit_table": "edit_table.png",
    "view_ge": "view_ge.png",
    "multi_kml_view": "multi_kml_view.png",
    "multi_kml_edit": "multi_kml_edit.png",
    "save_edits": "save_edits.png",
    "cancel_edits": "cancel_edits.png",
    "exit_multi_mode": "exit_multi_mode.png",
    "filter": "filter.png",
}

# Standard icons from PySide that can be used as fallbacks
STANDARD_ICON_MAPPING = {
    "import_csv": QStyle.StandardPixmap.SP_DialogOpenButton,
    "export_csv": QStyle.StandardPixmap.SP_DialogSaveButton,
    "fetch_api": QStyle.StandardPixmap.SP_ArrowDown,
    "manage_api": QStyle.StandardPixmap.SP_DialogApplyButton,
    "generate_kml": QStyle.StandardPixmap.SP_FileIcon,
    "delete_rows": QStyle.StandardPixmap.SP_TrashIcon,
    "edit_table": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "view_ge": QStyle.StandardPixmap.SP_CommandLink,
    "multi_kml_view": QStyle.StandardPixmap.SP_DriveNetIcon,
    "multi_kml_edit": QStyle.StandardPixmap.SP_FileLinkIcon,
    "save_edits": QStyle.StandardPixmap.SP_DialogSaveButton,
    "cancel_edits": QStyle.StandardPixmap.SP_DialogCloseButton,
    "exit_multi_mode": QStyle.StandardPixmap.SP_DialogCancelButton,
    "filter": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "settings": QStyle.StandardPixmap.SP_DialogApplyButton,
    "about": QStyle.StandardPixmap.SP_MessageBoxInformation,
    "help": QStyle.StandardPixmap.SP_MessageBoxQuestion,
}

# Functions for retrieving icons and images

def get_organization_logo(size=QSize(40, 40)):
    """
    Get the organization logo as a QPixmap.
    
    Args:
        size (QSize): Desired size of the logo, default 40x40px
    
    Returns:
        QPixmap: The logo as a QPixmap, scaled to the requested size
    """
    # Try primary organization logo
    logo_path = resource_path(os.path.join(ASSETS_DIR, ORGANIZATION_LOGO))
    if os.path.exists(logo_path):
        pixmap = QPixmap(logo_path)
        if not pixmap.isNull():
            return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    # Try fallback logo
    fallback_path = resource_path(os.path.join(ASSETS_DIR, FALLBACK_LOGO))
    if os.path.exists(fallback_path):
        pixmap = QPixmap(fallback_path)
        if not pixmap.isNull():
            return pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    
    # If both fail, return computer icon as last resort
    app = QApplication.instance()
    if app and isinstance(app, QApplication):
        style = app.style()
        return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon).pixmap(size)
    
    # If all else fails, return null pixmap
    return QPixmap()

def get_app_icon():
    """
    Get the application icon.
    
    Returns:
        QIcon: The application icon
    """
    # Try custom app icon
    app_icon_path = resource_path(os.path.join(ASSETS_DIR, APP_ICON))
    if os.path.exists(app_icon_path):
        icon = QIcon(app_icon_path)
        if not icon.isNull():
            return icon
    
    # Try using logo as app icon
    logo_path = resource_path(os.path.join(ASSETS_DIR, ORGANIZATION_LOGO))
    if os.path.exists(logo_path):
        icon = QIcon(logo_path)
        if not icon.isNull():
            return icon
    
    # Fallback to standard computer icon
    app = QApplication.instance()
    if app and isinstance(app, QApplication):
        style = app.style()
        return style.standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    
    # If all else fails, return empty icon
    return QIcon()

def get_toolbar_icon(name, size=QSize(24, 24)):
    """
    Get an icon for toolbar buttons with proper fallbacks.
    
    Args:
        name (str): Icon name as defined in TOOLBAR_ICONS or STANDARD_ICON_MAPPING
        size (QSize): Desired icon size, default 24x24px
    
    Returns:
        QIcon: The requested icon
    """
    # First try to load from custom icons directory
    if name in TOOLBAR_ICONS:
        icon_path = resource_path(os.path.join(ICONS_DIR, TOOLBAR_ICONS[name]))
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                return icon
    
    # If custom icon failed or doesn't exist, use standard icon
    if name in STANDARD_ICON_MAPPING:
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            style = app.style()
            return style.standardIcon(STANDARD_ICON_MAPPING[name])
    
    # If all else fails, return empty icon
    return QIcon()

def get_multi_kml_button_color():
    """Returns the standard blue color for Multi-KML buttons"""
    return "#0078D7"

def check_icons_availability():
    """
    Check if all defined icons are available and log missing ones.
    Useful for debugging.
    
    Returns:
        dict: A dictionary with status of all icons
    """
    results = {
        "organization_logo": os.path.exists(resource_path(os.path.join(ASSETS_DIR, ORGANIZATION_LOGO))),
        "app_icon": os.path.exists(resource_path(os.path.join(ASSETS_DIR, APP_ICON))),
        "fallback_logo": os.path.exists(resource_path(os.path.join(ASSETS_DIR, FALLBACK_LOGO))),
        "toolbar_icons": {}
    }
    
    # Check all toolbar icons
    for name, file in TOOLBAR_ICONS.items():
        icon_path = resource_path(os.path.join(ICONS_DIR, file))
        results["toolbar_icons"][name] = os.path.exists(icon_path)
    
    return results 