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
if kind=='recyclablememorystream':
    files=[root/'src/Microsoft.IO.RecyclableMemoryStream.csproj']; expected={'Microsoft.SourceLink.GitHub'}; target='net8.0'
elif kind=='reactive':
    files=[root/'Rx.NET/Source/Directory.build.props'];expected={'Nerdbank.GitVersioning','Microsoft.SourceLink.GitHub'};target='net8.0'
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

if kind=='reactive':
    file=root/'Rx.NET/Source/src/System.Reactive/System.Reactive.nuspec'
    tree=E.parse(file)
    for parent in tree.iter():
        for child in list(parent):
            tag=child.tag.split('}')[-1]
            if tag=='group' and child.get('targetFramework')!='net8.0':parent.remove(child)
            elif tag=='frameworkAssemblies':parent.remove(child)
            elif tag=='file':
                source=child.get('src','')
                if ('$outputpath$' in source or '$refassemblypath$' in source) and 'net8.0\\' not in source:parent.remove(child)
                elif '$analyzerassemblypath$' in source:parent.remove(child)
    tree.write(file,encoding='utf-8',xml_declaration=True)

if kind=='reactive':
    count=0
    for file in (root/'Rx.NET/Source/src/System.Reactive/Linq/Observable').glob('FromEvent*.cs'):
        text=file.read_text(encoding='utf-8-sig')
        for expression in ('nameof(Action<,>.Invoke)','nameof(Action<>.Invoke)'):
            count+=text.count(expression);text=text.replace(expression,'nameof(Action.Invoke)')
        file.write_text(text)
    assert count==4,count
