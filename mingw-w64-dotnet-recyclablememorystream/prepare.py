import json, sys
from pathlib import Path
import xml.etree.ElementTree as E
kind=sys.argv[1]; root=Path(sys.argv[2]); removed=[]
for path in root.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.winmd','.nupkg','.obj','.lib','.a','.pdb','.resources'}:
        removed.append(str(path.relative_to(root)));path.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
if kind=='recyclablememorystream':
    files=[root/'src/Microsoft.IO.RecyclableMemoryStream.csproj']; expected={'Microsoft.SourceLink.GitHub'}; target='net8.0'
elif kind=='notifyicon':
    files=[root/'src/Directory.Build.props']; expected={'Nerdbank.GitVersioning','Microsoft.SourceLink.GitHub'};target='net8.0-windows'
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
