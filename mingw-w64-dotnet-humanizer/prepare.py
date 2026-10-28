"""Remove versioning/source-link build tools from the original Humanizer project."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

root = Path(sys.argv[1])
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
path = root / "src/Directory.build.props"
tree = ET.parse(path)
expected = {"Nerdbank.GitVersioning", "Microsoft.SourceLink.GitHub"}
found = set()
for group in tree.iter():
    for element in list(group):
        if element.tag == "PackageReference" and element.get("Include") in expected:
            found.add(element.get("Include"))
            group.remove(element)
assert found == expected, (found, expected)
tree.write(path, encoding="utf-8", xml_declaration=True)
