# ----------------------------------------------------------------------
# File: DilasaKMLTool_v4/core/data_processor.py
# ----------------------------------------------------------------------
import re

# Expected CSV Headers - Centralized here for data_processor
# The main UI part will also need to be aware of these if it directly interacts with CSVs
# or if it needs to display data based on these specific field names.
CSV_HEADERS = {
    "uuid": "UUID (use as the file name)",
    "response_code": "Response Code",
    "farmer_name": "Name of the Farmer",
    "village": "Village Name",
    "block": "Block",
    "district": "District",
    "area": "Proposed Area (Acre)",
    "p1_utm": "Point 1 (UTM)", "p1_alt": "Point 1 (altitude)",
    "p2_utm": "Point 2 (UTM)", "p2_alt": "Point 2 (altitude)",
    "p3_utm": "Point 3 (UTM)", "p3_alt": "Point 3 (altitude)",
    "p4_utm": "Point 4 (UTM)", "p4_alt": "Point 4 (altitude)",
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
    Processes a single row dictionary (from csv.DictReader).
    Cleans BOM from keys if present, extracts data based on CSV_HEADERS,
    validates points, attempts substitution for one missing point.
    Returns a dictionary flattened and ready for database insertion,
    including 'status' and 'error_messages' (as a string).
    """
    # Clean BOM from all keys in the input dictionary.
    # This ensures that lookups using CSV_HEADERS (which are clean) will work.
    row_dict = {k.lstrip('\ufeff'): v for k, v in row_dict_from_reader.items()}

    processed_for_db = {
        "uuid": row_dict.get(CSV_HEADERS["uuid"], "").strip(),
        "response_code": row_dict.get(CSV_HEADERS["response_code"], "").strip(),
        "farmer_name": row_dict.get(CSV_HEADERS["farmer_name"], "").strip(),
        "village_name": row_dict.get(CSV_HEADERS["village"], "").strip(), # Corrected key from "Village Name"
        "block": row_dict.get(CSV_HEADERS["block"], "").strip(),
        "district": row_dict.get(CSV_HEADERS["district"], "").strip(),
        "proposed_area_acre": row_dict.get(CSV_HEADERS["area"], "").strip(),
        "status": "valid_for_kml", # Default status
        # error_messages will be populated as a string later
    }
    
    error_accumulator = [] # Internal list to gather error messages

    if not processed_for_db["uuid"]:
        error_accumulator.append(f"UUID is empty or missing. Expected header: '{CSV_HEADERS['uuid']}'. Available headers in row: {list(row_dict.keys())}")
    if not processed_for_db["response_code"]:
        error_accumulator.append(f"Response Code is empty or missing. Expected header: '{CSV_HEADERS['response_code']}'. Available headers in row: {list(row_dict.keys())}")

    if not processed_for_db["uuid"] or not processed_for_db["response_code"]:
        processed_for_db["status"] = "error_missing_identifiers"
        if not any("empty or missing" in msg for msg in error_accumulator): # Add general if specific not present
             error_accumulator.append("Critical: Missing UUID or Response Code.")
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
        utm_header = CSV_HEADERS[f"p{i}_utm"]
        alt_header = CSV_HEADERS[f"p{i}_alt"]
        
        utm_str_val = row_dict.get(utm_header, "").strip()
        alt_str_val = row_dict.get(alt_header, "0").strip() # Default to "0" if missing
        
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
