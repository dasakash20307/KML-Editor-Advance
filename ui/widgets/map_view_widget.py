# File: DilasaKMLTool_v4/ui/widgets/map_view_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QUrl, Slot
import folium
import os
import tempfile
import xml.etree.ElementTree as ET

# Assuming CredentialManager is in core, which is a sibling to ui
from core.credential_manager import CredentialManager

class MapViewWidget(QWidget):
    def __init__(self, credential_manager: CredentialManager, parent=None):
        super().__init__(parent)
        self.credential_manager = credential_manager
        self.web_view = QWebEngineView()

        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)

        self.description_edit = QTextEdit()
        self.description_edit.setReadOnly(True)
        self.description_edit.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; padding: 5px;")
        self.description_edit.setFixedHeight(100)
        layout.addWidget(self.description_edit)

        self.setLayout(layout)

        self.temp_map_file = None
        self.current_map = None # Initialize current_map
        self._initialize_map()

    # TODO: Task 9 - KML Locking Integration for Editing
    # When "Edit" is clicked (likely in a context menu or button not yet created in this widget directly,
    # but this widget might be controlled by an editor widget/dialog):
    # 1. kml_filename = ... (determined from the currently loaded/selected KML)
    # 2. main_window_instance = self.find_main_window() # Helper to get MainWindow, or pass MainWindow instance
    #    (May need to implement find_main_window or ensure MainWindow instance is available via parent or signal)
    # 3. Example for acquiring lock before entering edit mode:
    #    lock_status = main_window_instance.kml_file_lock_manager.acquire_kml_lock(kml_filename, "KML Edit Session")
    # 4. If lock_status is True:
    #    proceed_with_edit_mode() # Enable UI for editing KML features
    # 5. Else if lock_status == "STALE_LOCK_DETECTED":
    #    # Delegate stale lock handling to MainWindow or a shared utility that can show QMessageBox
    #    # e.g., main_window_instance.handle_stale_kml_lock_override_for_edit(kml_filename, callback_on_success=proceed_with_edit_mode)
    #    pass # Placeholder for stale lock handling; likely involves main_window interaction
    # 6. Else (lock_status is False (busy) or "ERROR"):
    #    QMessageBox.warning(self, "Cannot Edit", f"Cannot edit KML '{kml_filename}'. It might be locked by another user/process or an error occurred.")
    #
    # During an active edit session (if KML features are modified):
    # - Periodically call: main_window_instance.kml_file_lock_manager.update_kml_heartbeat(kml_filename)
    #   (e.g., on a timer, or after significant edits)
    #
    # On "Save" action (after editing):
    # - Perform save operation...
    # - Finally, always release the lock:
    #   main_window_instance.kml_file_lock_manager.release_kml_lock(kml_filename)
    #
    # On "Cancel" action (discarding edits):
    # - Finally, always release the lock:
    #   main_window_instance.kml_file_lock_manager.release_kml_lock(kml_filename)


    @staticmethod
    def _parse_kml_data(kml_content_string: str) -> tuple[list[tuple[float, float]] | None, str | None, bool, str | None]:
        """
        Parses KML content string to extract coordinates, description, and type (Point/Polygon).
        Returns: (coordinates, description, is_point, error_message)
        Coordinates are [(lat, lon), ...]. Error_message is None on success.
        """
        try:
            root = ET.fromstring(kml_content_string)
            namespaces = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'gx': 'http://www.google.com/kml/ext/2.2'
            }

            def find_element_ns(parent_el, path_with_prefixes):
                """Helper to find elements using a path with 'kml:' prefixes."""
                element = parent_el.find(path_with_prefixes, namespaces)
                if element is None:
                    path_no_prefixes = path_with_prefixes.replace('kml:', '')
                    if path_no_prefixes != path_with_prefixes:
                        element = parent_el.find(path_no_prefixes)
                return element

            description_text = "No description available"
            desc_el = find_element_ns(root, './/kml:Placemark/kml:description')
            if desc_el is None or desc_el.text is None:
                desc_el = find_element_ns(root, './/kml:Document/kml:description')

            if desc_el is not None and desc_el.text:
                description_text = desc_el.text.strip()

            coords_list_lat_lon = []
            is_point = False

            coords_el = find_element_ns(root, './/kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates')

            if coords_el is None:
                point_tag_el = find_element_ns(root, './/kml:Point')
                if point_tag_el is not None:
                    is_point = True
                    coords_el = find_element_ns(point_tag_el, 'kml:coordinates')

            if coords_el is not None and coords_el.text:
                coordinates_str = coords_el.text.strip()
                raw_coords = coordinates_str.split()
                for coord_pair_str in raw_coords:
                    parts = coord_pair_str.split(',')
                    if len(parts) >= 2:
                        try:
                            lon, lat = float(parts[0]), float(parts[1])
                            coords_list_lat_lon.append((lat, lon))
                        except ValueError:
                            print(f"MapViewWidget._parse_kml_data: Warning: Could not parse coordinate part: {parts}")
                            continue

            return coords_list_lat_lon if coords_list_lat_lon else None, description_text, is_point, None

        except ET.ParseError as e:
            return None, "Error parsing KML.", False, f"XML ParseError: {e}"
        except Exception as e:
            return None, "Unexpected error during KML parsing.", False, f"Unexpected error: {e}"


    def _initialize_map(self, lat=20.5937, lon=78.9629, zoom=5):
        self.current_map = folium.Map(
            location=[lat, lon],
            zoom_start=zoom,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery'
        )
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(self.current_map)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(self.current_map)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Esri Satellite (Default)', overlay=False, control=True
        ).add_to(self.current_map)

        folium.LayerControl().add_to(self.current_map)
        if hasattr(self, 'description_edit'):
            self.description_edit.clear()
            self.description_edit.setText("Map initialized. No KML loaded.")
        self.update_map(self.current_map)

    def update_map(self, folium_map_object):
        self.current_map = folium_map_object
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing old temp map file: {e}")
            self.temp_map_file = None

        try:
            fd, new_temp_file_path = tempfile.mkstemp(suffix=".html", prefix="map_view_")
            os.close(fd)
            self.temp_map_file = new_temp_file_path
            self.current_map.save(self.temp_map_file)
            self.web_view.setUrl(QUrl.fromLocalFile(self.temp_map_file))
        except Exception as e:
            print(f"Error saving or loading map: {e}")
            self.web_view.setHtml("<html><body style='display:flex;justify-content:center;align-items:center;height:100%;font-family:sans-serif;'><h1>Error loading map</h1></body></html>")

    def load_kml_for_display(self, kml_file_path: str):
        MIN_ZOOM_LEVEL = 2 # Absolute minimum zoom for any view

        try:
            with open(kml_file_path, 'r', encoding='utf-8') as f:
                kml_content = f.read()
        except FileNotFoundError:
            print(f"KML file not found: {kml_file_path}")
            self._initialize_map()
            if hasattr(self, 'description_edit'):
                 self.description_edit.setText(f"Error: KML file not found\n{os.path.basename(kml_file_path)}")
            return
        except Exception as e:
            print(f"Error reading KML file {kml_file_path}: {e}")
            self._initialize_map()
            if hasattr(self, 'description_edit'):
                self.description_edit.setText(f"Error reading KML file: {os.path.basename(kml_file_path)}\nDetails: {e}")
            return

        self.current_map = folium.Map( # Initialize new map for this KML
            location=[20.5937, 78.9629],
            zoom_start=5,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            control_scale=True # Ensure scale control is on by default
        )
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(self.current_map)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(self.current_map)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Esri Satellite (Default)', overlay=False, control=True
        ).add_to(self.current_map)

        coords_list_lat_lon, description_text, is_point, error_message = MapViewWidget._parse_kml_data(kml_content)

        if error_message:
            print(f"Error parsing KML content from {kml_file_path}: {error_message}")
            self._initialize_map()
            if hasattr(self, 'description_edit'):
                self.description_edit.setText(f"Error parsing KML: {os.path.basename(kml_file_path)}\nDetails: {error_message}")
            return

        if hasattr(self, 'description_edit'):
             self.description_edit.setText(description_text or "No description available.")
        else:
            print(f"KML Description: {description_text or 'No description available.'}")

        settings = self.credential_manager.get_kml_default_view_settings()
        fill_color = settings.get("kml_fill_color_hex")
        fill_opacity_val = settings.get("kml_fill_opacity_percent") / 100.0
        stroke_color = settings.get("kml_line_color_hex")
        stroke_width_val = settings.get("kml_line_width_px")
        view_mode = settings.get("kml_view_mode")
        zoom_offset = settings.get("kml_zoom_offset", 0)

        if view_mode == "Outline Only":
            fill_opacity_val = 0.0
        elif view_mode == "Fill Only":
            stroke_width_val = 0

        if coords_list_lat_lon:
            if is_point:
                 if len(coords_list_lat_lon) == 1:
                    folium.Marker(
                        location=coords_list_lat_lon[0],
                        tooltip=description_text if description_text and description_text != "No description available" else "KML Point",
                    ).add_to(self.current_map)

                    self.current_map.location = coords_list_lat_lon[0]
                    base_zoom_for_point = 15
                    final_point_zoom = max(MIN_ZOOM_LEVEL, base_zoom_for_point + zoom_offset)
                    self.current_map.zoom_start = final_point_zoom
                    self.current_map.options.update({
                        'zoom': final_point_zoom,
                        'location': coords_list_lat_lon[0],
                        'control_scale': True
                    })
                    if hasattr(self.current_map, '_zoom'):
                        self.current_map._zoom = final_point_zoom
                    print(f"MapViewWidget: Point KML. Base zoom: {base_zoom_for_point}, Offset: {zoom_offset}, Final zoom: {final_point_zoom}, Center: {coords_list_lat_lon[0]}")

            elif len(coords_list_lat_lon) > 2: # A polygon
                folium.Polygon(
                    locations=coords_list_lat_lon,
                    color=stroke_color,
                    weight=stroke_width_val,
                    fill=True,
                    fill_color=fill_color,
                    fill_opacity=fill_opacity_val,
                    tooltip="KML Polygon"
                ).add_to(self.current_map)

                min_lat = min(c[0] for c in coords_list_lat_lon)
                max_lat = max(c[0] for c in coords_list_lat_lon)
                min_lon = min(c[1] for c in coords_list_lat_lon)
                max_lon = max(c[1] for c in coords_list_lat_lon)
                bounds_for_map = [[min_lat, min_lon], [max_lat, max_lon]]

                center_lat = (bounds_for_map[0][0] + bounds_for_map[1][0]) / 2
                center_lon = (bounds_for_map[0][1] + bounds_for_map[1][1]) / 2

                self.current_map.fit_bounds(bounds_for_map)

                base_zoom_after_fit = None
                if hasattr(self.current_map, '_zoom'):
                    base_zoom_after_fit = self.current_map._zoom
                elif hasattr(self.current_map, 'options') and 'zoom' in self.current_map.options:
                    base_zoom_after_fit = self.current_map.options.get('zoom')
                elif hasattr(self.current_map, 'zoom_start'):
                    base_zoom_after_fit = self.current_map.zoom_start

                print(f"MapViewWidget: Polygon KML. Bounds: {bounds_for_map}, Calc. center: ({center_lat}, {center_lon}). Zoom after fit_bounds: {base_zoom_after_fit}")

                if base_zoom_after_fit is not None:
                    final_polygon_zoom = max(MIN_ZOOM_LEVEL, base_zoom_after_fit + zoom_offset)
                    self.current_map.location = [center_lat, center_lon]
                    self.current_map.zoom_start = final_polygon_zoom
                    self.current_map.options.update({
                        'zoom': final_polygon_zoom,
                        'location': [center_lat, center_lon],
                        'control_scale': True
                    })
                    if hasattr(self.current_map, '_zoom'):
                         self.current_map._zoom = final_polygon_zoom
                    print(f"MapViewWidget: Polygon KML. Offset: {zoom_offset}. Final zoom: {final_polygon_zoom}. Center re-asserted.")
                else:
                    print("MapViewWidget: Could not get zoom after fit_bounds. Using calculated center and default zoom_start if offset was also 0, or just fit_bounds result.")
                    self.current_map.location = [center_lat, center_lon] # Ensure center is set
                    self.current_map.options.update({'location': [center_lat, center_lon], 'control_scale': True})

            else:
                if hasattr(self, 'description_edit'): self.description_edit.append("\nNote: Insufficient coordinates for displayable geometry.")
        else:
            if hasattr(self, 'description_edit'): self.description_edit.append("\nNote: No valid coordinate data found in KML.")

        folium.LayerControl().add_to(self.current_map)
        self.update_map(self.current_map)

    def clear_map(self):
        self._initialize_map()

    def cleanup(self):
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing temp map file during cleanup: {e}")
        self.temp_map_file = None
        self.current_map = None
