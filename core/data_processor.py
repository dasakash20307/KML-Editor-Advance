# ----------------------------------------------------------------------
# File: DilasaKMLTool_v4/core/data_processor.py
# ----------------------------------------------------------------------
import re

# Expected CSV Headers - Centralized here for data_processor
# These headers align with V5 database schema and include KML description fields.
CSV_HEADERS = {
    # V5 Mandatory DB Columns (aligning with polygon_data table)
    "uuid": "uuid",  # Often auto-generated if missing in CSV, but good to have a header
    "response_code": "response_code",  # Critical for duplicate checks
    "farmer_name": "farmer_name",
    "village_name": "village_name", # Changed from "village" to match DB
    "block": "block",
    "district": "district",
    "proposed_area_acre": "proposed_area_acre", # Changed from "area"
    "p1_utm_str": "p1_utm_str", "p1_altitude": "p1_altitude", # Explicitly named to match DB
    "p2_utm_str": "p2_utm_str", "p2_altitude": "p2_altitude",
    "p3_utm_str": "p3_utm_str", "p3_altitude": "p3_altitude",
    "p4_utm_str": "p4_utm_str", "p4_altitude": "p4_altitude",
    # New V5 fields (device_code, kml_file_name, kml_file_status, etc.) are typically set programmatically
    # and are not expected directly from the base CSV for farmer plot data.
    # If they could optionally come from CSV, they would be added here.

    # Example columns for KML description
    "kml_desc_survey_date": "kml_desc_survey_date", # User-friendly: "Survey Date for KML"
    "kml_desc_crop_type": "kml_desc_crop_type",   # User-friendly: "Crop Type for KML"
    "kml_desc_notes": "kml_desc_notes",         # User-friendly: "Additional Notes for KML"
}

def parse_utm_string(utm_str):
    """
    Parses a UTM string like "43Q 533039 2196062" into components.
    Returns (zone_number, zone_letter, easting, northing) or None if error.
    """
    if not utm_str or not isinstance(utm_str, str):
        return None
    parts = utm_str.strip().split()
    if len(parts) != 3:
        return None
    
    zone_designator = parts[0]
    easting_str = parts[1]
    northing_str = parts[2]

    match = re.match(r"(\d+)([A-Za-z])$", zone_designator)
    if not match:
        return None
    
    try:
        zone_number = int(match.group(1))
        zone_letter = match.group(2).upper()
        easting = float(easting_str)
        northing = float(northing_str)
        return zone_number, zone_letter, easting, northing
    except ValueError:
        return None

def process_csv_row_data(row_dict_from_reader):
    """
    Processes a single row dictionary (from csv.DictReader) according to V5 schema.
    Cleans BOM from keys, extracts data based on updated CSV_HEADERS,
    validates points, attempts substitution for one missing point.
    Includes specific KML description fields in the output.
    Returns a dictionary flattened and ready for database insertion,
    including 'status' and 'error_messages' (as a string).
    """
    # Clean BOM from all keys in the input dictionary.
    row_dict = {k.lstrip('\ufeff'): v for k, v in row_dict_from_reader.items()}

    processed_for_db = {}
    error_accumulator = [] # Internal list to gather error messages

    # Populate with V5 mandatory fields from CSV
    # Using .get with CSV_HEADERS values directly as keys for row_dict
    processed_for_db["uuid"] = row_dict.get(CSV_HEADERS["uuid"], "").strip()
    processed_for_db["response_code"] = row_dict.get(CSV_HEADERS["response_code"], "").strip()
    processed_for_db["farmer_name"] = row_dict.get(CSV_HEADERS["farmer_name"], "").strip()
    processed_for_db["village_name"] = row_dict.get(CSV_HEADERS["village_name"], "").strip()
    processed_for_db["block"] = row_dict.get(CSV_HEADERS["block"], "").strip()
    processed_for_db["district"] = row_dict.get(CSV_HEADERS["district"], "").strip()
    processed_for_db["proposed_area_acre"] = row_dict.get(CSV_HEADERS["proposed_area_acre"], "").strip()
    
    processed_for_db["status"] = "valid_for_kml" # Default status

    # KML description fields
    processed_for_db["kml_desc_survey_date"] = row_dict.get(CSV_HEADERS["kml_desc_survey_date"], "").strip()
    processed_for_db["kml_desc_crop_type"] = row_dict.get(CSV_HEADERS["kml_desc_crop_type"], "").strip()
    processed_for_db["kml_desc_notes"] = row_dict.get(CSV_HEADERS["kml_desc_notes"], "").strip()

    # Validate critical V5 mandatory fields that must come from CSV
    if not processed_for_db["uuid"]:
        # While UUID can be auto-generated later, if a CSV provides it, it should be valid.
        # For this processor, we'll flag if the CSV intends to provide it but it's empty.
        # The main import logic might decide to generate one if this field is empty.
        # For now, let's assume if the column "uuid" is present and empty, it's an issue for this row.
        # If the column "uuid" itself is missing, row_dict.get provides "", so this check works.
        error_accumulator.append(f"'{CSV_HEADERS['uuid']}' is empty or missing. This field is used for KML filename generation.")

    if not processed_for_db["response_code"]:
        error_accumulator.append(f"'{CSV_HEADERS['response_code']}' is empty or missing. This field is critical for duplicate checking.")

    # Add checks for other new V5 mandatory fields expected from CSV
    if not processed_for_db["farmer_name"]:
        error_accumulator.append(f"'{CSV_HEADERS['farmer_name']}' is empty or missing.")
    if not processed_for_db["village_name"]:
        error_accumulator.append(f"'{CSV_HEADERS['village_name']}' is empty or missing.")
    # Block, District, proposed_area_acre might be optional or have defaults,
    # but if they are considered mandatory from CSV, add checks:
    # if not processed_for_db["block"]:
    #     error_accumulator.append(f"'{CSV_HEADERS['block']}' is empty or missing.")
    # if not processed_for_db["district"]:
    #     error_accumulator.append(f"'{CSV_HEADERS['district']}' is empty or missing.")
    # if not processed_for_db["proposed_area_acre"]:
    #     error_accumulator.append(f"'{CSV_HEADERS['proposed_area_acre']}' is empty or missing.")


    if not processed_for_db["uuid"] or not processed_for_db["response_code"]: # Still critical for processing flow
        processed_for_db["status"] = "error_missing_identifiers"
        # Ensure specific error messages for these are present if not already added
        if not any(CSV_HEADERS['uuid'] in msg for msg in error_accumulator) and not processed_for_db["uuid"]:
            error_accumulator.append(f"'{CSV_HEADERS['uuid']}' is critically missing.")
        if not any(CSV_HEADERS['response_code'] in msg for msg in error_accumulator) and not processed_for_db["response_code"]:
            error_accumulator.append(f"'{CSV_HEADERS['response_code']}' is critically missing.")
        # Populate point fields with defaults for DB consistency even on this critical error
        for i in range(1, 5):
            processed_for_db[f"p{i}_utm_str"] = ""
            processed_for_db[f"p{i}_altitude"] = 0.0
            processed_for_db[f"p{i}_easting"] = None
            processed_for_db[f"p{i}_northing"] = None
            processed_for_db[f"p{i}_zone_num"] = None
            processed_for_db[f"p{i}_zone_letter"] = None
            processed_for_db[f"p{i}_substituted"] = False
        processed_for_db["error_messages"] = "\n".join(error_accumulator) if error_accumulator else None
        return processed_for_db

    # This list stores detailed info for each point during processing
    # Each item: {"utm_str", "altitude", "easting", "northing", "zone_num", "zone_letter", "substituted", "is_valid_parse"}
    intermediate_points_data = []
    for i in range(1, 5):
        # Use new V5 header keys for points
        utm_header_key = f"p{i}_utm_str" # This is the key in CSV_HEADERS dict
        alt_header_key = f"p{i}_altitude" # This is the key in CSV_HEADERS dict

        # Attempt to get the header name from CSV_HEADERS. If the key itself (e.g. "p1_utm_str") 
        # is not in CSV_HEADERS (which would be a setup error), default to using the key directly.
        # This makes it slightly more robust to CSV_HEADERS definition errors, though ideally, they match.
        utm_csv_header_name = CSV_HEADERS.get(utm_header_key, utm_header_key)
        alt_csv_header_name = CSV_HEADERS.get(alt_header_key, alt_header_key)

        utm_str_val = row_dict.get(utm_csv_header_name, "").strip()
        alt_str_val = row_dict.get(alt_csv_header_name, "0").strip() # Default to "0" if missing
        
        altitude_val = 0.0
        try:
            altitude_val = float(alt_str_val) if alt_str_val else 0.0
        except ValueError:
            error_accumulator.append(f"Point {i} altitude ('{alt_str_val}') is non-numeric, defaulted to 0.")
        
        parsed_utm_components = parse_utm_string(utm_str_val)
        point_data_item = {
            "utm_str": utm_str_val, "altitude": altitude_val, 
            "easting": None, "northing": None, "zone_num": None, "zone_letter": None, 
            "substituted": False, "is_valid_parse": False # Internal flag for processing
        }
        if parsed_utm_components:
            zn, zl, e, n = parsed_utm_components
            point_data_item.update({
                "easting": e, "northing": n, "zone_num": zn, "zone_letter": zl, 
                "is_valid_parse": True
            })
        else:
            if utm_str_val: # Only log malformed if it wasn't empty
                error_accumulator.append(f"Point {i} UTM string ('{utm_str_val}') is malformed.")
        intermediate_points_data.append(point_data_item)

    # --- Point Substitution Logic ---
    invalid_point_indices = [idx for idx, p_data in enumerate(intermediate_points_data) if not p_data["is_valid_parse"]]
    if len(invalid_point_indices) > 1:
        processed_for_db["status"] = "error_too_many_missing_points"
        error_accumulator.append(f"Too many missing/invalid UTM points ({len(invalid_point_indices)}).")
    elif len(invalid_point_indices) == 1:
        idx_to_fix = invalid_point_indices[0]
        # Substitution map: 0->1, 1->2, 2->3, 3->0 (indices for intermediate_points_data)
        substitute_source_idx_map = {0: 1, 1: 2, 2: 3, 3: 0} 
        substitute_from_idx = substitute_source_idx_map[idx_to_fix]

        if intermediate_points_data[substitute_from_idx]["is_valid_parse"]:
            source_point = intermediate_points_data[substitute_from_idx]
            target_point = intermediate_points_data[idx_to_fix]
            
            target_point.update({
                "easting": source_point["easting"], "northing": source_point["northing"],
                "zone_num": source_point["zone_num"], "zone_letter": source_point["zone_letter"],
                "is_valid_parse": True, # Now considered valid for data structure
                "substituted": True,
                # Keep original altitude, update utm_str to reflect substitution
                "utm_str": target_point["utm_str"] + f" (Coords from P{substitute_from_idx+1})" 
            })
            error_accumulator.append(f"Point {idx_to_fix+1} coordinates substituted with Point {substitute_from_idx+1} data.")
        else:
            processed_for_db["status"] = "error_substitution_failed"
            error_accumulator.append(f"Cannot substitute Point {idx_to_fix+1} as substitute Point {substitute_from_idx+1} is also invalid.")
    
    # --- Flatten point data into processed_for_db and final status checks ---
    all_points_structurally_valid = True
    for i in range(4):
        p_data_item = intermediate_points_data[i]
        processed_for_db[f"p{i+1}_utm_str"] = p_data_item["utm_str"]
        processed_for_db[f"p{i+1}_altitude"] = p_data_item["altitude"]
        processed_for_db[f"p{i+1}_easting"] = p_data_item["easting"]
        processed_for_db[f"p{i+1}_northing"] = p_data_item["northing"]
        processed_for_db[f"p{i+1}_zone_num"] = p_data_item["zone_num"]
        processed_for_db[f"p{i+1}_zone_letter"] = p_data_item["zone_letter"]
        processed_for_db[f"p{i+1}_substituted"] = p_data_item["substituted"]
        if not p_data_item["is_valid_parse"]: # Check internal flag after substitution
            all_points_structurally_valid = False

    if processed_for_db["status"] == "valid_for_kml": # Only if no major errors so far
        if not all_points_structurally_valid:
            processed_for_db["status"] = "error_point_data_invalid"
            error_accumulator.append("One or more points have invalid/missing coordinate data after processing attempts.")
        else:
            # Zone consistency check (only if all points are structurally valid)
            p1_zn = processed_for_db.get("p1_zone_num")
            p1_zl = processed_for_db.get("p1_zone_letter")
            if p1_zn is not None and p1_zl is not None:
                first_point_zone = (p1_zn, p1_zl)
                for i in range(2, 5): # Check P2, P3, P4 against P1
                    current_point_zn = processed_for_db.get(f"p{i}_zone_num")
                    current_point_zl = processed_for_db.get(f"p{i}_zone_letter")
                    if current_point_zn is not None and current_point_zl is not None:
                        if (current_point_zn, current_point_zl) != first_point_zone:
                            processed_for_db["status"] = "error_inconsistent_zones"
                            error_accumulator.append(f"Inconsistent UTM zones found (e.g., P1: {first_point_zone}, P{i}: {(current_point_zn, current_point_zl)}).")
                            break 
                    else: # This point was supposed to be valid but is missing zone info for check
                        processed_for_db["status"] = "error_point_processing_incomplete"
                        error_accumulator.append(f"Missing zone information for Point {i} needed for consistency check.")
                        break # Stop further zone checks
            else: # P1 itself is missing zone information
                processed_for_db["status"] = "error_point_processing_incomplete"
                error_accumulator.append("Missing zone information for Point 1, cannot perform consistency check.")
    
    processed_for_db["error_messages"] = "\n".join(error_accumulator) if error_accumulator else None
    return processed_for_db

# --- API Data Processing ---

def process_api_row_data(api_row_dict, api_to_db_map):
    """
    Processes a single data record (dictionary) from an API.
    Uses api_to_db_map to map API field names to internal DB field names.
    Extracts data, validates points, attempts substitution for one missing point.
    Returns a dictionary flattened and ready for database insertion,
    including 'status' and 'error_messages' (as a string).
    """
    processed_for_db = {}
    error_accumulator = []

    # 1. Initial Mapping based on api_to_db_map
    for api_key, db_key in api_to_db_map.items():
        processed_for_db[db_key] = api_row_dict.get(api_key, "").strip()

    # 2. Ensure essential fields (uuid, response_code) are populated
    # We need to find the DB keys for uuid and response_code from the map values
    # This is a bit simplistic; a more robust way might be to have fixed internal keys
    # for these critical fields if the api_to_db_map could vary wildly.
    # For now, assume api_to_db_map *will* contain mappings for "uuid" and "response_code".

    # Find the db_key corresponding to 'uuid' and 'response_code' in the map's values
    db_uuid_key = None
    db_response_code_key = None
    for api_k, db_k in api_to_db_map.items():
        if db_k == "uuid":
            db_uuid_key = db_k
        elif db_k == "response_code":
            db_response_code_key = db_k

    # Use the found db_keys to check values in processed_for_db
    if not db_uuid_key or not processed_for_db.get(db_uuid_key):
        error_accumulator.append(f"Critical: UUID is empty or missing from API data based on map. API key expected to map to 'uuid'.")
    if not db_response_code_key or not processed_for_db.get(db_response_code_key):
        error_accumulator.append(f"Critical: Response Code is empty or missing from API data based on map. API key expected to map to 'response_code'.")

    if error_accumulator and ("UUID is empty or missing" in error_accumulator[-1] or \
                              "Response Code is empty or missing" in error_accumulator[-1]):
        processed_for_db["status"] = "error_missing_identifiers"
        # Populate point fields with defaults for DB consistency
        for i in range(1, 5):
            processed_for_db[f"p{i}_utm_str"] = ""
            processed_for_db[f"p{i}_altitude"] = 0.0
            processed_for_db[f"p{i}_easting"] = None
            processed_for_db[f"p{i}_northing"] = None
            processed_for_db[f"p{i}_zone_num"] = None
            processed_for_db[f"p{i}_zone_letter"] = None
            processed_for_db[f"p{i}_substituted"] = False
        processed_for_db["error_messages"] = "\n".join(error_accumulator)
        return processed_for_db

    processed_for_db.setdefault("status", "valid_for_kml") # Default status if not error_missing_identifiers

    # 3. UTM Point Processing
    # This list stores detailed info for each point during processing
    intermediate_points_data = []

    # api_to_db_map needs to define mappings for point data. Example:
    # "api_p1_utm": "p1_utm_str", "api_p1_alt": "p1_altitude", etc.
    for i in range(1, 5):
        # Find the api_keys for current point's UTM string and altitude from the map
        api_utm_key_for_point = None
        api_alt_key_for_point = None

        # Expected db_keys for points are "pX_utm_str" and "pX_altitude"
        target_db_utm_key = f"p{i}_utm_str"
        target_db_alt_key = f"p{i}_altitude"

        for api_k, db_k in api_to_db_map.items():
            if db_k == target_db_utm_key:
                api_utm_key_for_point = api_k
            elif db_k == target_db_alt_key:
                api_alt_key_for_point = api_k

        utm_str_val = api_row_dict.get(api_utm_key_for_point, "").strip() if api_utm_key_for_point else ""
        alt_str_val = api_row_dict.get(api_alt_key_for_point, "0").strip() if api_alt_key_for_point else "0" # Default "0"

        # Ensure these keys exist in processed_for_db from initial mapping if they were in api_to_db_map
        # If they weren't in api_to_db_map, they wouldn't be in processed_for_db yet.
        # The parse_utm_string and altitude processing will use utm_str_val and alt_str_val directly.
        # The final results will be stored using standard pX_ keys.
        processed_for_db[target_db_utm_key] = utm_str_val # Store the original UTM string

        altitude_val = 0.0
        try:
            altitude_val = float(alt_str_val) if alt_str_val else 0.0
        except ValueError:
            error_accumulator.append(f"Point {i} altitude ('{alt_str_val}') from API key '{api_alt_key_for_point}' is non-numeric, defaulted to 0.")
        processed_for_db[target_db_alt_key] = altitude_val # Store the parsed or default altitude

        parsed_utm_components = parse_utm_string(utm_str_val)
        point_data_item = {
            "utm_str": utm_str_val, "altitude": altitude_val,
            "easting": None, "northing": None, "zone_num": None, "zone_letter": None,
            "substituted": False, "is_valid_parse": False
        }
        if parsed_utm_components:
            zn, zl, e, n = parsed_utm_components
            point_data_item.update({
                "easting": e, "northing": n, "zone_num": zn, "zone_letter": zl,
                "is_valid_parse": True
            })
        else:
            if utm_str_val: # Only log malformed if it wasn't empty
                error_accumulator.append(f"Point {i} UTM string ('{utm_str_val}') from API key '{api_utm_key_for_point}' is malformed.")
        intermediate_points_data.append(point_data_item)

    # --- Point Substitution Logic (adapted from process_csv_row_data) ---
    invalid_point_indices = [idx for idx, p_data in enumerate(intermediate_points_data) if not p_data["is_valid_parse"]]
    if len(invalid_point_indices) > 1:
        processed_for_db["status"] = "error_too_many_missing_points"
        error_accumulator.append(f"Too many missing/invalid UTM points ({len(invalid_point_indices)}) from API data.")
    elif len(invalid_point_indices) == 1:
        idx_to_fix = invalid_point_indices[0]
        substitute_source_idx_map = {0: 1, 1: 2, 2: 3, 3: 0}
        substitute_from_idx = substitute_source_idx_map[idx_to_fix]

        if intermediate_points_data[substitute_from_idx]["is_valid_parse"]:
            source_point = intermediate_points_data[substitute_from_idx]
            target_point = intermediate_points_data[idx_to_fix]

            target_point.update({
                "easting": source_point["easting"], "northing": source_point["northing"],
                "zone_num": source_point["zone_num"], "zone_letter": source_point["zone_letter"],
                "is_valid_parse": True, "substituted": True,
                "utm_str": target_point["utm_str"] + f" (Coords from P{substitute_from_idx+1})"
            })
            # Altitudes are kept as their original/defaulted values unless substitution implies altitude change too.
            # For now, only coordinates are substituted.
            error_accumulator.append(f"Point {idx_to_fix+1} coordinates substituted with Point {substitute_from_idx+1} data using API fields.")
        else:
            processed_for_db["status"] = "error_substitution_failed"
            error_accumulator.append(f"Cannot substitute Point {idx_to_fix+1} (from API) as substitute Point {substitute_from_idx+1} is also invalid.")

    # --- Flatten point data into processed_for_db and final status checks (adapted) ---
    all_points_structurally_valid = True
    for i_loop_idx in range(4): # Loop 0 to 3 for list indices
        p_data_item = intermediate_points_data[i_loop_idx]
        db_point_idx = i_loop_idx + 1 # DB point index P1, P2, ...

        # These were already set or defaulted earlier, but substitution might change them
        processed_for_db[f"p{db_point_idx}_utm_str"] = p_data_item["utm_str"]
        processed_for_db[f"p{db_point_idx}_altitude"] = p_data_item["altitude"]
        # These are the core parsed values
        processed_for_db[f"p{db_point_idx}_easting"] = p_data_item["easting"]
        processed_for_db[f"p{db_point_idx}_northing"] = p_data_item["northing"]
        processed_for_db[f"p{db_point_idx}_zone_num"] = p_data_item["zone_num"]
        processed_for_db[f"p{db_point_idx}_zone_letter"] = p_data_item["zone_letter"]
        processed_for_db[f"p{db_point_idx}_substituted"] = p_data_item["substituted"]

        if not p_data_item["is_valid_parse"]:
            all_points_structurally_valid = False

    if processed_for_db["status"] == "valid_for_kml": # Only if no major errors so far
        if not all_points_structurally_valid:
            processed_for_db["status"] = "error_point_data_invalid"
            error_accumulator.append("One or more points from API data have invalid/missing coordinate data after processing attempts.")
        else:
            # Zone consistency check
            p1_zn = processed_for_db.get("p1_zone_num")
            p1_zl = processed_for_db.get("p1_zone_letter")
            if p1_zn is not None and p1_zl is not None: # Ensure P1 has valid zone info
                first_point_zone = (p1_zn, p1_zl)
                for i_check_idx in range(2, 5): # Check P2, P3, P4 against P1
                    current_point_zn = processed_for_db.get(f"p{i_check_idx}_zone_num")
                    current_point_zl = processed_for_db.get(f"p{i_check_idx}_zone_letter")
                    if current_point_zn is not None and current_point_zl is not None:
                        if (current_point_zn, current_point_zl) != first_point_zone:
                            processed_for_db["status"] = "error_inconsistent_zones"
                            error_accumulator.append(f"Inconsistent UTM zones in API data (e.g., P1: {first_point_zone}, P{i_check_idx}: {(current_point_zn, current_point_zl)}).")
                            break
                    else: # This point was supposed to be valid but is missing zone info
                        processed_for_db["status"] = "error_point_processing_incomplete"
                        error_accumulator.append(f"Missing zone information for Point {i_check_idx} from API data needed for consistency check.")
                        break
            else: # P1 itself is missing zone information
                processed_for_db["status"] = "error_point_processing_incomplete"
                error_accumulator.append("Missing zone information for Point 1 from API data, cannot perform consistency check.")

    processed_for_db["error_messages"] = "\n".join(error_accumulator) if error_accumulator else None
    return processed_for_db


if __name__ == '__main__':
    print("--- Testing CSV Processor with V5 Headers and Logic ---")

    # Test Case 1: Valid V5 CSV data
    # Using the actual values from CSV_HEADERS as keys for the sample row,
    # as DictReader would produce if these were the headers in the CSV file.
    sample_csv_row_v5_valid = {
        CSV_HEADERS["uuid"]: "CSV_UUID_V5_001",
        CSV_HEADERS["response_code"]: "CSV_RC_V5_001",
        CSV_HEADERS["farmer_name"]: "CSV Farmer V5",
        CSV_HEADERS["village_name"]: "CSV Village V5",
        CSV_HEADERS["block"]: "CSV Block V5",
        CSV_HEADERS["district"]: "CSV District V5",
        CSV_HEADERS["proposed_area_acre"]: "6.5",
        CSV_HEADERS["p1_utm_str"]: "43Q 123456 7890123", CSV_HEADERS["p1_altitude"]: "110",
        CSV_HEADERS["p2_utm_str"]: "43Q 123457 7890124", CSV_HEADERS["p2_altitude"]: "111",
        CSV_HEADERS["p3_utm_str"]: "43Q 123458 7890125", CSV_HEADERS["p3_altitude"]: "112",
        CSV_HEADERS["p4_utm_str"]: "43Q 123459 7890126", CSV_HEADERS["p4_altitude"]: "113",
        CSV_HEADERS["kml_desc_survey_date"]: "2024-03-15",
        CSV_HEADERS["kml_desc_crop_type"]: "Wheat",
        CSV_HEADERS["kml_desc_notes"]: "Fertile land, good yield expected.",
    }
    print("\nTest Case 1: Valid V5 CSV Data")
    processed_csv_data_v5_valid = process_csv_row_data(sample_csv_row_v5_valid)
    print(f"CSV Processed: {processed_csv_data_v5_valid.get('uuid')}, Status: {processed_csv_data_v5_valid.get('status')}")
    print(f"KML Survey Date: {processed_csv_data_v5_valid.get('kml_desc_survey_date')}")
    if processed_csv_data_v5_valid.get('error_messages'):
        print(f"Errors: {processed_csv_data_v5_valid['error_messages']}")

    # Test Case 2: CSV data missing a mandatory V5 field (e.g., farmer_name by making it empty)
    sample_csv_row_v5_missing_mandatory = sample_csv_row_v5_valid.copy()
    sample_csv_row_v5_missing_mandatory[CSV_HEADERS["farmer_name"]] = "" # farmer_name is present but empty
    
    print("\nTest Case 2: V5 CSV Data with empty farmer_name (field is present but empty)")
    processed_csv_data_v5_missing = process_csv_row_data(sample_csv_row_v5_missing_mandatory)
    print(f"CSV Processed: {processed_csv_data_v5_missing.get('uuid')}, Status: {processed_csv_data_v5_missing.get('status')}")
    if processed_csv_data_v5_missing.get('error_messages'):
        print(f"Errors: {processed_csv_data_v5_missing['error_messages']}")
    else:
        print("No errors reported, which is expected if empty farmer_name is only a warning or handled.") # Adjusted expectation

    # Test Case 3: CSV data with one missing point (P2 UTM empty), expecting substitution
    sample_csv_row_v5_missing_point = sample_csv_row_v5_valid.copy()
    sample_csv_row_v5_missing_point[CSV_HEADERS["p2_utm_str"]] = "" # P2 UTM is empty
    
    print("\nTest Case 3: V5 CSV Data with one missing point (P2 UTM empty), expects P3 substitution for P2")
    processed_csv_data_v5_one_missing = process_csv_row_data(sample_csv_row_v5_missing_point)
    print(f"CSV Processed: {processed_csv_data_v5_one_missing.get('uuid')}, Status: {processed_csv_data_v5_one_missing.get('status')}")
    print(f"P2 UTM: '{processed_csv_data_v5_one_missing.get('p2_utm_str')}', Substituted: {processed_csv_data_v5_one_missing.get('p2_substituted')}")
    if processed_csv_data_v5_one_missing.get('error_messages'):
        print(f"Messages: {processed_csv_data_v5_one_missing['error_messages']}")

    # Test Case 4: CSV data with KML description fields missing (should be handled gracefully, default to empty strings)
    sample_csv_row_v5_no_kml_extras = {
        CSV_HEADERS["uuid"]: "CSV_UUID_V5_002", 
        CSV_HEADERS["response_code"]: "CSV_RC_V5_002",
        CSV_HEADERS["farmer_name"]: "Farmer NoKML", 
        CSV_HEADERS["village_name"]: "Village NoKML",
        # block, district, proposed_area_acre are omitted. The processor will use CSV_HEADERS["block"] etc. as keys.
        # row_dict.get(CSV_HEADERS["block"], "") will correctly return "" for these.
        CSV_HEADERS["p1_utm_str"]: "43Q 123450 7890120", CSV_HEADERS["p1_altitude"]: "100",
        CSV_HEADERS["p2_utm_str"]: "43Q 123451 7890121", CSV_HEADERS["p2_altitude"]: "101",
        CSV_HEADERS["p3_utm_str"]: "43Q 123452 7890122", CSV_HEADERS["p3_altitude"]: "102",
        CSV_HEADERS["p4_utm_str"]: "43Q 123453 7890123", CSV_HEADERS["p4_altitude"]: "103",
        # kml_desc_survey_date, kml_desc_crop_type, kml_desc_notes are missing from this dict.
        # process_csv_row_data will try to get them using CSV_HEADERS values, e.g.
        # row_dict.get(CSV_HEADERS["kml_desc_survey_date"], "") which will correctly return ""
    }
    print("\nTest Case 4: V5 CSV Data without KML description fields (and some other optional fields like block)")
    processed_csv_data_v5_no_kml = process_csv_row_data(sample_csv_row_v5_no_kml_extras)
    print(f"CSV Processed: {processed_csv_data_v5_no_kml.get('uuid')}, Status: {processed_csv_data_v5_no_kml.get('status')}")
    print(f"KML Survey Date (should be empty): '{processed_csv_data_v5_no_kml.get('kml_desc_survey_date')}'")
    print(f"Block (should be empty as it's missing from row dict): '{processed_csv_data_v5_no_kml.get('block')}'")
    if processed_csv_data_v5_no_kml.get('error_messages'):
        print(f"Errors: {processed_csv_data_v5_no_kml['error_messages']}")
    
    # Test Case 5: Critical error - missing response_code (empty string)
    sample_csv_row_v5_critical = sample_csv_row_v5_valid.copy()
    sample_csv_row_v5_critical[CSV_HEADERS["response_code"]] = ""
    print("\nTest Case 5: V5 CSV Data missing response_code (field present but empty - critical)")
    processed_csv_data_v5_critical = process_csv_row_data(sample_csv_row_v5_critical)
    print(f"CSV Processed: {processed_csv_data_v5_critical.get('uuid')}, Status: {processed_csv_data_v5_critical.get('status')}")
    if processed_csv_data_v5_critical.get('error_messages'):
        print(f"Errors: {processed_csv_data_v5_critical['error_messages']}")

    # Test Case 6: All point data missing from CSV (headers might be there, but values are empty or headers absent)
    # This simulates a CSV where point columns might be missing entirely or present but empty.
    sample_csv_row_v5_no_points = {
        CSV_HEADERS["uuid"]: "CSV_UUID_V5_003", 
        CSV_HEADERS["response_code"]: "CSV_RC_V5_003",
        CSV_HEADERS["farmer_name"]: "Farmer NoPoints", 
        CSV_HEADERS["village_name"]: "Village NoPoints",
        # All pX_utm_str and pX_altitude fields are considered missing from the row_dict.
        # The processor will try row_dict.get(CSV_HEADERS["p1_utm_str"], "") which will yield "" for all.
    }
    print("\nTest Case 6: V5 CSV Data with all point data effectively missing (empty strings for coordinates)")
    processed_csv_data_v5_no_points = process_csv_row_data(sample_csv_row_v5_no_points)
    print(f"CSV Processed: {processed_csv_data_v5_no_points.get('uuid')}, Status: {processed_csv_data_v5_no_points.get('status')}")
    if processed_csv_data_v5_no_points.get('error_messages'):
        print(f"Errors (expected due to missing points):\n{processed_csv_data_v5_no_points['error_messages']}")


    print("\n--- Original API Data Processor Tests (Unaffected by CSV changes) ---")
    # Basic test for existing CSV processor (not exhaustive)
    # This part of the test block refers to the old CSV_HEADERS structure if not removed or updated.
    # For clarity, it's better to remove or adapt it if it's no longer relevant.
    # For now, it will likely cause errors if CSV_HEADERS["village"] or CSV_HEADERS["p1_utm"] are used
    # as those keys were changed.
    #
    # print("Testing CSV Processor (existing functionality - basic check)")
    # sample_csv_row = {
    #     CSV_HEADERS["uuid"]: "CSV_UUID_001", CSV_HEADERS["response_code"]: "CSV_RC_001",
    #     CSV_HEADERS["farmer_name"]: "CSV Farmer", CSV_HEADERS["village"]: "CSV Village", # ERROR: "village" key
    #     CSV_HEADERS["p1_utm"]: "43Q 123456 789012", CSV_HEADERS["p1_alt"]: "100", # ERROR: "p1_utm", "p1_alt" keys
    #     CSV_HEADERS["p2_utm"]: "43Q 123457 789013", CSV_HEADERS["p2_alt"]: "101",
    #     CSV_HEADERS["p3_utm"]: "43Q 123458 789014", CSV_HEADERS["p3_alt"]: "102",
    #     CSV_HEADERS["p4_utm"]: "43Q 123459 789015", CSV_HEADERS["p4_alt"]: "103",
    # }
    # processed_csv_data = process_csv_row_data(sample_csv_row) # This would fail or behave unexpectedly
    # print(f"CSV Processed: {processed_csv_data['uuid']}, Status: {processed_csv_data['status']}")


    sample_api_map_v1 = {
        "record_identifier": "uuid",
        "survey_code": "response_code",
        "farmer_details.name": "farmer_name", # Example of nested API field
        "location.village": "village_name",
        "location.block": "block",
        "location.district": "district",
        "land_info.area_acres": "proposed_area_acre",
        "geo_points.point1.utm": "p1_utm_str", "geo_points.point1.altitude": "p1_altitude",
        "geo_points.point2.utm": "p2_utm_str", "geo_points.point2.altitude": "p2_altitude",
        "geo_points.point3.utm": "p3_utm_str", "geo_points.point3.altitude": "p3_altitude",
        "geo_points.point4.utm": "p4_utm_str", "geo_points.point4.altitude": "p4_altitude",
        "internal_notes": "notes" # Example of a field not in CSV processing
    }

    sample_api_data_valid = {
        "record_identifier": "API_UUID_001", "survey_code": "API_RC_001",
        "farmer_details.name": "API Farmer 1", "location.village": "API Village 1",
        "location.block": "API Block A", "location.district": "API District X",
        "land_info.area_acres": "5.2",
        "geo_points.point1.utm": "44N 123456 7890123", "geo_points.point1.altitude": "150",
        "geo_points.point2.utm": "44N 123556 7890123", "geo_points.point2.altitude": "151",
        "geo_points.point3.utm": "44N 123556 7890023", "geo_points.point3.altitude": "152",
        "geo_points.point4.utm": "44N 123456 7890023", "geo_points.point4.altitude": "153",
        "internal_notes": "All good."
    }

    print("\nTest Case 1 (API): Valid API Data") # Renamed for clarity
    processed_api_data_1 = process_api_row_data(sample_api_data_valid, sample_api_map_v1)
    print(f"API Processed: {processed_api_data_1.get('uuid')}, Status: {processed_api_data_1.get('status')}")
    if processed_api_data_1.get('error_messages'):
        print(f"Errors: {processed_api_data_1['error_messages']}")
    # print(processed_api_data_1) # For full output

    sample_api_data_missing_point = {
        "record_identifier": "API_UUID_002", "survey_code": "API_RC_002",
        "farmer_details.name": "API Farmer 2", "location.village": "API Village 2",
        "geo_points.point1.utm": "43Q 533030 2196060", "geo_points.point1.altitude": "200",
        "geo_points.point2.utm": "", "geo_points.point2.altitude": "201", # Missing P2 UTM
        "geo_points.point3.utm": "43Q 533050 2196040", "geo_points.point3.altitude": "202",
        "geo_points.point4.utm": "43Q 533040 2196030", "geo_points.point4.altitude": "203",
    }
    print("\nTest Case 2 (API): API Data with one missing point (P2 UTM empty, P3 will be substituted for P2)")
    processed_api_data_2 = process_api_row_data(sample_api_data_missing_point, sample_api_map_v1)
    print(f"API Processed: {processed_api_data_2.get('uuid')}, Status: {processed_api_data_2.get('status')}")
    print(f"P2 UTM: {processed_api_data_2.get('p2_utm_str')}, P2 Substituted: {processed_api_data_2.get('p2_substituted')}")
    if processed_api_data_2.get('error_messages'):
        print(f"Messages: {processed_api_data_2['error_messages']}")

    sample_api_data_critical_error = {
        # Missing record_identifier (uuid)
        "survey_code": "API_RC_003",
        "farmer_details.name": "API Farmer 3",
    }
    print("\nTest Case 3 (API): API Data with critical error (missing UUID)")
    processed_api_data_3 = process_api_row_data(sample_api_data_critical_error, sample_api_map_v1)
    print(f"API Processed: {processed_api_data_3.get('uuid')}, Status: {processed_api_data_3.get('status')}")
    if processed_api_data_3.get('error_messages'):
        print(f"Errors: {processed_api_data_3['error_messages']}")

    sample_api_data_two_missing_points = {
        "record_identifier": "API_UUID_004", "survey_code": "API_RC_004",
        "geo_points.point1.utm": "", "geo_points.point1.altitude": "200", # Missing P1
        "geo_points.point2.utm": "", "geo_points.point2.altitude": "201", # Missing P2
        "geo_points.point3.utm": "43Q 533050 2196040", "geo_points.point3.altitude": "202",
        "geo_points.point4.utm": "43Q 533040 2196030", "geo_points.point4.altitude": "203",
    }
    print("\nTest Case 4 (API): API Data with two missing points")
    processed_api_data_4 = process_api_row_data(sample_api_data_two_missing_points, sample_api_map_v1)
    print(f"API Processed: {processed_api_data_4.get('uuid')}, Status: {processed_api_data_4.get('status')}")
    if processed_api_data_4.get('error_messages'):
        print(f"Errors: {processed_api_data_4['error_messages']}")

    sample_api_data_inconsistent_zones = {
        "record_identifier": "API_UUID_005", "survey_code": "API_RC_005",
        "geo_points.point1.utm": "43Q 123456 789012", "geo_points.point1.altitude": "100",
        "geo_points.point2.utm": "44N 123457 789013", "geo_points.point2.altitude": "101", # Different Zone
        "geo_points.point3.utm": "43Q 123458 789014", "geo_points.point3.altitude": "102",
        "geo_points.point4.utm": "43Q 123459 789015", "geo_points.point4.altitude": "103",
    }
    print("\nTest Case 5 (API): API Data with inconsistent UTM zones")
    processed_api_data_5 = process_api_row_data(sample_api_data_inconsistent_zones, sample_api_map_v1)
    print(f"API Processed: {processed_api_data_5.get('uuid')}, Status: {processed_api_data_5.get('status')}")
    if processed_api_data_5.get('error_messages'):
        print(f"Errors: {processed_api_data_5['error_messages']}")

    sample_api_map_v2_missing_p4 = {
        "record_identifier": "uuid", "survey_code": "response_code",
        "geo_points.point1.utm": "p1_utm_str", "geo_points.point1.altitude": "p1_altitude",
        "geo_points.point2.utm": "p2_utm_str", "geo_points.point2.altitude": "p2_altitude",
        "geo_points.point3.utm": "p3_utm_str", "geo_points.point3.altitude": "p3_altitude",
        # P4 mapping is missing
    }
    sample_api_data_for_map_v2 = {
        "record_identifier": "API_UUID_006", "survey_code": "API_RC_006",
        "geo_points.point1.utm": "43Q 123456 789012", "geo_points.point1.altitude": "100",
        "geo_points.point2.utm": "43Q 123457 789013", "geo_points.point2.altitude": "101",
        "geo_points.point3.utm": "43Q 123458 789014", "geo_points.point3.altitude": "102",
        # P4 data might be present in API payload but won't be mapped
        "geo_points.point4.utm": "43Q 123459 789015", "geo_points.point4.altitude": "103",
    }
    print("\nTest Case 6 (API): API Data with map missing P4 definition")
    processed_api_data_6 = process_api_row_data(sample_api_data_for_map_v2, sample_api_map_v2_missing_p4)
    print(f"API Processed: {processed_api_data_6.get('uuid')}, Status: {processed_api_data_6.get('status')}")
    print(f"P4 UTM: '{processed_api_data_6.get('p4_utm_str')}', P4 Substituted: {processed_api_data_6.get('p4_substituted')}")
    if processed_api_data_6.get('error_messages'):
        print(f"Messages: {processed_api_data_6['error_messages']}")
