// Global OpenLayers variables
var map;
var vectorSource;
var vectorLayer;
var selectInteraction;
var modifyInteraction;
var webChannel;
var esriLayer;
var osmLayer;

// Default map constraints (can be updated from Python)
var mapConstraints = {
    maxZoom: 18, // Default max zoom
    initialZoom: 2,
    kmlFillColor: 'rgba(255, 255, 0, 0.2)',
    kmlStrokeColor: 'yellow',
    kmlStrokeWidth: 3
};

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM Content Loaded. Setting up QWebChannel.");
    if (typeof QWebChannel !== 'undefined') {
        new QWebChannel(qt.webChannelTransport, function (channel) {
            webChannel = channel.objects.kml_editor_bridge;
            if (webChannel) {
                console.log("QWebChannel bridge 'kml_editor_bridge' connected.");
                initMap(); // Initialize map after channel is ready
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
            attributions: 'Tiles © Esri',
            maxZoom: 19,
            crossOrigin: 'anonymous'
        });

        // Configure OpenStreetMap Source
        const osmSource = new ol.source.OSM({
            crossOrigin: 'anonymous'
        });

        esriLayer = new ol.layer.Tile({
            source: esriSource,
            visible: true
        });

        osmLayer = new ol.layer.Tile({
            source: osmSource,
            visible: false
        });

        vectorSource = new ol.source.Vector();
        vectorLayer = new ol.layer.Vector({
            source: vectorSource,
            style: new ol.style.Style({ 
                stroke: new ol.style.Stroke({
                    color: mapConstraints.kmlStrokeColor,
                    width: mapConstraints.kmlStrokeWidth
                }),
                fill: new ol.style.Fill({
                    color: mapConstraints.kmlFillColor
                }),
                image: new ol.style.Circle({
                    radius: 7,
                    fill: new ol.style.Fill({
                        color: '#ffcc33'
                    }),
                    stroke: new ol.style.Stroke({
                        color: 'black',
                        width: 1
                    })
                })
            })
        });

        const controls = [
            new ol.control.Zoom(),
            new ol.control.Attribution({
                collapsible: true,
                collapsed: true
            }),
            new ol.control.ScaleLine(),
            new ol.control.FullScreen()
        ];

        map = new ol.Map({
            target: 'map',
            layers: [
                osmLayer,
                esriLayer,
                vectorLayer
            ],
            view: new ol.View({
                center: ol.proj.fromLonLat([0, 0]),
                zoom: mapConstraints.initialZoom,
                maxZoom: mapConstraints.maxZoom
            }),
            controls: controls
        });

        console.log("JS: OpenLayers map object initialized with Esri & OSM Tiles.");
        
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Info: Map initialized successfully.");
        }

    } catch (e) {
        console.error("JS: CRITICAL ERROR during map initialization:", e.message, e.stack);
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Critical Error: Map initialization failed - " + e.message);
        }
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
                padding: [70, 70, 70, 70], 
                duration: 1000,
                maxZoom: mapConstraints.maxZoom // Use constrained maxZoom here too
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
    if (!vectorSource) {
        console.warn("JS Warning: getEditedGeometry - vectorSource is not available.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: getEditedGeometry - vectorSource not available.");
        }
        return JSON.stringify({ type: 'FeatureCollection', features: [] });
    }
    
    const features = vectorSource.getFeatures();
    if (features.length === 0) {
        console.warn("JS Warning: getEditedGeometry - no features available in vectorSource.");
        if (webChannel && webChannel.jsLogMessage) {
            webChannel.jsLogMessage("JS Warning: getEditedGeometry - no features available.");
        }
        return JSON.stringify({ type: 'FeatureCollection', features: [] });
    }

    const geojsonFormat = new ol.format.GeoJSON();
    let featuresArray = [];

    features.forEach(function(feature) {
        try {
            const geometry = feature.getGeometry();
            if (!geometry) {
                console.warn("JS Warning: Feature found with no geometry, skipping.", feature.getId());
                 if (webChannel && webChannel.jsLogMessage) {
                    webChannel.jsLogMessage(`JS Warning: Feature ID ${feature.getId()} has no geometry.`);
                }
                return; // Skip this feature
            }

            // Clone and transform geometry to EPSG:4326 before writing to GeoJSON
            const transformedGeometry = geometry.clone().transform(
                map.getView().getProjection(), // From map projection (e.g., EPSG:3857)
                'EPSG:4326'                   // To Lon/Lat
            );
            
            const geojsonFeatureObject = {
                type: 'Feature',
                geometry: geojsonFormat.writeGeometryObject(transformedGeometry), // Geometry is now in EPSG:4326
                properties: {
                    // ol.format.KML typically reads <Placemark id="..."> into feature.id_
                    // and <name>, <description> into feature.get('name'), feature.get('description')
                    db_id: feature.getId() || feature.get('db_id') || null, 
                    name: feature.get('name') || null, 
                    description: feature.get('description') || null
                }
            };
            featuresArray.push(geojsonFeatureObject);
        } catch (e) {
            let errorMsg = "JS Error: Error processing a feature for getEditedGeometry";
            let featureIdForError = feature ? feature.getId() || feature.get('db_id') : 'unknown';
            console.error(`${errorMsg} (ID: ${featureIdForError}):`, e.message, e.stack, feature);
            if (webChannel && webChannel.jsLogMessage) {
                 webChannel.jsLogMessage(`${errorMsg} (ID: ${featureIdForError}) - ${e.message}`);
            }
        }
    });

    // For multi-KML save, return the FeatureCollection.
    // For single KML save, the Python backend needs to extract the single feature.
    const featureCollection = {
        type: 'FeatureCollection',
        features: featuresArray
    };
    
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage(`JS Info: getEditedGeometry returning FeatureCollection with ${featuresArray.length} features.`);
    }
    // console.log("JS: Returning FeatureCollection:", JSON.stringify(featureCollection)); // For debugging, can be verbose
    return JSON.stringify(featureCollection);
}

function clearMap() {
    console.log("JS: clearMap called.");
    if (vectorSource) {
        vectorSource.clear();
    }
    if (map) {
        map.getView().setCenter(ol.proj.fromLonLat([0, 0]));
        map.getView().setZoom(mapConstraints.initialZoom);
    }
    disableMapEditing();
    console.log("Map cleared and view reset.");
    if (webChannel && webChannel.jsLogMessage) {
        webChannel.jsLogMessage("JS Info: Map cleared and view reset.");
    }
}

function switchBaseLayer(layerName) {
    console.log("JS: switchBaseLayer called with:", layerName);
    if (!map || !esriLayer || !osmLayer) {
        console.error("JS Error: Map or base layers not initialized for switching.");
        return;
    }
    if (layerName === 'Esri') {
        esriLayer.setVisible(true);
        osmLayer.setVisible(false);
        console.log("JS: Switched to Esri layer.");
    } else if (layerName === 'OSM') {
        esriLayer.setVisible(false);
        osmLayer.setVisible(true);
        console.log("JS: Switched to OSM layer.");
    } else {
        console.warn("JS Warning: Unknown layer name for switchBaseLayer:", layerName);
    }
}

// New function to apply settings from Python
function setMapDisplaySettings(settings) {
    console.log("JS: setMapDisplaySettings called with:", settings);
    if (!map || !vectorLayer) {
        console.error("JS Error: Map or vectorLayer not ready for setMapDisplaySettings.");
        return;
    }

    let newMaxZoom = parseInt(settings.kml_max_zoom, 10);
    if (isNaN(newMaxZoom) || newMaxZoom < 1 || newMaxZoom > 22) {
        newMaxZoom = 18; // Fallback to a sensible default if parsing fails or out of range
        console.warn("JS: Invalid kml_max_zoom received, defaulting to 18.");
    }
    mapConstraints.maxZoom = newMaxZoom;
    map.getView().setMaxZoom(newMaxZoom);
    console.log("JS: View maxZoom updated to", newMaxZoom);

    mapConstraints.kmlFillColor = settings.kml_fill_color_hex ? settings.kml_fill_color_hex + Math.round(settings.kml_fill_opacity_percent * 2.55).toString(16).padStart(2, '0') : 'rgba(0,123,255,0.5)';
    mapConstraints.kmlStrokeColor = settings.kml_line_color_hex || '#000000';
    mapConstraints.kmlStrokeWidth = parseInt(settings.kml_line_width_px, 10) || 1;

    vectorLayer.setStyle(new ol.style.Style({
        stroke: new ol.style.Stroke({
            color: mapConstraints.kmlStrokeColor,
            width: mapConstraints.kmlStrokeWidth
        }),
        fill: new ol.style.Fill({
            color: mapConstraints.kmlFillColor
        }),
        image: new ol.style.Circle({ 
            radius: 7,
            fill: new ol.style.Fill({
                color: mapConstraints.kmlFillColor 
            }),
            stroke: new ol.style.Stroke({
                color: mapConstraints.kmlStrokeColor,
                width: 1
            })
        })
    }));
    vectorSource.refresh(); // To apply new style to existing features
    console.log("JS: KML vector layer style updated.");
}

console.log("kml_editor_map.js loaded (modified for Esri Tiles).");
