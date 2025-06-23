"""
Utility functions for KML manipulation, primarily for merging KML files.
"""
import os
import copy # Added for deepcopy
from lxml import etree

KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
# For KML, the namespace is often the default namespace, so `None` is the key.
# However, lxml might require an explicit prefix for XPath if the KML files use it.
# We'll try with default first, and then with an explicit 'kml' prefix if needed for XPath.
NSMAP_DEFAULT = {None: KML_NAMESPACE}
NSMAP_PREFIXED = {'kml': KML_NAMESPACE}

def merge_kml_files(input_kml_paths: list, output_kml_path: str) -> bool:
    """
    Merges Placemark elements from multiple KML files into a single new KML file.

    Args:
        input_kml_paths: A list of paths to the input KML files.
        output_kml_path: The path where the merged KML file will be saved.

    Returns:
        True if merging was successful and at least one placemark was merged, False otherwise.
    """
    if not input_kml_paths:
        print("No input KML files provided.")
        return False

    # Create root <kml> and <Document> elements for the new merged file
    # Using QName for clarity and to ensure correct namespace handling from the start.
    # Explicitly pass nsmap to the root element.
    merged_root = etree.Element(etree.QName(KML_NAMESPACE, "kml"), nsmap=NSMAP_DEFAULT)
    # SubElements inherit nsmap from parent. QName handles the tag's namespace.
    # Pylance might be strict; if errors persist for SubElement,
    # one could pass attrib={} or attrib=None if that's what it expects for empty attributes.
    # Using string representation for namespaced tag: "{namespace}localname"
    # Setting attrib=None and nsmap=None explicitly. nsmap=None allows inheritance from parent.
    merged_doc_element = etree.SubElement(merged_root, f"{{{KML_NAMESPACE}}}Document", attrib=None, nsmap=None)
    
    # Optional: Add a name to the document
    # Using string representation for namespaced tag and setting attrib=None, nsmap=None explicitly.
    name_element = etree.SubElement(merged_doc_element, f"{{{KML_NAMESPACE}}}name", attrib=None, nsmap=None)
    name_element.text = "Consolidated KML"

    placemark_count = 0
    for kml_path in input_kml_paths:
        if not os.path.exists(kml_path):
            print(f"Warning: KML file not found, skipping: {kml_path}")
            continue
        try:
            # remove_blank_text can help with pretty_print later
            parser = etree.XMLParser(remove_blank_text=True, recover=True) # recover=True for robustness
            tree = etree.parse(kml_path, parser)
            root = tree.getroot()
            
            # Attempt to find Placemarks using an explicit prefix for the KML namespace.
            # This is more robust for XPath engines that do not support empty prefixes for default namespaces.
            # The `.//` ensures we find Placemarks at any level within the KML structure (e.g., inside Folders).
            placemarks = root.xpath('.//kml:Placemark', namespaces=NSMAP_PREFIXED)
            
            if not placemarks:
                # This block can be entered if no kml:Placemark tags are found using the kml prefix.
                # It might be useful to log or handle cases where KMLs might not use the 'kml' prefix
                # or have a different structure, though standard KMLs should match.
                # For now, if no placemarks are found with the 'kml:' prefix, the loop will be skipped.
                pass # Or print a specific message: print(f"No 'kml:Placemark' found in {kml_path}")

            for placemark in placemarks:
                # Append a deep copy of the placemark to the merged document.
                # This is important if the original elements are modified or if the source tree is not kept.
                # Using copy.deepcopy() is cleaner than tostring/fromstring for lxml elements.
                merged_doc_element.append(copy.deepcopy(placemark))
                placemark_count += 1
        except etree.XMLSyntaxError as e:
            print(f"Error parsing KML file {kml_path}: {e}")
            continue
        except Exception as e: # Catch other potential errors during file processing
            print(f"An unexpected error occurred while processing {kml_path}: {e}")
            continue
    
    if placemark_count > 0:
        try:
            # Create an ElementTree from the merged root element
            merged_tree = etree.ElementTree(merged_root)
            # Write the merged KML to the output file
            merged_tree.write(output_kml_path, 
                              pretty_print=True, 
                              xml_declaration=True, 
                              encoding='UTF-8')
            print(f"Successfully merged {placemark_count} placemarks into {output_kml_path}")
            return True
        except Exception as e:
            print(f"Error writing merged KML to {output_kml_path}: {e}")
            return False
    else:
        print("No placemarks found in the provided KML files to merge.")
        return False
