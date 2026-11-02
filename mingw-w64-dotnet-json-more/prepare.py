"""Build each original json-everything project against packaged dependencies."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

kind, directory = sys.argv[1:]
root = Path(directory)
projects = {"more": "Json.More", "pointer": "JsonPointer", "schema": "JsonSchema"}
removed = []
for path in root.rglob("*"):
    if path.is_file() and path.suffix.lower() in {
        ".dll", ".exe", ".winmd", ".nupkg", ".obj", ".lib", ".a", ".pdb",
        ".resources", ".so", ".dylib",
    }:
        removed.append(str(path.relative_to(root)))
        path.unlink()
(root / "removed-binaries.json").write_text(json.dumps(sorted(removed), indent=2) + "\n")
for path in root.rglob("global.json"):
    path.unlink()
(root / "global.json").write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
name = projects[kind]
path = root / "src" / name / (name + ".csproj")
tree = ET.parse(path)
expected = {"PolySharp", "Microsoft.SourceLink.GitHub"}
replacements = {
    "..\\Json.More\\Json.More.csproj": ("Json.More.Net", "[2.0.2]"),
    "..\\JsonPointer\\JsonPointer.csproj": ("JsonPointer.Net", "[5.0.2]"),
}
found = set()
for group in tree.iter():
    for element in list(group):
        if element.tag == "PackageReference" and element.get("Include") in expected:
            found.add(element.get("Include"))
            group.remove(element)
        if element.tag == "ProjectReference":
            package, version = replacements[element.get("Include")]
            element.tag = "PackageReference"
            element.set("Include", package)
            element.set("Version", version)
assert found == expected, (found, expected)
tree.write(path, encoding="utf-8", xml_declaration=True)
print("Removed build-only references:", sorted(found), "; binary inputs:", len(removed))
