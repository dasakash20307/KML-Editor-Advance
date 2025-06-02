import unittest
import xml.etree.ElementTree as ET # For ET.ParseError
from ui.widgets.map_view_widget import MapViewWidget # To access the static method

# Basic KML Structure for tests
KML_WRAPPER_START = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Document</name>
"""
KML_WRAPPER_END = """
  </Document>
</kml>
"""

# Placemark with Polygon
KML_POLYGON_PLACEMARK = """
    <Placemark>
      <name>Test Polygon Placemark</name>
      <description>Description for Polygon Placemark</description>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -122.365662,37.826760,0 -122.365200,37.826300,0 -122.364417,37.826917,0 -122.365662,37.826760,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
"""

# Placemark with Point
KML_POINT_PLACEMARK = """
    <Placemark>
      <name>Test Point Placemark</name>
      <description>Description for Point Placemark</description>
      <Point>
        <coordinates>-122.082203,37.422289,0</coordinates>
      </Point>
    </Placemark>
"""

class TestKMLParsing(unittest.TestCase):

    def test_valid_polygon_kml(self):
        kml_content = KML_WRAPPER_START + KML_POLYGON_PLACEMARK + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Parsing error occurred: {error}")
        self.assertIsNotNone(coords, "Coordinates should not be None for valid polygon KML.")
        self.assertEqual(desc, "Description for Polygon Placemark")
        self.assertFalse(is_point, "Should be identified as Polygon, not Point.")
        expected_coords = [
            (37.826760, -122.365662), (37.826300, -122.365200),
            (37.826917, -122.364417), (37.826760, -122.365662)
        ]
        self.assertEqual(coords, expected_coords)

    def test_valid_point_kml(self):
        kml_content = KML_WRAPPER_START + KML_POINT_PLACEMARK + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Parsing error occurred: {error}")
        self.assertIsNotNone(coords, "Coordinates should not be None for valid point KML.")
        if coords is not None: # Explicit check before len()
            self.assertEqual(len(coords), 1, "Point KML should have one coordinate tuple.")
        # If coords is None, assertIsNotNone should have failed. This is an extra guard.
        self.assertEqual(desc, "Description for Point Placemark")
        self.assertTrue(is_point, "Should be identified as Point.")
        expected_coords = [(37.422289, -122.082203)]
        self.assertEqual(coords, expected_coords)

    def test_description_document_level(self):
        kml_doc_desc = """
    <description>Document Level Description Test</description>
"""
        kml_placemark_no_desc = """
    <Placemark>
      <name>Placemark Without Description</name>
      <Point><coordinates>-1,1,0</coordinates></Point>
    </Placemark>
"""
        kml_content = KML_WRAPPER_START + kml_doc_desc + kml_placemark_no_desc + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error)
        self.assertEqual(desc, "Document Level Description Test",
                         "Should use Document description if Placemark description is missing.")

    def test_description_placemark_priority(self):
        kml_doc_desc_override = """
    <description>THIS SHOULD BE OVERRIDDEN by Placemark</description>
"""
        kml_content = KML_WRAPPER_START + kml_doc_desc_override + KML_POLYGON_PLACEMARK + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error)
        self.assertEqual(desc, "Description for Polygon Placemark",
                         "Placemark description should take priority over Document description.")

    def test_malformed_kml_invalid_xml(self):
        kml_content = "<kml><Document><Placemark></Placemark></Docu ment></kml>" # Malformed </Docu ment>
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNotNone(error, "Error should be reported for malformed KML.")
        if error is not None: # Explicit check before assertIn
            self.assertIn("XML ParseError", error, "Error message should indicate XML parsing issue.")
        # If error is None, assertIsNotNone should have failed. This is an extra guard.
        self.assertIsNone(coords)
        # Description might be the default error string or None, depending on implementation
        self.assertEqual(desc, "Error parsing KML.")


    def test_kml_missing_coordinates_tag_polygon(self):
        kml_no_coords_polygon = """
    <Placemark>
      <name>Polygon No Coords</name>
      <description>Polygon missing coordinates tag</description>
      <Polygon><outerBoundaryIs><LinearRing></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
"""
        kml_content = KML_WRAPPER_START + kml_no_coords_polygon + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Error occurred: {error}")
        self.assertIsNone(coords, "Coordinates should be None or empty list if <coordinates> tag is missing.")
        self.assertEqual(desc, "Polygon missing coordinates tag")
        self.assertFalse(is_point) # It found a Polygon structure, even if coords are missing

    def test_kml_missing_coordinates_tag_point(self):
        kml_no_coords_point = """
    <Placemark>
      <name>Point No Coords</name>
      <description>Point missing coordinates tag</description>
      <Point></Point>
    </Placemark>
"""
        kml_content = KML_WRAPPER_START + kml_no_coords_point + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Error occurred: {error}")
        self.assertIsNone(coords, "Coordinates should be None or empty list if <coordinates> tag is missing.")
        self.assertEqual(desc, "Point missing coordinates tag")
        self.assertTrue(is_point) # It found a Point structure

    def test_kml_empty_coordinates_string(self):
        kml_empty_coords_str = """
    <Placemark>
      <name>Empty Coords String</name>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>  </coordinates></LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
"""
        kml_content = KML_WRAPPER_START + kml_empty_coords_str + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Error occurred: {error}")
        self.assertIsNone(coords, "Coordinates should be None or empty if <coordinates> string is empty/whitespace.")


    def test_kml_missing_description_tag(self):
        kml_no_desc_placemark = """
    <Placemark>
      <name>Placemark with No Description Tag</name>
      <Point><coordinates>-2,2,0</coordinates></Point>
    </Placemark>
"""
        # KML_WRAPPER_START already has a <Document><name>, but no <description> at Document level by default.
        # To test this properly, ensure no fallback to a Document description if Placemark one is missing.
        kml_doc_no_desc = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Test Document No Desc</name>
""" # KML_WRAPPER_START without its own <description>
        kml_content = kml_doc_no_desc + kml_no_desc_placemark + KML_WRAPPER_END
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)

        self.assertIsNone(error, f"Error occurred: {error}")
        self.assertEqual(desc, "No description available",
                         "Should return default description if no tag is found in Placemark or Document.")

    def test_kml_with_namespace_prefix_everywhere(self):
        kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml:kml xmlns:kml="http://www.opengis.net/kml/2.2">
  <kml:Document>
    <kml:name>Test Document Prefixed</kml:name>
    <kml:Placemark>
      <kml:name>Test Polygon Prefixed</kml:name>
      <kml:description>Description for Prefixed Polygon</kml:description>
      <kml:Polygon>
        <kml:outerBoundaryIs>
          <kml:LinearRing>
            <kml:coordinates>
              -10,10,0 -11,10,0 -11,11,0 -10,10,0
            </kml:coordinates>
          </kml:LinearRing>
        </kml:outerBoundaryIs>
      </kml:Polygon>
    </kml:Placemark>
  </kml:Document>
</kml:kml>"""
        coords, desc, is_point, error = MapViewWidget._parse_kml_data(kml_content)
        self.assertIsNone(error, f"Parsing error with prefixed KML: {error}")
        self.assertEqual(desc, "Description for Prefixed Polygon")
        self.assertFalse(is_point)
        expected_coords = [(10.0, -10.0), (10.0, -11.0), (11.0, -11.0), (10.0, -10.0)]
        self.assertEqual(coords, expected_coords)

if __name__ == '__main__':
    unittest.main()
