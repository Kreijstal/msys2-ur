"""Retarget the original PowerShell MarkdownRender project for the offline SDK."""
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
path = root / "src/Microsoft.PowerShell.MarkdownRender.csproj"
tree = ET.parse(path)
framework = tree.find(".//TargetFramework")
assert framework.text == "netstandard2.0"
framework.text = "net8.0"
reference = tree.find(".//PackageReference[@Include='Markdig.Signed']")
assert reference is not None and reference.get("Version") == "0.31.0"
# PowerShell supplies Markdig 0.33.0; use and declare that exact packaged library.
reference.set("Version", "[0.33.0]")
assets = reference.find("PrivateAssets")
assert assets is not None and assets.text == "All"
reference.remove(assets)
tree.write(path, encoding="utf-8", xml_declaration=True)
