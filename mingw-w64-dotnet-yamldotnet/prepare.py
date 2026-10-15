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
if kind=='yamldotnet':
    # Nullable is a source-only attribute polyfill for pre-netcoreapp3.0 targets; net8.0 has the attributes in-box.
    files=[root/'YamlDotNet/YamlDotNet.csproj'];expected={'Nullable'};target='net8.0'
    # Upstream's tools/build (Bullseye/GitVersion) renders AssemblyInfo.template; do the same with the 16.3.0 release values.
    props=root/'YamlDotNet/Properties';text=(props/'AssemblyInfo.template').read_text(encoding='utf-8-sig')
    for key,value in {'assemblyVersion':'16.0.0.0','assemblyFileVersion':'16.3.0.0','assemblyInformationalVersion':'16.3.0'}.items():
        assert text.count(f'<%{key}%>')==1;text=text.replace(f'<%{key}%>',value)
    (props/'AssemblyInfo.cs').write_text(text,encoding='utf-8')
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
