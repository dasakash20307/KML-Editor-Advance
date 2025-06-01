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
                # ElementTree's find expects {namespace}tag format if no prefix is used in path,
                # or prefix:tag if namespaces map is provided.
                # This helper assumes path_with_prefixes is like './/kml:Placemark/kml:description'
                element = parent_el.find(path_with_prefixes, namespaces)
                if element is None:
                    # Fallback for KMLs that might not use prefixes AND don't declare a default namespace
                    # or if the path was accidentally passed without prefixes.
                    # This is less common for standard KML.
                    # We remove "kml:" prefixes for this fallback.
                    path_no_prefixes = path_with_prefixes.replace('kml:', '')
                    if path_no_prefixes != path_with_prefixes: # only try if modification happened
                        element = parent_el.find(path_no_prefixes)
                return element

            description_text = "No description available" # Removed trailing period
            # Paths should now include the 'kml:' prefix for tags
            desc_el = find_element_ns(root, './/kml:Placemark/kml:description')
            if desc_el is None or desc_el.text is None:
                desc_el = find_element_ns(root, './/kml:Document/kml:description')

            if desc_el is not None and desc_el.text:
                description_text = desc_el.text.strip()

            coords_list_lat_lon = []
            is_point = False

            # Try to find Polygon coordinates first
            coords_el = find_element_ns(root, './/kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates')

            if coords_el is None: # No Polygon coordinates found, check for Point
                point_tag_el = find_element_ns(root, './/kml:Point') # Check for the Point tag itself
                if point_tag_el is not None:
                    is_point = True # A Point structure exists
                    # Now try to get coordinates from within this Point
                    coords_el = find_element_ns(point_tag_el, 'kml:coordinates')
                    # If find_element_ns used './/' internally, it might find coords from another point if not careful.
                    # Assuming find_element_ns when given a parent_el searches within it.
                    # Corrected: find_element_ns should search relative to point_tag_el if path is not .//
                    # The path 'kml:coordinates' is relative.

            if coords_el is not None and coords_el.text:
                coordinates_str = coords_el.text.strip()
                raw_coords = coordinates_str.split()
                for coord_pair_str in raw_coords:
                    parts = coord_pair_str.split(',')
                    if len(parts) >= 2: # lon,lat[,alt]
                        try:
                            lon, lat = float(parts[0]), float(parts[1])
                            coords_list_lat_lon.append((lat, lon)) # Folium: (lat, lon)
                        except ValueError:
                            # Could log this if a logger was passed in
                            print(f"MapViewWidget._parse_kml_data: Warning: Could not parse coordinate part: {parts}")
                            continue

            return coords_list_lat_lon if coords_list_lat_lon else None, description_text, is_point, None

        except ET.ParseError as e:
            return None, "Error parsing KML.", False, f"XML ParseError: {e}"
        except Exception as e: # Catch any other unexpected error during parsing
            return None, "Unexpected error during KML parsing.", False, f"Unexpected error: {e}"


    def _initialize_map(self, lat=20.5937, lon=78.9629, zoom=5):
        """Initializes the map with Esri Satellite as the default base layer and clears description."""
        # Default to Esri Satellite
        self.current_map = folium.Map(
            location=[lat, lon],
            zoom_start=zoom,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery' # Attribution for Esri
        )

        # Add other base layers for selection
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(self.current_map)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(self.current_map)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Esri Satellite (Default)',
            overlay=False,
            control=True
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
            self.current_map.save(self.temp_map_file) # Save the current_map
            self.web_view.setUrl(QUrl.fromLocalFile(self.temp_map_file))
        except Exception as e:
            print(f"Error saving or loading map: {e}")
            self.web_view.setHtml("<html><body style='display:flex;justify-content:center;align-items:center;height:100%;font-family:sans-serif;'><h1>Error loading map</h1></body></html>")

    # def display_polygon(self, polygon_coords_lat_lon, centroid_lat_lon=None, zoom_level=18):
    #     # This method's functionality will be largely replaced by load_kml_for_display
    #     # Keeping it commented out for now.
    #     if not polygon_coords_lat_lon:
    #         self._initialize_map(); return
    #     center_loc = centroid_lat_lon if centroid_lat_lon else polygon_coords_lat_lon[0]
    #     m = folium.Map(
    #         location=center_loc,
    #         zoom_start=zoom_level,
    #         tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    #         attr='Esri World Imagery',
    #         name='Satellite View (Default)'
    #     )
    #     folium.TileLayer('openstreetmap', name='Street Map').add_to(m)
    #     folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
    #     folium.TileLayer(
    #         tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    #         attr='Esri',
    #         name='Satellite View (Default)',
    #         overlay=False,
    #         control=True
    #     ).add_to(m)
    #     folium.Polygon(
    #         locations=polygon_coords_lat_lon,
    #         color="blue", weight=3, fill=True, fill_color="blue", fill_opacity=0.1,
    #         tooltip="Selected Polygon"
    #     ).add_to(m)
    #     if center_loc:
    #         folium.Marker(location=center_loc, tooltip="Polygon Area").add_to(m)
    #     folium.LayerControl().add_to(m)
    #     self.update_map(m)

    def load_kml_for_display(self, kml_file_path: str):
        """
        Loads a KML file, extracts polygon coordinates and description,
        and displays them on the map.
        """
        try:
            with open(kml_file_path, 'r', encoding='utf-8') as f:
                kml_content = f.read()
        except FileNotFoundError:
            print(f"KML file not found: {kml_file_path}")
            self._initialize_map()
            self.description_edit.setText(f"Error: KML file not found\n{os.path.basename(kml_file_path)}")
            return
        except Exception as e: # Catch other file reading errors
            print(f"Error reading KML file {kml_file_path}: {e}")
            self._initialize_map()
            self.description_edit.setText(f"Error reading KML file: {os.path.basename(kml_file_path)}\nDetails: {e}")
            return

        # Initialize a new map for fresh display
        self.current_map = folium.Map(
            location=[20.5937, 78.9629], # Default India center
            zoom_start=5,
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery'
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
            self._initialize_map() # Reset map to default state on parsing error
            if hasattr(self, 'description_edit'): # Ensure description_edit exists
                self.description_edit.setText(f"Error parsing KML: {os.path.basename(kml_file_path)}\nDetails: {error_message}")
            return

        if hasattr(self, 'description_edit'):
             self.description_edit.setText(description_text or "No description available.")
        else: # Fallback if description_edit somehow doesn't exist
            print(f"KML Description: {description_text or 'No description available.'}")


        # Fetch KML view settings
        # Fallback to CredentialManager defaults if any key is missing (get_kml_default_view_settings handles this)
        settings = self.credential_manager.get_kml_default_view_settings()

        fill_color = settings.get("kml_fill_color_hex")
        # Convert opacity from percent (0-100) to float (0.0-1.0)
        fill_opacity_val = settings.get("kml_fill_opacity_percent") / 100.0
        stroke_color = settings.get("kml_line_color_hex")
        stroke_width_val = settings.get("kml_line_width_px")
        view_mode = settings.get("kml_view_mode")
        zoom_offset = settings.get("kml_zoom_offset")

        # Apply view mode adjustments
        if view_mode == "Outline Only":
            fill_opacity_val = 0.0
        elif view_mode == "Fill Only":
            stroke_width_val = 0 # Effectively makes the line invisible

        if coords_list_lat_lon:
            if is_point:
                 if len(coords_list_lat_lon) == 1:
                    # For Markers, color customization is more complex (e.g. custom icon).
                    # For now, use default marker style or a simple color if easily doable.
                    # Folium markers use icons, so direct color application like Polygons isn't straightforward.
                    # We can use a generic colored icon or a specific one if available.
                    # For simplicity, we'll use the stroke_color for a basic marker color hint if possible,
                    # but this usually means creating a custom icon.
                    # Default marker:
                    folium.Marker(
                        location=coords_list_lat_lon[0],
                        tooltip=description_text if description_text and description_text != "No description available" else "KML Point",
                        # Example: trying to use a colored icon (requires more setup for specific colors)
                        # icon=folium.Icon(color=stroke_color if folium.Icon.is_valid_color(stroke_color) else 'blue')
                        # For now, let's stick to default marker appearance.
                    ).add_to(self.current_map)
                    self.current_map.location = coords_list_lat_lon[0]
                    self.current_map.zoom_start = 15 # Default zoom for a point
                    # Apply zoom_offset for points as well
                    current_point_zoom = self.current_map.zoom_start # Start with the default for point
                    new_point_zoom = max(1, current_point_zoom + zoom_offset)
                    self.current_map.options['zoom'] = new_point_zoom
                    self.current_map.zoom_start = new_point_zoom
                    if hasattr(self.current_map, '_zoom'):
                        self.current_map._zoom = new_point_zoom


            elif len(coords_list_lat_lon) > 2: # A polygon
                folium.Polygon(
                    locations=coords_list_lat_lon,
                    color=stroke_color,
                    weight=stroke_width_val,
                    fill=True, # Fill is true, opacity controls visibility
                    fill_color=fill_color,
                    fill_opacity=fill_opacity_val,
                    tooltip="KML Polygon" # Could use description_text here too
                ).add_to(self.current_map)

                min_lat = min(c[0] for c in coords_list_lat_lon)
                max_lat = max(c[0] for c in coords_list_lat_lon)
                min_lon = min(c[1] for c in coords_list_lat_lon)
                max_lon = max(c[1] for c in coords_list_lat_lon)
                bounds_for_map = [[min_lat, min_lon], [max_lat, max_lon]]
                self.current_map.fit_bounds(bounds_for_map)

                MIN_ZOOM_LEVEL = 2 # Absolute minimum zoom level for the map

                base_zoom_after_fit = None
                if hasattr(self.current_map, 'options') and 'zoom' in self.current_map.options:
                    base_zoom_after_fit = self.current_map.options['zoom']
                elif hasattr(self.current_map, '_zoom'):
                    base_zoom_after_fit = self.current_map._zoom
                elif hasattr(self.current_map, 'zoom_start'):
                    base_zoom_after_fit = self.current_map.zoom_start # Less ideal but a fallback

                if base_zoom_after_fit is not None:
                    # Apply the zoom_offset from settings
                    effective_zoom = max(MIN_ZOOM_LEVEL, base_zoom_after_fit + zoom_offset)
                    self.current_map.options['zoom'] = effective_zoom
                    self.current_map.zoom_start = effective_zoom
                    if hasattr(self.current_map, '_zoom'):
                        self.current_map._zoom = effective_zoom
                    print(f"MapViewWidget: Original zoom after fit_bounds: {base_zoom_after_fit}. Offset: {zoom_offset}. Final zoom: {effective_zoom}")
                else:
                    print("MapViewWidget: Could not determine base zoom after fit_bounds to apply offset.")

            else: # Not a point and not enough coords for a polygon
                if hasattr(self, 'description_edit'): self.description_edit.append("\nNote: Insufficient coordinates for displayable geometry.")
        else:
            if hasattr(self, 'description_edit'): self.description_edit.append("\nNote: No valid coordinate data found in KML.")

        folium.LayerControl().add_to(self.current_map)
        self.update_map(self.current_map)


    def clear_map(self):
        self._initialize_map() # This already handles clearing description via _initialize_map

    def cleanup(self):
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing temp map file during cleanup: {e}")
        self.temp_map_file = None
        self.current_map = None
