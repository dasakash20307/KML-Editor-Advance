# File: DilasaKMLTool_v4/core/kml_generator.py
# ----------------------------------------------------------------------
import simplekml
import utm # For UTM to Lat/Lon conversion

# No CSV_HEADERS needed here directly if data is passed pre-processed

def create_kml_description_for_placemark(polygon_db_record):
    """
    Creates the formatted KML description string from a polygon data dictionary
    (as retrieved from the database or processed).
    """
    area_val = polygon_db_record.get("proposed_area_acre")
    area_display = area_val if area_val and area_val.strip() else "N/A"
    
    description = (
        f"Farmer name: {polygon_db_record.get('farmer_name', 'N/A')}\n"
        f"Village: {polygon_db_record.get('village_name', 'N/A')}\n"
        f"Block: {polygon_db_record.get('block', 'N/A')}\n"
        f"District: {polygon_db_record.get('district', 'N/A')}\n"
        f"Proposed Area (acre): {area_display}"
    )
    return description

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
    }

    if add_polygon_to_kml_object(kml_test, sample_record):
        print("Sample polygon added successfully.")
        kml_test.save("test_polygon.kml")
        print("Saved test_polygon.kml")
    else:
        print("Failed to add sample polygon.")

