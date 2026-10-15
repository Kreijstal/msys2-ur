import json, sys
from pathlib import Path
import xml.etree.ElementTree as E
kind=sys.argv[1]; root=Path(sys.argv[2]); removed=[]
for path in root.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.winmd','.nupkg','.obj','.lib','.a','.pdb','.resources','.so','.dylib'}:
        removed.append(str(path.relative_to(root)));path.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
for nested in root.rglob('global.json'):nested.unlink()
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
if kind=='bcnencoder':
    # SourceLink is build-time only. Microsoft.Toolkit.HighPerformance 7.0.2 stays and restores from the offline library-packs feed.
    files=[root/'BCnEnc.Net/BCnEncoder.csproj'];expected={'Microsoft.SourceLink.GitHub'};target='net8.0'
    text=files[0].read_text(encoding='utf-8-sig');old='<TargetFramework>netstandard2.1</TargetFramework>'
    assert text.count(old)==1
    files[0].write_text(text.replace(old,'<TargetFramework>net8.0</TargetFramework>'),encoding='utf-8')
    # netstandard2.1 has no System.Half, so upstream's 'using System; using BCnEncoder.Shared;' files are unambiguous there;
    # on net8.0 CS0104 arises. A compilation-unit alias takes precedence over namespace imports and keeps upstream's type.
    (root/'BCnEnc.Net/MsysHalfAlias.cs').write_text('global using Half = BCnEncoder.Shared.Half;\n')
else:files=[];expected=set();target='net8.0'
found=set()
for file in files:
    tree=E.parse(file)
    for group in tree.iter():
        for element in list(group):
            if element.tag=='PackageReference' and element.get('Include') in expected:
                found.add(element.get('Include'));group.remove(element)
            if element.tag=='TargetFrameworks':element.text=target
    tree.write(file,encoding='utf-8',xml_declaration=True)
assert found==expected,(found,expected)
print('Prepared original source project; removed',len(removed),'binary inputs and build-only package references',sorted(found))
