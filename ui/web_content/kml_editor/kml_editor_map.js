// Global OpenLayers variables
var map;
var vectorSource;
var vectorLayer;
var selectInteraction;
var modifyInteraction;
// webChannel will be populated by the QWebChannel setup
var webChannel;

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded. Setting up QWebChannel.");
    if (typeof QWebChannel !== 'undefined') {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            webChannel = channel.objects.kml_editor_bridge;
            if (webChannel) {
                console.log("QWebChannel bridge 'kml_editor_bridge' connected.");
                initMap(); // Initialize map after channel is ready
                // Notify Python that the JS editor is ready (optional)
                // if (webChannel.jsEditorReady) webChannel.jsEditorReady("KML Editor JavaScript is ready.");
            } else {
                console.error("KML Editor Bridge object (kml_editor_bridge) not found in QWebChannel.");
                alert("Error: Could not connect to Python backend (QWebChannel bridge not found). Map functionality will be limited.");
            }
        });
    } else {
        console.error("QWebChannel is not defined. Ensure qwebchannel.js is loaded correctly.");
        alert("Error: QWebChannel.js not loaded. Map functionality will be disabled.");
    }
});

function initMap() {
    try {
        console.log("JS: Attempting to initialize OpenLayers map...");

        // Configure Esri World Imagery Source
        const esriSource = new ol.source.XYZ({
            url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attributions: 'Tiles &copy; <a href="https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer">ArcGIS</a>',
            maxZoom: 19, // Esri World Imagery typically supports up to zoom level 19
            tileLoadFunction: function(tile, src) { // Optional: Add error logging for Esri tiles
                const image = tile.getImage();
                image.onload = function() {
                    // console.log('JS: Esri Tile load end:', src);
                };
                image.onerror = function() {
                    console.error('JS: Esri Tile load error for URL:', src);
                    if (webChannel && webChannel.jsLogMessage) {
                        webChannel.jsLogMessage("Error: Failed to load Esri map tile: " + src);
                    }
                };
                image.src = src;
            }
        });

        vectorSource = new ol.source.Vector(); // Ensure vectorSource is initialized
        vectorLayer = new ol.layer.Vector({
            source: vectorSource,
            style: new ol.style.Style({ // Basic default style for KML features
                stroke: new ol.style.Stroke({
                    color: 'yellow',
                    width: 3 // Increased width for better visibility
                }),
                fill: new ol.style.Fill({
                    color: 'rgba(255, 255, 0, 0.2)' // Lighter yellow fill
                }),
                image: new ol.style.Circle({ // Style for points
                    radius: 7,
                    fill: new ol.style.Fill({
                        color: '#ffcc33' // Default yellow for points too
                    }),
                    stroke: new ol.style.Stroke({ // Add stroke to points
                        color: 'black',
                        width: 1
                    })
                })
            })
        });

        map = new ol.Map({
            target: 'map',
            layers: [
                new ol.layer.Tile({
                    source: esriSource // Use the new Esri source here
                }),
                vectorLayer
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([0, 0]), // Default center
                zoom: 2 // Default zoom
            })
        });

        console.log("JS: OpenLayers map object should be initialized with Esri Tiles.");
        // if (webChannel && webChannel.jsEditorReady) { // Check if jsEditorReady exists
             // webChannel.jsEditorReady(); // If you have a corresponding slot in Python
        // }

    } catch (e) {
        console.error("JS: CRITICAL ERROR during map initialization:", e.message, e.stack);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("CRITICAL JS ERROR during map initialization: " + e.message);
        }
        // Optionally, display an error message in the map div
        const mapDiv = document.getElementById('map');
        if (mapDiv) {
            mapDiv.innerHTML = '<p style="color:red;text-align:center;padding:20px;">Critical Error: Map could not be initialized. Check console.</p>';
        }
    }
}

function loadKmlToMap(kmlString) {
    console.log("JS: loadKmlToMap called.");
    if (!map || !vectorSource) {
        console.error("Map or vectorSource not initialized yet.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Error: loadKmlToMap called before map/vectorSource initialized.");
        }
        return;
    }
    if (!kmlString || kmlString.trim() === "") {
        console.warn("JS: KML string is empty or null. Clearing map.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: KML string empty, clearing map.");
        }
        clearMap();
        return;
    }

    try {
        vectorSource.clear(); // Clear existing features
        const kmlFormat = new ol.format.KML({
            extractStyles: false // We use a default layer style for now
        });

        // Features are read in EPSG:4326 and transformed to the map's view projection (likely EPSG:3857)
        const features = kmlFormat.readFeatures(kmlString, {
            dataProjection: 'EPSG:4326', // KML coordinates are Lon/Lat
            featureProjection: map.getView().getProjection()
        });

        if (features && features.length > 0) {
            vectorSource.addFeatures(features);
            map.getView().fit(vectorSource.getExtent(), {
                padding: [70, 70, 70, 70], // Increased padding
                duration: 1000,
                maxZoom: 18 // Prevent zooming too close on small features (can be adjusted based on Esri maxZoom)
            });
            console.log(`Loaded ${features.length} features from KML.`);
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage(`JS Info: Loaded ${features.length} features from KML.`);
            }
        } else {
            console.warn("No features found in KML string or KML was invalid.");
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage("JS Warning: No features found in KML string or KML was invalid.");
            }
        }
    } catch (e) {
        console.error("Error loading KML to map:", e);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Error loading KML: " + e.message);
        }
        alert("Error parsing KML data. Please check the KML file format.");
    }
}

function enableMapEditing() {
    console.log("JS: enableMapEditing called.");
    if (!map || !vectorSource || vectorSource.getFeatures().length === 0) {
        console.warn("Cannot enable editing: Map not ready or no features to edit.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: Cannot enable editing - map not ready or no features.");
        }
        return;
    }

    disableMapEditing(); // Remove any existing instances first

    selectInteraction = new ol.interaction.Select({
        wrapX: false,
    });
    map.addInteraction(selectInteraction);

    modifyInteraction = new ol.interaction.Modify({
        features: selectInteraction.getFeatures(),
    });
    map.addInteraction(modifyInteraction);

    console.log("Map editing enabled (Select & Modify).");
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS Info: Map editing enabled.");
    }
}

function disableMapEditing() {
    console.log("JS: disableMapEditing called.");
    if (!map) return;

    if (selectInteraction) {
        map.removeInteraction(selectInteraction);
        selectInteraction = null;
    }
    if (modifyInteraction) {
        map.removeInteraction(modifyInteraction);
        modifyInteraction = null;
    }
    console.log("Map editing disabled.");
     if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS Info: Map editing disabled.");
    }
}

function getEditedGeometry() {
    console.log("JS: getEditedGeometry called.");
    if (!vectorSource || vectorSource.getFeatures().length === 0) {
        console.warn("No features available to get geometry from.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: getEditedGeometry - no features available.");
        }
        return JSON.stringify(null);
    }

    const feature = vectorSource.getFeatures()[0];
    if (!feature) {
        console.warn("First feature is undefined.");
         if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: getEditedGeometry - first feature undefined.");
        }
        return JSON.stringify(null);
    }

    try {
        const geometry = feature.getGeometry();
        if (!geometry) {
            console.warn("Geometry is undefined for the feature.");
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage("JS Warning: getEditedGeometry - geometry undefined for feature.");
            }
            return JSON.stringify(null);
        }

        const transformedGeom = geometry.clone().transform(map.getView().getProjection(), 'EPSG:4326');
        const coordinates = transformedGeom.getCoordinates();
        let geojsonType = transformedGeom.getType();
        let finalCoordinates;

        if (geojsonType === 'Polygon' && Array.isArray(coordinates) && Array.isArray(coordinates[0])) {
            finalCoordinates = coordinates[0].map(coord => [coord[0], coord[1], coord[2] || 0.0]);
        } else if (geojsonType === 'LineString' && Array.isArray(coordinates)) {
             finalCoordinates = coordinates.map(coord => [coord[0], coord[1], coord[2] || 0.0]);
        } else if (geojsonType === 'Point' && Array.isArray(coordinates)) {
            finalCoordinates = [[coordinates[0], coordinates[1], coordinates[2] || 0.0]];
        } else {
            console.warn("Unhandled geometry type for coordinate extraction:", geojsonType);
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage("JS Warning: getEditedGeometry - unhandled geometry type: " + geojsonType);
            }
            return JSON.stringify(null);
        }

        console.log("Extracted and transformed coordinates:", finalCoordinates);
        return JSON.stringify(finalCoordinates);

    } catch (e) {
        console.error("Error getting/transforming edited geometry:", e);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Error: getEditedGeometry - " + e.message);
        }
        return JSON.stringify(null);
    }
}

function clearMap() {
    console.log("JS: clearMap called.");
    if (vectorSource) {
        vectorSource.clear();
    }
    if (map) {
        map.getView().setCenter(ol.proj.fromLonLat([0, 0]));
        map.getView().setZoom(2);
    }
    disableMapEditing();
    console.log("Map cleared and view reset.");
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS Info: Map cleared and view reset.");
    }
}

console.log("kml_editor_map.js loaded (modified for Esri Tiles).");