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
    try {
        console.log("JS: Attempting to initialize OpenLayers map...");

        // Switch to Stamen tile source for reliability during this test
        const osmSource = new ol.source.Stamen({ layer: 'toner-lite' });
        // const osmSource = new ol.source.OSM(); // Keep OSM commented out for now

        osmSource.on('tileloadstart', function(event) {
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage('JS: Tile load start: ' + event.tile.src_);
            } else {
                console.log('JS: Tile load start: ' + event.tile.src_);
            }
        });

        osmSource.on('tileloadend', function(event) {
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage('JS: Tile load success: ' + event.tile.src_);
            } else {
                console.log('JS: Tile load success: ' + event.tile.src_);
            }
        });

        osmSource.on('tileloaderror', function(event) {
            // Attempt to get more details from the event or tile, though OpenLayers error events are sometimes minimal
            var errorDetails = 'State: ' + event.tile.getState();
            // Note: `event.error` or similar specific error message property isn't standard in OL tileloaderror
            // We rely on the browser console for more detailed network errors (e.g., CORS, SSL)
            console.error('JS: Tile load error. Tile URL: ' + event.tile.src_ + ', ' + errorDetails);
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage('JS: Tile load error: ' + event.tile.src_ + ', ' + errorDetails);
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
                    source: osmSource
                }),
                vectorLayer
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([0, 0]),
                zoom: 2
            })
        });

        console.log("JS: OpenLayers map object should be initialized.");
        if (webChannel && webChannel.jsEditorReady) { // Check if jsEditorReady exists
             // webChannel.jsEditorReady(); // If you have a corresponding slot in Python
        }

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
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS: loadKmlToMap invoked.");
    }

    if (!map || !vectorSource) {
        console.error("JS Error: Map or vectorSource not initialized before loadKmlToMap.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS KML Load Error: Map or vectorSource not initialized.");
        }
        return;
    }
    if (!kmlString || kmlString.trim() === "") {
        console.warn("JS Warning: KML string is empty or null. Clearing map.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS KML Load Warning: KML string is empty. Clearing map.");
        }
        clearMap();
        return;
    }

    try {
        vectorSource.clear();
        const kmlFormat = new ol.format.KML({
            extractStyles: false
        });

        const features = kmlFormat.readFeatures(kmlString, {
            dataProjection: 'EPSG:4326',
            featureProjection: map.getView().getProjection()
        });

        if (features && features.length > 0) {
            vectorSource.addFeatures(features);
            map.getView().fit(vectorSource.getExtent(), {
                padding: [70, 70, 70, 70],
                duration: 1000,
                maxZoom: 18
            });
            console.log(`JS: Loaded ${features.length} features from KML.`);
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage(`JS: KML Loaded successfully with ${features.length} features.`);
            }
        } else {
            console.warn("JS Warning: No features found in KML string or KML was invalid.");
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage("JS KML Load Warning: No features found in provided KML string.");
            }
        }
    } catch (e) {
        console.error("JS Error loading KML to map:", e.message, e.stack);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS KML Parse Error: " + e.message);
        }
        // alert("Error parsing KML data. Please check the KML file format and console."); // Alert can be intrusive
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
    console.log("JS: Called disableMapEditing() before enabling new interactions.");

    selectInteraction = new ol.interaction.Select({
        wrapX: false, // Important for geometries that cross the dateline
        // style: ... // Optional: style for selected features
    });
    map.addInteraction(selectInteraction);
    console.log("JS: ol.interaction.Select added.");

    modifyInteraction = new ol.interaction.Modify({
        features: selectInteraction.getFeatures(), // Modify only selected features
        deleteCondition: function(event) { // Added deleteCondition
            return ol.events.condition.altKeyOnly(event) && ol.events.condition.singleClick(event);
        }
    });
    map.addInteraction(modifyInteraction);
    console.log("JS: ol.interaction.Modify added with deleteCondition.");

    console.log("Map editing enabled (Select & Modify).");
    if(webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS: Map editing enabled (Select & Modify interactions added with deleteCondition).");
    }
}

function disableMapEditing() {
    console.log("JS: disableMapEditing called.");
    if (!map) {
        console.warn("JS: Map object not found, cannot disable editing.");
        if(webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: Map object not found in disableMapEditing.");
        }
        return;
    }

    var selectRemovedLog = "Select interaction not present or already removed.";
    if (selectInteraction) {
        map.removeInteraction(selectInteraction);
        selectInteraction = null; // Important to dereference
        console.log("JS: ol.interaction.Select removed.");
        selectRemovedLog = "Select interaction removed.";
    } else {
        console.log("JS: ol.interaction.Select was already null or not found.");
    }

    var modifyRemovedLog = "Modify interaction not present or already removed.";
    if (modifyInteraction) {
        map.removeInteraction(modifyInteraction);
        modifyInteraction = null; // Important to dereference
        console.log("JS: ol.interaction.Modify removed.");
        modifyRemovedLog = "Modify interaction removed.";
    } else {
        console.log("JS: ol.interaction.Modify was already null or not found.");
    }
    console.log("Map editing disabled.");
    if(webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage(`JS: Map editing disabled. ${selectRemovedLog} ${modifyRemovedLog}`);
    }
}

function getEditedGeometry() {
    console.log("JS: getEditedGeometry called.");
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS: getEditedGeometry invoked.");
    }

    if (!vectorSource || vectorSource.getFeatures().length === 0) {
        console.warn("JS GetGeom Error: No features available.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS GetGeom Error: No features available in vectorSource.");
        }
        return JSON.stringify(null);
    }

    const feature = vectorSource.getFeatures()[0];
    if (!feature) {
        console.warn("JS GetGeom Error: First feature is undefined.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS GetGeom Error: First feature is undefined.");
        }
        return JSON.stringify(null);
    }

    try {
        const geometry = feature.getGeometry();
        if (!geometry) {
            console.warn("JS GetGeom Error: Geometry is undefined for the feature.");
            if (webChannel && webChannel.jsLogMessage) {
                webChannel.jsLogMessage("JS GetGeom Error: Geometry is undefined for the feature.");
            }
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
        console.log("JS: getEditedGeometry - Extracted and transformed coordinates (before stringify):", finalCoordinates);
        if (webChannel && webChannel.jsLogMessage) {
            // Log the raw coordinates array as a string for Python to see
            webChannel.jsLogMessage("JS: Extracted coordinates (raw): " + JSON.stringify(finalCoordinates));
        }
        return JSON.stringify(finalCoordinates);

    } catch (e) {
        console.error("Error getting/transforming edited geometry:", e);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS ERROR in getEditedGeometry: " + e.message);
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

// Global error handler
window.onerror = function(message, source, lineno, colno, error) {
  if (webChannel && webChannel.jsLogMessage) {
    var errorMessage = "JS Global Error: " + message;
    if (source) errorMessage += " at " + source;
    if (lineno) errorMessage += ":" + lineno;
    if (colno) errorMessage += ":" + colno;
    if (error && error.stack) errorMessage += "\nStack: " + error.stack;
    webChannel.jsLogMessage(errorMessage);
  } else {
    console.error("JS Global Error (webChannel not available):", message, source, lineno, colno, error);
  }
  return false; // Let the default handler run too
};

console.log("kml_editor_map.js loaded with enhanced logging.");
