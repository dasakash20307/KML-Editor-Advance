# File: DilasaKMLTool_v4/ui/widgets/map_view_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtCore import QUrl, Slot, Qt # Added Qt
import folium
import os
import tempfile
import xml.etree.ElementTree as ET

from core.credential_manager import CredentialManager

class MapViewWidget(QWidget):
    DEFAULT_LAT = 20.5937
    DEFAULT_LON = 78.9629
    DEFAULT_ZOOM = 5
    MIN_ZOOM_LEVEL = 2

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
        self.current_folium_map = None # Stores the folium.Map object
        self._current_center = [self.DEFAULT_LAT, self.DEFAULT_LON]
        self._current_zoom = self.DEFAULT_ZOOM
        self._current_features = [] # Store features to re-add to map

        self._render_and_update_map() # Initial map rendering
        self.description_edit.setText("Map initialized. No KML loaded.")


    @staticmethod
    def _parse_kml_data(kml_content_string: str) -> tuple[list[tuple[float, float]] | None, str | None, bool, str | None]:
        try:
            root = ET.fromstring(kml_content_string)
            namespaces = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'gx': 'http://www.google.com/kml/ext/2.2'
            }

            def find_element_ns(parent_el, path_with_prefixes):
                element = parent_el.find(path_with_prefixes, namespaces)
                if element is None:
                    # Try without namespace prefix as a fallback
                    path_no_prefixes = path_with_prefixes.replace('kml:', '').replace('gx:', '')
                    if path_no_prefixes != path_with_prefixes:
                         element = parent_el.find(path_no_prefixes)
                return element

            description_text = "No description available"
            coords_list_lat_lon = None
            is_point = False
            found_geometry = False

            # Find the first Placemark and its description
            first_placemark = find_element_ns(root, './/kml:Placemark')
            if first_placemark is not None:
                desc_el = find_element_ns(first_placemark, 'kml:description')
                if desc_el is not None and desc_el.text:
                    description_text = desc_el.text.strip()
                else:
                     # Also check description directly under Document if no Placemark description
                     doc_desc_el = find_element_ns(root, './/kml:Document/kml:description')
                     if doc_desc_el is not None and doc_desc_el.text:
                         description_text = doc_desc_el.text.strip()


                # Find geometry within the first Placemark
                geometry_elements = first_placemark.findall('.//kml:Polygon', namespaces) + \
                                    first_placemark.findall('.//kml:LineString', namespaces) + \
                                    first_placemark.findall('.//kml:Point', namespaces) + \
                                    first_placemark.findall('.//kml:MultiGeometry', namespaces)

                for geom_el in geometry_elements:
                    if found_geometry: break # Only process the first geometry found

                    if geom_el.tag.endswith('Polygon'):
                        coords_el = find_element_ns(geom_el, 'kml:outerBoundaryIs/kml:LinearRing/kml:coordinates')
                        if coords_el is not None and coords_el.text:
                            coords_list_lat_lon = []
                            raw_coords = coords_el.text.strip().split()
                            for coord_pair_str in raw_coords:
                                parts = coord_pair_str.split(',')
                                if len(parts) >= 2:
                                    try:
                                        # KML coordinates are typically lon, lat, altitude
                                        lon, lat = float(parts[0]), float(parts[1])
                                        coords_list_lat_lon.append((lat, lon)) # Store as (lat, lon) for Folium
                                    except ValueError:
                                        print(f"MapViewWidget._parse_kml_data: Warning: Could not parse coordinate part: {parts}")
                                        continue
                            if coords_list_lat_lon: found_geometry = True

                    elif geom_el.tag.endswith('Point'):
                         coords_el = find_element_ns(geom_el, 'kml:coordinates')
                         if coords_el is not None and coords_el.text:
                             raw_coords = coords_el.text.strip().split()
                             if raw_coords:
                                 parts = raw_coords[0].split(',')
                                 if len(parts) >= 2:
                                     try:
                                         lon, lat = float(parts[0]), float(parts[1])
                                         coords_list_lat_lon = [(lat, lon)] # Store as (lat, lon)
                                         is_point = True
                                         found_geometry = True
                                     except ValueError:
                                         print(f"MapViewWidget._parse_kml_data: Warning: Could not parse point coordinate: {parts}")

                    elif geom_el.tag.endswith('LineString'):
                         # Currently not handling LineString for display, but could add later
                         pass # Or parse coordinates if needed

                    elif geom_el.tag.endswith('MultiGeometry'):
                        # Iterate through children of MultiGeometry
                        multi_geom_children = geom_el.findall('.//kml:Polygon', namespaces) + \
                                              geom_el.findall('.//kml:LineString', namespaces) + \
                                              geom_el.findall('.//kml:Point', namespaces)
                        for child_geom in multi_geom_children:
                             if found_geometry: break # Only process the first geometry found within MultiGeometry

                             if child_geom.tag.endswith('Polygon'):
                                 coords_el = find_element_ns(child_geom, 'kml:outerBoundaryIs/kml:LinearRing/kml:coordinates')
                                 if coords_el is not None and coords_el.text:
                                     coords_list_lat_lon = []
                                     raw_coords = coords_el.text.strip().split()
                                     for coord_pair_str in raw_coords:
                                         parts = coord_pair_str.split(',')
                                         if len(parts) >= 2:
                                             try:
                                                 lon, lat = float(parts[0]), float(parts[1])
                                                 coords_list_lat_lon.append((lat, lon))
                                             except ValueError:
                                                 print(f"MapViewWidget._parse_kml_data: Warning: Could not parse coordinate part in MultiGeometry: {parts}")
                                                 continue
                                     if coords_list_lat_lon: found_geometry = True

                             elif child_geom.tag.endswith('Point'):
                                 coords_el = find_element_ns(child_geom, 'kml:coordinates')
                                 if coords_el is not None and coords_el.text:
                                     raw_coords = coords_el.text.strip().split()
                                     if raw_coords:
                                         parts = raw_coords[0].split(',')
                                         if len(parts) >= 2:
                                             try:
                                                 lon, lat = float(parts[0]), float(parts[1])
                                                 coords_list_lat_lon = [(lat, lon)]
                                                 is_point = True
                                                 found_geometry = True
                                             except ValueError:
                                                 print(f"MapViewWidget._parse_kml_data: Warning: Could not parse point coordinate in MultiGeometry: {parts}")

                             # Add other geometry types within MultiGeometry if needed

            return coords_list_lat_lon if coords_list_lat_lon else None, description_text, is_point, None

        except ET.ParseError as e:
            return None, "Error parsing KML.", False, f"XML ParseError: {e}"
        except Exception as e:
            return None, "Unexpected error during KML parsing.", False, f"Unexpected error: {e}"

    def _render_and_update_map(self, bounds=None, center=None, zoom=None):
        """
        Creates a new Folium map, adds current features, adjusts view based on parameters,
        and updates the web view.
        """
        zoom_offset = self.credential_manager.get_kml_default_view_settings().get("kml_zoom_offset", 0)

        # Default map initialization parameters
        map_location = self._current_center
        map_zoom = self._current_zoom

        # If specific center and zoom are provided (typically for points)
        if center is not None and zoom is not None:
            map_location = center
            # Apply zoom offset for points (subtract to zoom out)
            map_zoom = max(self.MIN_ZOOM_LEVEL, zoom - zoom_offset)

        self.current_folium_map = folium.Map(
            location=map_location,
            zoom_start=map_zoom,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            control_scale=True
        )
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(self.current_folium_map)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(self.current_folium_map)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Esri Satellite (Default)', overlay=False, control=True
        ).add_to(self.current_folium_map)

        for feature_item in self._current_features: # Add current features
            feature_item.add_to(self.current_folium_map)

        folium.LayerControl().add_to(self.current_folium_map)

        # If bounds are provided (typically for polygons), fit the map to these bounds
        if bounds is not None:
            self.current_folium_map.fit_bounds(bounds)
            # The fit_bounds() method adjusts the map's view (location and zoom) internally.
            # The zoom_offset is handled for explicit center/zoom cases (e.g., points).
            # Applying a similar offset after fit_bounds for polygons would require
            # a more complex approach if Folium doesn't expose a direct way to modify
            # zoom post-fit_bounds without re-initializing the map.
            # For now, we rely on fit_bounds() to set the optimal view for polygons.

        self._update_webview_with_map(self.current_folium_map)

    def _update_webview_with_map(self, folium_map_object):
        """Saves the map to a temporary HTML and loads it in the QWebEngineView."""
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing old temp map file: {e}")
            self.temp_map_file = None
        try:
            fd, new_temp_file_path = tempfile.mkstemp(suffix=".html", prefix="map_view_")
            os.close(fd)
            self.temp_map_file = new_temp_file_path
            folium_map_object.save(self.temp_map_file)
            self.web_view.setUrl(QUrl.fromLocalFile(self.temp_map_file))
        except Exception as e:
            print(f"Error saving or loading map: {e}")
            self.web_view.setHtml("<html><body style='display:flex;justify-content:center;align-items:center;height:100%;font-family:sans-serif;'><h1>Error loading map</h1></body></html>")

    def load_kml_for_display(self, kml_file_path: str):
        self.description_edit.clear() # Clear previous description
        try:
            with open(kml_file_path, 'r', encoding='utf-8') as f:
                kml_content = f.read()
        except FileNotFoundError:
            self.log_message_callback(f"KML file not found: {kml_file_path}", "error") # Assuming log_message_callback exists if this class is used by MainWindow
            self.clear_map() # Reset to default map
            self.description_edit.setText(f"Error: KML file not found\n{os.path.basename(kml_file_path)}")
            return
        except Exception as e:
            self.log_message_callback(f"Error reading KML file {kml_file_path}: {e}", "error")
            self.clear_map()
            self.description_edit.setText(f"Error reading KML file: {os.path.basename(kml_file_path)}\nDetails: {e}")
            return

        coords_list_lat_lon, description_text, is_point, error_message = MapViewWidget._parse_kml_data(kml_content)

        if error_message:
            self.log_message_callback(f"Error parsing KML content from {kml_file_path}: {error_message}", "error")
            self.clear_map()
            self.description_edit.setText(f"Error parsing KML: {os.path.basename(kml_file_path)}\nDetails: {error_message}")
            return

        self.description_edit.setText(description_text or "No description available.")
        self._current_features = [] # Clear previous features

        settings = self.credential_manager.get_kml_default_view_settings()
        fill_color = settings.get("kml_fill_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_color_hex"])
        
        # Fix for line 222: Provide default for get()
        fill_opacity_percent = settings.get("kml_fill_opacity_percent", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_opacity_percent"])
        fill_opacity_val = fill_opacity_percent / 100.0
        
        stroke_color = settings.get("kml_line_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_color_hex"])
        stroke_width_val = settings.get("kml_line_width_px", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_width_px"])
        view_mode = settings.get("kml_view_mode", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_view_mode"])
        zoom_offset = settings.get("kml_zoom_offset", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_zoom_offset"])

        if view_mode == "Outline Only": fill_opacity_val = 0.0
        elif view_mode == "Fill Only": stroke_width_val = 0

        new_center = None
        new_zoom = None
        bounds_for_map = None

        if coords_list_lat_lon:
            if is_point:
                if len(coords_list_lat_lon) == 1:
                    point_feature = folium.Marker(
                        location=coords_list_lat_lon[0],
                        tooltip=description_text if description_text and description_text != "No description available" else "KML Point",
                    )
                    self._current_features.append(point_feature)
                    new_center = coords_list_lat_lon[0]
                    base_zoom_for_point = 15 # Define a base zoom level for points
                    new_zoom = max(self.MIN_ZOOM_LEVEL, base_zoom_for_point - zoom_offset) # Subtract offset
            elif len(coords_list_lat_lon) > 2: # Polygon
                polygon_feature = folium.Polygon(
                    locations=coords_list_lat_lon, color=stroke_color, weight=stroke_width_val,
                    fill=True, fill_color=fill_color, fill_opacity=fill_opacity_val,
                    tooltip="KML Polygon"
                )
                self._current_features.append(polygon_feature)
                
                min_lat = min(c[0] for c in coords_list_lat_lon)
                max_lat = max(c[0] for c in coords_list_lat_lon)
                min_lon = min(c[1] for c in coords_list_lat_lon)
                max_lon = max(c[1] for c in coords_list_lat_lon)
                bounds_for_map = [[min_lat, min_lon], [max_lat, max_lon]]
                # Folium's fit_bounds will calculate center and zoom. We'll apply offset later.
        else:
            self.description_edit.append("\nNote: No valid coordinate data found to display on map.")

        # After parsing and adding features, render the map and apply bounds or center/zoom
        if bounds_for_map:
            self._render_and_update_map(bounds=bounds_for_map)
        elif new_center and new_zoom: # Handle point case explicitly
             self._render_and_update_map(center=new_center, zoom=new_zoom)
        else: # No specific geometry to focus on, use defaults
            self._render_and_update_map()


    def display_polygon(self, lat_lon_coords: list[tuple[float,float]], center_coord: tuple[float,float]):
        """Displays a single polygon, usually not from KML but from direct interaction."""
        self._current_features = [] # Clear other KML features

        settings = self.credential_manager.get_kml_default_view_settings()
        fill_color = settings.get("kml_fill_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_fill_color_hex"])
        fill_opacity_percent = settings.get("kml_fill_opacity_percent", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_opacity_percent"]) # Corrected key
        fill_opacity_val = fill_opacity_percent / 100.0
        stroke_color = settings.get("kml_line_color_hex", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_color_hex"])
        stroke_width_val = settings.get("kml_line_width_px", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_line_width_px"])
        view_mode = settings.get("kml_view_mode", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_view_mode"])
        zoom_offset = settings.get("kml_zoom_offset", CredentialManager.DEFAULT_KML_VIEW_SETTINGS["kml_zoom_offset"])


        if view_mode == "Outline Only": fill_opacity_val = 0.0
        elif view_mode == "Fill Only": stroke_width_val = 0

        if lat_lon_coords and len(lat_lon_coords) > 2:
            polygon = folium.Polygon(
                locations=lat_lon_coords,
                color=stroke_color,
                weight=stroke_width_val,
                fill=True,
                fill_color=fill_color,
                fill_opacity=fill_opacity_val,
                tooltip="Selected Polygon"
            )
            self._current_features.append(polygon)

            # Determine bounds
            min_lat = min(c[0] for c in lat_lon_coords)
            max_lat = max(c[0] for c in lat_lon_coords)
            min_lon = min(c[1] for c in lat_lon_coords)
            max_lon = max(c[1] for c in lat_lon_coords)
            bounds = [[min_lat, min_lon], [max_lat, max_lon]]

            self.description_edit.setText("Displaying selected polygon from table.")

            # Render the map with features and adjust view using bounds
            self._render_and_update_map(bounds=bounds)

            # Note: Applying zoom_offset after fit_bounds might require JS injection or recalculation.
            # For now, relying on fit_bounds to get the correct view.

        else:
            self.description_edit.setText("Cannot display polygon: insufficient coordinates.")
            self.clear_map() # Clear if polygon is invalid
            return

    def clear_map(self):
        self._current_center = [self.DEFAULT_LAT, self.DEFAULT_LON]
        self._current_zoom = self.DEFAULT_ZOOM
        self._current_features = []
        self.description_edit.setText("Map cleared. No KML loaded.")
        self._render_and_update_map()

    def cleanup(self):
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing temp map file during cleanup: {e}")
        self.temp_map_file = None
        self.current_folium_map = None
        # Stop web_view if necessary, though usually handled by QWidget destruction
        # self.web_view.stop()
        # self.web_view.setHtml("") # Clear content
    
    # Dummy log_message_callback if this widget is run standalone
    def log_message_callback(self, message, level="info"):
        print(f"MapViewWidget_LOG [{level.upper()}]: {message}")
