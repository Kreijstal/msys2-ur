import json, sys
from pathlib import Path
import xml.etree.ElementTree as E
kind=sys.argv[1]; root=Path(sys.argv[2]); removed=[]
for path in root.rglob('*'):
    if path.is_file() and path.suffix.lower() in {'.dll','.exe','.winmd','.nupkg','.obj','.lib','.a','.pdb','.resources'}:
        removed.append(str(path.relative_to(root)));path.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
for nested in root.rglob('global.json'):nested.unlink()
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
if kind=='bouncycastle':
    files=[root/'crypto/src/BouncyCastle.Crypto.csproj'];expected={'Microsoft.NETFramework.ReferenceAssemblies','Microsoft.SourceLink.GitHub','Nerdbank.GitVersioning'};target='net8.0'
    # Nerdbank.GitVersioning hook targets and the Publish-only Authenticode signfile.bat step are not part of the offline build.
    (root/'Directory.Build.props').write_text('<Project />\n')
else:files=[];expected=set();target='net8.0'
found=set()
for file in files:
    tree=E.parse(file)
    for group in tree.iter():
        for element in list(group):
            if element.tag=='PackageReference' and element.get('Include') in expected:
                found.add(element.get('Include'));group.remove(element)
            if element.tag=='TargetFrameworks':element.text=target
            if kind=='bouncycastle' and element.tag=='Target' and element.get('Name') in {'FixAssemblyAttributes','SignAssemblies'}:group.remove(element)
    tree.write(file,encoding='utf-8',xml_declaration=True)
assert found==expected,(found,expected)
print('Prepared original source project; removed',len(removed),'binary inputs and build-only package references',sorted(found))
