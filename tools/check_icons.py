#!/usr/bin/env python3
"""
Icon Checker Tool

This script checks if all the required icons are available in the appropriate directories
and generates a report. It helps diagnose missing or incorrect icon files.

Usage:
    python tools/check_icons.py
"""

import os
import sys
import json
from pathlib import Path

# Add the project root directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.icons import check_icons_availability
from core.utils import resource_path

def print_colored(text, color_code):
    """Print colored text"""
    print(f"\033[{color_code}m{text}\033[0m")

def print_success(text):
    """Print success message in green"""
    print_colored(text, "32")

def print_error(text):
    """Print error message in red"""
    print_colored(text, "31")

def print_warning(text):
    """Print warning message in yellow"""
    print_colored(text, "33")

def print_info(text):
    """Print info message in blue"""
    print_colored(text, "34")

def main():
    """Main function to check icons and generate report"""
    print_info("=== KML Editor Icon Checker ===")
    print_info("Checking if all required icons are available...")
    print()

    # Get icon availability report
    report = check_icons_availability()
    
    # Check organization logo
    if report["organization_logo"]:
        logo_path = resource_path("assets/dilasa_logo.jpg")
        print_success(f"✓ Organization logo found: {logo_path}")
    else:
        print_error(f"✗ Organization logo missing: assets/dilasa_logo.jpg")
        print_warning("  The application will use fallback logo or standard icon.")
    
    # Check app icon
    if report["app_icon"]:
        app_icon_path = resource_path("assets/app_icon.ico")
        print_success(f"✓ Application icon found: {app_icon_path}")
    else:
        print_error(f"✗ Application icon missing: assets/app_icon.ico")
        print_warning("  The application will use fallback icon.")
    
    # Check fallback logo
    if report["fallback_logo"]:
        fallback_path = resource_path("assets/logo_placeholder.png")
        print_success(f"✓ Fallback logo found: {fallback_path}")
    else:
        print_error(f"✗ Fallback logo missing: assets/logo_placeholder.png")
        print_warning("  The application will use standard computer icon as fallback.")
    
    # Check toolbar icons
    print()
    print_info("Checking toolbar icons:")
    
    icons_dir = os.path.join("assets", "icons")
    all_toolbar_present = True
    
    for name, present in report["toolbar_icons"].items():
        icon_path = os.path.join(icons_dir, name + ".png")
        if present:
            print_success(f"✓ {name}: Found")
        else:
            all_toolbar_present = False
            print_error(f"✗ {name}: Missing - will use standard icon fallback")
    
    print()
    if all_toolbar_present:
        print_success("All toolbar icons are present!")
    else:
        print_warning("Some toolbar icons are missing. The application will use standard icons as fallbacks.")
        print_info("To add missing icons, place them in the assets/icons directory with the appropriate names.")
    
    # Create icons directory if it doesn't exist
    icons_dir_full = resource_path(icons_dir)
    if not os.path.exists(icons_dir_full):
        os.makedirs(icons_dir_full, exist_ok=True)
        print()
        print_info(f"Created icons directory: {icons_dir_full}")
    
    print()
    print_info("Icon check complete!")

if __name__ == "__main__":
    main() 