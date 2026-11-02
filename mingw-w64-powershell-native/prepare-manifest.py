#!/usr/bin/env python3
"""Expose the same provider data in the instrumentationManifest XML envelope."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

source, output = map(Path, sys.argv[1:])
ns = "http://schemas.microsoft.com/win/2004/08/events"
asm = "urn:schemas-microsoft-com:asm.v3"
tree = ET.parse(source).getroot()
events = tree.find(f".//{{{ns}}}events")
localization = tree.find(f"{{{asm}}}localization")
assert events is not None and localization is not None
for element in localization.iter():
    assert element.tag.startswith("{" + asm + "}")
    element.tag = "{" + ns + "}" + element.tag.split("}", 1)[1]
ET.register_namespace("", ns)
root = ET.Element("{" + ns + "}instrumentationManifest", {
    "xmlns:win": "http://manifests.microsoft.com/win/2004/08/windows/events",
    "xmlns:trace": "http://schemas.microsoft.com/win/2004/08/events/trace",
    "xmlns:xs": "http://www.w3.org/2001/XMLSchema",
})
ET.SubElement(root, "{" + ns + "}instrumentation").append(events)
root.append(localization)
ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
