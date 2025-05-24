import ee

# Global variable to track GEE initialization status
ee_initialized = False

def initialize_ee():
    """
    Initializes the Earth Engine library.

    Tries to use the high-volume endpoint first (with a connection test),
    then falls back to the standard initialization (with a connection test).
    Remembers if initialization was successful to avoid re-trying.
    Catches GEE exceptions and prints helpful messages with a 'CORE_GEE:' prefix.

    Returns:
        bool: True if GEE was initialized successfully or is already initialized, False otherwise.
    """
    global ee_initialized

    if ee_initialized:
        print("CORE_GEE: Google Earth Engine is already initialized.")
        return True

    # Attempt 1: High-volume endpoint
    try:
        print("CORE_GEE: Attempting to initialize Google Earth Engine (high-volume endpoint)...")
        ee.Initialize(opt_url='https://earthengine-highvolume.googleapis.com', quiet=True)
        # Test connectivity by getting the size of a small image collection
        # This confirms that requests can be made and results returned.
        test_collection = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT').limit(1)
        _ = test_collection.size().getInfo() # Should return 1 if successful
        print("CORE_GEE: Google Earth Engine initialized successfully and tested (high-volume endpoint).")
        ee_initialized = True
        return True
    except Exception as e_high_volume:
        print(f"CORE_GEE: Failed to initialize or test with high-volume endpoint: {e_high_volume}")
        print("CORE_GEE: Falling back to standard Earth Engine initialization...")

    # Attempt 2: Standard endpoint
    try:
        print("CORE_GEE: Attempting to initialize Google Earth Engine (standard endpoint)...")
        ee.Initialize(quiet=True)
        # Test connectivity
        test_collection = ee.ImageCollection('LANDSAT/LC08/C01/T1_RT').limit(1)
        _ = test_collection.size().getInfo() # Should return 1 if successful
        print("CORE_GEE: Google Earth Engine initialized successfully and tested (standard endpoint).")
        ee_initialized = True
        return True
    except ee.EEException as e_standard_ee: # ee.EEException is the standard GEE exception
        print(f"CORE_GEE: Earth Engine standard initialization failed (EEException): {e_standard_ee}")
        print("CORE_GEE: Please ensure you have authenticated with Google Earth Engine (e.g., run 'earthengine authenticate').")
        ee_initialized = False
        return False
    except Exception as e_standard_other:
        print(f"CORE_GEE: Earth Engine standard initialization failed (Other Exception): {e_standard_other}")
        ee_initialized = False
        return False

if __name__ == '__main__':
    print("MAIN_TEST: Running GEE Handler directly to test initialization...")
    initialized_successfully = initialize_ee()
    if initialized_successfully:
        print("MAIN_TEST: GEE Initialization test: Succeeded.")
    else:
        print("MAIN_TEST: GEE Initialization test: Failed.")
