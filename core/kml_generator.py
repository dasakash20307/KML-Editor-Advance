# File: DilasaKMLTool_v4/core/kml_generator.py
# ----------------------------------------------------------------------
import simplekml
import utm # For UTM to Lat/Lon conversion

# No CSV_HEADERS needed here directly if data is passed pre-processed

def create_kml_description_for_placemark(data_record):
    """
    Creates a formatted KML description string dynamically from a data record dictionary,
    excluding specified keys.
    """
    excluded_keys = [
        'uuid', 'response_code', 'id', 'db_id',
        'status', 'kml_file_status', 'kml_file_name',
        'kml_export_count', 'last_kml_export_date',
        'date_added', 'last_modified',
        'edit_count', 'last_edit_date', 'editor_device_id', 'editor_device_nickname',
        'device_code', 'error_messages',
        'p1_utm_str', 'p1_altitude', 'p1_easting', 'p1_northing', 'p1_zone_num', 'p1_zone_letter', 'p1_substituted',
        'p2_utm_str', 'p2_altitude', 'p2_easting', 'p2_northing', 'p2_zone_num', 'p2_zone_letter', 'p2_substituted',
        'p3_utm_str', 'p3_altitude', 'p3_easting', 'p3_northing', 'p3_zone_num', 'p3_zone_letter', 'p3_substituted',
        'p4_utm_str', 'p4_altitude', 'p4_easting', 'p4_northing', 'p4_zone_num', 'p4_zone_letter', 'p4_substituted',
    ]

    description_parts = []
    if not data_record:
        return "No data available for description."

    for key, value in data_record.items():
        if key not in excluded_keys:
            # Format key: replace underscores with spaces, capitalize words
            formatted_key = key.replace('_', ' ').title()
            # Use 'N/A' for None or empty string values
            display_value = value if value is not None and str(value).strip() != "" else "N/A"
            description_parts.append(f"{formatted_key}: {display_value}")

    if not description_parts:
        return "No description available."

    return '\n'.join(description_parts)

def add_polygon_to_kml_object(kml_document, polygon_db_record, edited_coordinates_list=None):
    """
    Adds a single polygon to a simplekml.Kml object.
    polygon_db_record is a dictionary containing all necessary data for one polygon.
    If edited_coordinates_list (list of (lon, lat, alt) tuples) is provided,
    it's used for the polygon. Otherwise, P1-P4 UTM coordinates are extracted
    from polygon_db_record and converted.
    Returns True if polygon was added successfully, False otherwise.
    """
    kml_coordinates_with_altitude = []
    placemark_name = polygon_db_record.get("uuid", "Unnamed Polygon")
    used_edited_coords = False # Flag to log which path was taken

    try:
        if edited_coordinates_list and isinstance(edited_coordinates_list, list) and len(edited_coordinates_list) > 0:
            print(f"KML GEN Info: Using edited_coordinates_list for {placemark_name}. Length: {len(edited_coordinates_list)}")
            used_edited_coords = True
            # Use provided coordinates
            kml_coordinates_with_altitude = [] # Initialize to ensure it's fresh
            for i, coord_tuple in enumerate(edited_coordinates_list):
                if not isinstance(coord_tuple, (list, tuple)) or not (2 <= len(coord_tuple) <= 3):
                    print(f"KML GEN Error: Invalid coordinate tuple format for {placemark_name} at index {i}: {coord_tuple}")
                    return False

                lon = coord_tuple[0]
                lat = coord_tuple[1]
                alt = coord_tuple[2] if len(coord_tuple) == 3 and coord_tuple[2] is not None else 0.0
                kml_coordinates_with_altitude.append((lon, lat, alt))

            if len(kml_coordinates_with_altitude) < 3: # A polygon needs at least 3 points
                print(f"KML GEN Error: Not enough valid points processed from edited_coordinates_list for {placemark_name}. Need at least 3.")
                return False

            # Close the polygon if it's not already closed
            # Important: Check if list is not empty before accessing elements
            if kml_coordinates_with_altitude and (kml_coordinates_with_altitude[0] != kml_coordinates_with_altitude[-1]):
                kml_coordinates_with_altitude.append(kml_coordinates_with_altitude[0])
                print(f"KML GEN Info: Polygon for {placemark_name} (from edited) was auto-closed.")
        else:
            print(f"KML GEN Info: Falling back to P1-P4 UTM conversion for {placemark_name}.")
            # Fallback to P1-P4 UTM conversion
            for i in range(1, 5): # Points P1 to P4
                easting = polygon_db_record.get(f'p{i}_easting')
                northing = polygon_db_record.get(f'p{i}_northing')
                altitude = polygon_db_record.get(f'p{i}_altitude', 0.0) # Default altitude if missing
                zone_num = polygon_db_record.get(f'p{i}_zone_num')
                zone_letter = polygon_db_record.get(f'p{i}_zone_letter')

                if None in [easting, northing, zone_num, zone_letter]:
                    print(f"KML GEN Error: Missing critical UTM components for Point {i} in UUID {placemark_name}")
                    return False

                lat, lon = utm.to_latlon(easting, northing, zone_num, zone_letter)
                kml_coordinates_with_altitude.append((lon, lat, altitude))

            if len(kml_coordinates_with_altitude) != 4: # Should be exactly 4 before closing
                print(f"KML GEN Error: Could not form 4 valid coordinates from P1-P4 for UUID {placemark_name}")
                return False

            # Close the 4-point polygon
            kml_coordinates_with_altitude.append(kml_coordinates_with_altitude[0])

        if not kml_coordinates_with_altitude: # Should not happen if logic above is correct
             print(f"KML GEN Error: No coordinates processed for UUID {placemark_name}")
             return False

        # Create KML Polygon
        polygon = kml_document.newpolygon(name=placemark_name)
        polygon.outerboundaryis = kml_coordinates_with_altitude

        # Add description
        polygon.description = create_kml_description_for_placemark(polygon_db_record)

        # Apply styling
        polygon.style.linestyle.color = simplekml.Color.yellow  # KML yellow (aabbggrr -> ff00ffff)
        polygon.style.linestyle.width = 2
        polygon.style.polystyle.outline = 1  # True (draw outline)
        polygon.style.polystyle.fill = 0     # False (do not fill)

        if used_edited_coords:
            print(f"KML GEN Success: Polygon for {placemark_name} added using edited_coordinates_list. Points used: {len(kml_coordinates_with_altitude)}")
        else:
            print(f"KML GEN Success: Polygon for {placemark_name} added using P1-P4 UTM data. Points used: {len(kml_coordinates_with_altitude)}")
        return True # Polygon added successfully

    except utm.error.OutOfRangeError as e_utm: # type: ignore
        print(f"KML GEN Error (UTM Conversion): {e_utm} for UUID {placemark_name}. Used edited: {used_edited_coords}")
        return False
    except Exception as e:
        print(f"KML GEN Error (General): Adding polygon {placemark_name} to KML failed: {e}. Used edited: {used_edited_coords}")
        return False

# Example usage (if testing kml_generator.py directly)
if __name__ == '__main__':
    print("Testing KML Generator module...")
    kml_test_doc = simplekml.Kml(name="Test KML Document")

    # Sample data similar to what would be fetched from DB for a 'valid_for_kml' record
    sample_record_utm = {
        "uuid": "TEST_UUID_UTM_001", "response_code": "RC_TEST_001", "id": "ID_001", "db_id": "DB_ID_XYZ",
        "farmer_name": "UTM Test Farmer", "village_name": "UTM Test Village",
        "block": "Test Block", "district": "Test District", "proposed_area_acre": "2.5",
        "p1_easting": 471895.31, "p1_northing": 2135690.93, "p1_altitude": 100, "p1_zone_num": 43, "p1_zone_letter": "Q", "p1_utm_str": "43Q 471895.31 2135690.93",
        "p2_easting": 471995.31, "p2_northing": 2135690.93, "p2_altitude": 101, "p2_zone_num": 43, "p2_zone_letter": "Q", "p2_substituted": "false",
        "p3_easting": 471995.31, "p3_northing": 2135590.93, "p3_altitude": 102, "p3_zone_num": 43, "p3_zone_letter": "Q",
        "p4_easting": 471895.31, "p4_northing": 2135590.93, "p4_altitude": 103, "p4_zone_num": 43, "p4_zone_letter": "Q",
        "status": "valid_for_kml", "kml_file_status": "Pending", "kml_file_name": "test_utm.kml",
        "evaluation_status": "Eligible", "crop_name": "Maize",
    }

    print(f"\n--- Testing with UTM P1-P4 data (UUID: {sample_record_utm['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_utm):
        print(f"Polygon for {sample_record_utm['uuid']} added successfully (from UTM).")
    else:
        print(f"Failed to add polygon for {sample_record_utm['uuid']} (from UTM).")

    # Sample data for testing with edited_coordinates_list
    sample_record_edited = {
        "uuid": "TEST_UUID_EDITED_002",
        "farmer_name": "Edited Coords Farmer", "village_name": "Edited Coords Village",
        "block": "Edit Block", "district": "Edit District", "proposed_area_acre": "5.0",
        "evaluation_status": "Re-evaluated", "crop_name": "Cotton",
        # P1-P4 data can be absent or present, should be ignored if edited_coordinates_list is used
    }

    # Case 1: Valid edited_coordinates_list (already closed)
    edited_coords_closed = [
        (78.476, 17.385, 50),  # Lon, Lat, Alt
        (78.477, 17.385, 50),
        (78.477, 17.384, 50),
        (78.476, 17.384, 50),
        (78.476, 17.385, 50)
    ]
    print(f"\n--- Testing with valid (closed) edited_coordinates_list (UUID: {sample_record_edited['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_edited, edited_coordinates_list=edited_coords_closed):
        print(f"Polygon for {sample_record_edited['uuid']} with pre-closed coords added successfully.")
    else:
        print(f"Failed to add polygon for {sample_record_edited['uuid']} with pre-closed coords.")

    # Case 2: Valid edited_coordinates_list (not closed)
    sample_record_edited["uuid"] = "TEST_UUID_EDITED_003" # New UUID for new placemark
    edited_coords_open = [
        (78.500, 17.400, 55),
        (78.501, 17.400, 55),
        (78.501, 17.399, 55),
        (78.500, 17.399, 55)
    ]
    print(f"\n--- Testing with valid (open) edited_coordinates_list (UUID: {sample_record_edited['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_edited, edited_coordinates_list=edited_coords_open):
        print(f"Polygon for {sample_record_edited['uuid']} with open coords added successfully (should be auto-closed).")
    else:
        print(f"Failed to add polygon for {sample_record_edited['uuid']} with open coords.")

    # Case 3: Edited_coordinates_list with less than 3 points
    sample_record_edited["uuid"] = "TEST_UUID_EDITED_004"
    edited_coords_too_few = [
        (78.510, 17.410, 60),
        (78.511, 17.410, 60)
    ]
    print(f"\n--- Testing with too few points in edited_coordinates_list (UUID: {sample_record_edited['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_edited, edited_coordinates_list=edited_coords_too_few):
        print(f"Polygon for {sample_record_edited['uuid']} with too few points - unexpectedly added.")
    else:
        print(f"Failed to add polygon for {sample_record_edited['uuid']} with too few points (expected failure).")

    # Case 4: Edited_coordinates_list with invalid tuple format (lon, lat only, no alt)
    # Note: The code now auto-adds altitude 0.0 if only (lon,lat) is provided.
    # To truly test invalid format, it would need to be something like a single number, or (lon,lat,alt,extra)
    sample_record_edited["uuid"] = "TEST_UUID_EDITED_005"
    edited_coords_lon_lat_only = [
        (78.520, 17.420),
        (78.521, 17.420),
        (78.521, 17.419),
        (78.520, 17.419)
    ]
    print(f"\n--- Testing with (lon,lat) tuples in edited_coordinates_list (UUID: {sample_record_edited['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_edited, edited_coordinates_list=edited_coords_lon_lat_only):
        print(f"Polygon for {sample_record_edited['uuid']} with (lon,lat) tuples added successfully (altitude should be 0.0).")
    else:
        print(f"Failed to add polygon for {sample_record_edited['uuid']} with (lon,lat) tuples.")

    # Case 5: Empty edited_coordinates_list (should fall back to UTM)
    sample_record_fallback = {
        "uuid": "TEST_UUID_FALLBACK_006",
        "farmer_name": "Fallback Farmer", "village_name": "Fallback Village",
        "p1_easting": 471800, "p1_northing": 2135600, "p1_altitude": 110, "p1_zone_num": 43, "p1_zone_letter": "Q",
        "p2_easting": 471900, "p2_northing": 2135600, "p2_altitude": 111, "p2_zone_num": 43, "p2_zone_letter": "Q",
        "p3_easting": 471900, "p3_northing": 2135500, "p3_altitude": 112, "p3_zone_num": 43, "p3_zone_letter": "Q",
        "p4_easting": 471800, "p4_northing": 2135500, "p4_altitude": 113, "p4_zone_num": 43, "p4_zone_letter": "Q",
        "evaluation_status": "Eligible", "crop_name": "Soybean",
    }
    print(f"\n--- Testing with empty edited_coordinates_list (UUID: {sample_record_fallback['uuid']}) ---")
    if add_polygon_to_kml_object(kml_test_doc, sample_record_fallback, edited_coordinates_list=[]):
        print(f"Polygon for {sample_record_fallback['uuid']} with empty list added successfully (fallback to UTM).")
    else:
        print(f"Failed to add polygon for {sample_record_fallback['uuid']} with empty list (UTM fallback failed).")


    output_kml_file = "test_polygons_refactored.kml"
    try:
        kml_test_doc.save(output_kml_file)
        print(f"\nSaved refactored KML test results to: {output_kml_file}")
    except Exception as e_save:
        print(f"Error saving KML file: {e_save}")
