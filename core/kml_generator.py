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

def add_polygon_to_kml_object(kml_document, polygon_db_record):
    """
    Adds a single polygon to a simplekml.Kml object.
    polygon_db_record is a dictionary containing all necessary data for one polygon,
    including p1_easting, p1_northing, p1_altitude, p1_zone_num, p1_zone_letter, etc.
    Returns True if polygon was added successfully, False otherwise.
    """
    kml_coordinates_with_altitude = []

    try:
        for i in range(1, 5): # Points P1 to P4
            easting = polygon_db_record.get(f'p{i}_easting')
            northing = polygon_db_record.get(f'p{i}_northing')
            altitude = polygon_db_record.get(f'p{i}_altitude', 0.0) # Default altitude if missing
            zone_num = polygon_db_record.get(f'p{i}_zone_num')
            zone_letter = polygon_db_record.get(f'p{i}_zone_letter')

            if None in [easting, northing, zone_num, zone_letter]:
                # This check should ideally be redundant if status is 'valid_for_kml'
                print(f"KML GEN Error: Missing critical UTM components for Point {i} in UUID {polygon_db_record.get('uuid')}")
                return False

            # Convert UTM to Latitude/Longitude
            # The `utm` library typically handles zone letters to determine N/S hemisphere.
            lat, lon = utm.to_latlon(easting, northing, zone_num, zone_letter)
            kml_coordinates_with_altitude.append((lon, lat, altitude))

        if len(kml_coordinates_with_altitude) != 4:
            print(f"KML GEN Error: Could not form 4 valid coordinates for UUID {polygon_db_record.get('uuid')}")
            return False

        # Close the polygon by adding the first point at the end
        kml_coordinates_with_altitude.append(kml_coordinates_with_altitude[0])

        # Create KML Polygon
        placemark_name = polygon_db_record.get("uuid", "Unnamed Polygon")
        polygon = kml_document.newpolygon(name=placemark_name)
        polygon.outerboundaryis = kml_coordinates_with_altitude

        # Add description
        polygon.description = create_kml_description_for_placemark(polygon_db_record)

        # Apply styling
        polygon.style.linestyle.color = simplekml.Color.yellow  # KML yellow (aabbggrr -> ff00ffff)
        polygon.style.linestyle.width = 2
        polygon.style.polystyle.outline = 1  # True (draw outline)
        polygon.style.polystyle.fill = 0     # False (do not fill)

        return True # Polygon added successfully

    except utm.error.OutOfRangeError as e_utm: # type: ignore
        print(f"KML GEN Error (UTM Conversion): {e_utm} for UUID {polygon_db_record.get('uuid')}")
        return False
    except Exception as e:
        print(f"KML GEN Error (General): Adding polygon {polygon_db_record.get('uuid', 'N/A')} to KML failed: {e}")
        return False

# Example usage (if testing kml_generator.py directly)
if __name__ == '__main__':
    print("Testing KML Generator module...")
    kml_test = simplekml.Kml(name="Test KML Document")

    # Sample data similar to what would be fetched from DB for a 'valid_for_kml' record
    sample_record = {
        "uuid": "TEST_UUID_001", "response_code": "RC_TEST_001",
        "farmer_name": "KML Test Farmer", "village_name": "KML Test Village",
        "block": "Test Block", "district": "Test District", "proposed_area_acre": "2.5",
        "p1_easting": 471895.31, "p1_northing": 2135690.93, "p1_altitude": 100, "p1_zone_num": 43, "p1_zone_letter": "Q",
        "p2_easting": 471995.31, "p2_northing": 2135690.93, "p2_altitude": 101, "p2_zone_num": 43, "p2_zone_letter": "Q",
        "p3_easting": 471995.31, "p3_northing": 2135590.93, "p3_altitude": 102, "p3_zone_num": 43, "p3_zone_letter": "Q",
        "p4_easting": 471895.31, "p4_northing": 2135590.93, "p4_altitude": 103, "p4_zone_num": 43, "p4_zone_letter": "Q",
        "status": "valid_for_kml"
        # Add new v5 fields to test if they are correctly excluded or included if not in excluded_keys
        # For example, if 'evaluation_status' is NOT in excluded_keys, it should appear.
        # If 'some_other_field' is added and not in excluded_keys, it should appear.
        ,"evaluation_status": "Eligible",
        "custom_field_test": "Custom Value"
    }

    if add_polygon_to_kml_object(kml_test, sample_record):
        print("Sample polygon added successfully.")
        # You can inspect the generated KML description in the output file.
        # The description for "TEST_UUID_001" should now be dynamically generated.
        # Expected fields in description (based on sample_record and default exclusions):
        # Farmer Name: KML Test Farmer
        # Village Name: KML Test Village
        # Block: Test Block
        # District: Test District
        # Proposed Area Acre: 2.5
        # Evaluation Status: Eligible
        # Custom Field Test: Custom Value
        kml_test.save("test_polygon_v5desc.kml") # Save with a new name to see the change
        print("Saved test_polygon_v5desc.kml")
    else:
        print("Failed to add sample polygon.")
