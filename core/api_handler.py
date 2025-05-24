# File: DilasaKMLTool_v4/core/api_handler.py
# ----------------------------------------------------------------------
import requests
from io import StringIO # To treat string as a file for csv.DictReader
import csv # For csv.DictReader

# No CSV_HEADERS needed here if process_csv_row_data handles it

def fetch_data_from_mwater_api(api_url, source_title="mWater API"):
    """
    Fetches data from the given mWater API URL.
    Decodes the response using 'utf-8-sig' to handle BOM.
    Returns a list of row dictionaries (from csv.DictReader) or None on error.
    Also returns any error message.
    """
    print(f"CORE: Fetching data from {source_title} ({api_url})...")
    try:
        response = requests.get(api_url, timeout=30) # 30-second timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

        # Decode with 'utf-8-sig' to handle BOM from API response bytes.
        # This should ensure csv.DictReader gets clean fieldnames.
        try:
            text_data = response.content.decode('utf-8-sig')
        except UnicodeDecodeError:
            print(f"CORE: API Response for {source_title} not utf-8-sig. Trying default (requests' detected) decoding.")
            text_data = response.text # Fallback to requests' default decoding
        
        # Basic check if data looks like CSV (optional, but can help)
        # content_type = response.headers.get('content-type','').lower()
        # if 'csv' not in content_type and (not text_data or not text_data.strip()):
        #     return None, f"Response from {source_title} does not appear to be CSV or is empty. Content-Type: '{content_type}'."

        csv_file_like_object = StringIO(text_data)
        reader = csv.DictReader(csv_file_like_object)
        
        if not reader.fieldnames:
            return None, f"No CSV headers (fieldnames) found in response from {source_title}."
            
        row_list = list(reader) # Consume the reader into a list of dictionaries
        return row_list, None # Success: return list of rows, no error message

    except requests.exceptions.RequestException as e:
        return None, f"Network or HTTP error fetching from {source_title}: {e}"
    except UnicodeDecodeError as e:
        return None, f"Unicode decoding error for {source_title} (tried utf-8-sig). Response might not be UTF-8. Error: {e}"
    except Exception as e: # Catch other potential errors during processing
        return None, f"Unexpected error processing data from {source_title}: {e}"
