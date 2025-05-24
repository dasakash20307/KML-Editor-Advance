# File: DilasaKMLTool_v4/ui/widgets/map_view_widget.py
# ----------------------------------------------------------------------
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings 
from PySide6.QtCore import QUrl, Slot 
import folium
import os
import tempfile 

class MapViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()
        
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        self.setLayout(layout)
        
        self.temp_map_file = None
        self._initialize_map()

    def _initialize_map(self, lat=20.5937, lon=78.9629, zoom=5): 
        """Initializes the map with Esri Satellite as the default base layer."""
        # Default to Esri Satellite
        m = folium.Map(
            location=[lat, lon], 
            zoom_start=zoom, 
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery' # Attribution for Esri
        )
        
        # Add other base layers for selection
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(m)
        # The Esri layer is already the base, but we can add it to LayerControl explicitly if needed or for consistency
        # If we want it to appear in LayerControl with a specific name, add it again (it won't duplicate the base map itself)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Esri Satellite (Default)', # Name for LayerControl
            overlay=False, # Base layer
            control=True # Show in LayerControl
        ).add_to(m)

        folium.LayerControl().add_to(m)
        self.update_map(m)

    def update_map(self, folium_map_object):
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


    def display_polygon(self, polygon_coords_lat_lon, centroid_lat_lon=None, zoom_level=18):
        if not polygon_coords_lat_lon:
            self._initialize_map(); return

        center_loc = centroid_lat_lon if centroid_lat_lon else polygon_coords_lat_lon[0]
        
        # Default to Esri Satellite
        m = folium.Map(
            location=center_loc, 
            zoom_start=zoom_level, 
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Satellite View (Default)'
        )

        # Add other base layers for selection
        folium.TileLayer('openstreetmap', name='Street Map').add_to(m)
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        # Explicitly add Esri Satellite to LayerControl if not already covered by default `tiles` in control
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satellite View (Default)', # Name for LayerControl
            overlay=False,
            control=True
        ).add_to(m)
        
        folium.Polygon(
            locations=polygon_coords_lat_lon,
            color="blue", weight=3, fill=True, fill_color="blue", fill_opacity=0.1,
            tooltip="Selected Polygon"
        ).add_to(m)
        
        if center_loc:
            folium.Marker(location=center_loc, tooltip="Polygon Area").add_to(m)

        folium.LayerControl().add_to(m)
        self.update_map(m)

    def clear_map(self):
        self._initialize_map()

    def cleanup(self):
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try: os.remove(self.temp_map_file)
            except OSError as e: print(f"Error removing temp map file during cleanup: {e}")
        self.temp_map_file = None

