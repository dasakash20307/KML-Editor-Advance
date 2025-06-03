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
                // webChannel.jsEditorReady("KML Editor JavaScript is ready.");
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
    console.log("Initializing OpenLayers map...");
    vectorSource = new ol.source.Vector();
    vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        style: new ol.style.Style({ // Basic style for KML features
            fill: new ol.style.Fill({
                color: 'rgba(255, 255, 255, 0.2)' // Semi-transparent white fill
            }),
            stroke: new ol.style.Stroke({
                color: '#ffcc33', // Yellow stroke
                width: 3
            }),
            image: new ol.style.Circle({ // Style for points
                radius: 7,
                fill: new ol.style.Fill({
                    color: '#ffcc33'
                })
            })
        })
    });

    const stamenTerrainSource = new ol.source.Stamen({
        layer: 'terrain', // Specify the Stamen layer type
        // Stamen tiles are served over HTTPS, so no crossOrigin:'anonymous' typically needed unless issues persist
    });

    stamenTerrainSource.on('tileloadstart', function(event) {
        // console.log('JS: Stamen Tile load start:', event.tile.src_); // Too verbose for normal operation
    });

    stamenTerrainSource.on('tileloadend', function(event) {
        // console.log('JS: Stamen Tile load end:', event.tile.src_); // Too verbose for normal operation
    });

    stamenTerrainSource.on('tileloaderror', function(event) {
        console.error('JS: Stamen Tile load error:', event.tile.src_);
        if (webChannel && webChannel.jsLogMessage) { // Check if jsLogMessage exists
            webChannel.jsLogMessage("Error: Failed to load Stamen map tile: " + event.tile.src_);
        }
    });

    map = new ol.Map({
        target: 'map', // ID of the div in kml_editor.html
        layers: [
            new ol.layer.Tile({
                source: stamenTerrainSource // Use the new Stamen source
            }),
            vectorLayer // Add the KML vector layer
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([0, 0]), // Default center (lon, lat)
            zoom: 2 // Default zoom
        })
    });

    console.log("OpenLayers map initialized.");
    if (webChannel) {
        // Example: Call a Python method if it exists on the bridge
        // webChannel.jsFunctionFromPython("Map JS Initialized and Ready");
    }
}

function loadKmlToMap(kmlString) {
    console.log("JS: loadKmlToMap called.");
    if (!map || !vectorSource) {
        console.error("Map or vectorSource not initialized yet.");
        return;
    }
    if (!kmlString || kmlString.trim() === "") {
        console.warn("JS: KML string is empty or null. Clearing map.");
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
                maxZoom: 18 // Prevent zooming too close on small features
            });
            console.log(`Loaded ${features.length} features from KML.`);

            // Optional: Extract name/description from the first placemark for Python (if needed)
            // const firstFeatureName = features[0].get('name');
            // const firstFeatureDesc = features[0].get('description');
            // if (webChannel && firstFeatureName) {
            //     webChannel.updatePlacemarkDetails(firstFeatureName, firstFeatureDesc || "");
            // }

        } else {
            console.warn("No features found in KML string or KML was invalid.");
        }
    } catch (e) {
        console.error("Error loading KML to map:", e);
        alert("Error parsing KML data. Please check the KML file format.");
    }
}

function enableMapEditing() {
    console.log("JS: enableMapEditing called.");
    if (!map || !vectorSource || vectorSource.getFeatures().length === 0) {
        console.warn("Cannot enable editing: Map not ready or no features to edit.");
        // Optionally, send a message back to Python or show an alert
        // if (webChannel) webChannel.editingError("No features to edit.");
        return;
    }

    disableMapEditing(); // Remove any existing instances first

    selectInteraction = new ol.interaction.Select({
        wrapX: false, // Important for geometries that cross the dateline
        // style: ... // Optional: style for selected features
    });
    map.addInteraction(selectInteraction);

    modifyInteraction = new ol.interaction.Modify({
        features: selectInteraction.getFeatures(), // Modify only selected features
        // source: vectorSource, // Alternative: modify any feature in the source
    });
    map.addInteraction(modifyInteraction);

    console.log("Map editing enabled (Select & Modify).");
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
}

function getEditedGeometry() {
    console.log("JS: getEditedGeometry called.");
    if (!vectorSource || vectorSource.getFeatures().length === 0) {
        console.warn("No features available to get geometry from.");
        return JSON.stringify(null); // Or an empty GeoJSON structure
    }

    // Assuming we're interested in the first feature (simplification)
    const feature = vectorSource.getFeatures()[0];
    if (!feature) {
        console.warn("First feature is undefined.");
        return JSON.stringify(null);
    }

    try {
        const geometry = feature.getGeometry();
        if (!geometry) {
            console.warn("Geometry is undefined for the feature.");
            return JSON.stringify(null);
        }

        // Clone and transform the geometry to EPSG:4326 (Lon/Lat)
        const transformedGeom = geometry.clone().transform(map.getView().getProjection(), 'EPSG:4326');
        const coordinates = transformedGeom.getCoordinates();

        // Determine geometry type for correct GeoJSON structure
        let geojsonType = transformedGeom.getType(); // e.g., "Polygon", "Point", "LineString"

        // Simplify structure for single Polygon/LineString for now
        // OpenLayers coordinates for Polygon: [[ [lon,lat,alt?], ... ]]
        // OpenLayers coordinates for LineString: [ [lon,lat,alt?], ... ]
        // The Python side expects list of (lon, lat, alt) tuples for add_polygon_to_kml_object's edited_coordinates_list
        // For Polygon, coordinates[0] is the outer ring.
        let finalCoordinates;
        if (geojsonType === 'Polygon' && Array.isArray(coordinates) && Array.isArray(coordinates[0])) {
            finalCoordinates = coordinates[0].map(coord => [coord[0], coord[1], coord[2] || 0.0]); // Ensure 3D for KML
        } else if (geojsonType === 'LineString' && Array.isArray(coordinates)) {
             finalCoordinates = coordinates.map(coord => [coord[0], coord[1], coord[2] || 0.0]);
        } else if (geojsonType === 'Point' && Array.isArray(coordinates)) {
            finalCoordinates = [[coordinates[0], coordinates[1], coordinates[2] || 0.0]]; // Wrap point to look like a path
        }
        else {
            console.warn("Unhandled geometry type for coordinate extraction:", geojsonType);
            return JSON.stringify(null);
        }

        // Return a simplified list of [lon, lat, alt] tuples, as expected by the Python side for `edited_coordinates_list`
        console.log("Extracted and transformed coordinates:", finalCoordinates);
        return JSON.stringify(finalCoordinates);

    } catch (e) {
        console.error("Error getting/transforming edited geometry:", e);
        return JSON.stringify(null);
    }
}

function clearMap() {
    console.log("JS: clearMap called.");
    if (vectorSource) {
        vectorSource.clear();
    }
    if (map) {
        map.getView().setCenter(ol.proj.fromLonLat([0, 0])); // Reset to default view
        map.getView().setZoom(2);
    }
    disableMapEditing(); // Also disable any active editing interactions
    console.log("Map cleared and view reset.");
}

// Example function that could be called from Python via webChannel
// (Requires corresponding Slot in KMLJSBridge if webChannel.pythonFunction is called)
/*
function jsFunctionCalledByPython(message) {
    console.log("JS: jsFunctionCalledByPython received message: " + message);
    alert("Message from Python: " + message);
    if (webChannel) {
        // Example of JS calling a Python slot (if KMLJSBridge has a 'handleJSMessage' slot)
        // webChannel.handleJSMessage("Hello from JavaScript!");
    }
}
*/
console.log("kml_editor_map.js loaded.");
