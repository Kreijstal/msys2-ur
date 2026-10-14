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
elif kind=='svg':
    files=[root/'Source/Svg.csproj',root/'Generators/Svg.Generators.csproj'];expected={'Nerdbank.GitVersioning','Microsoft.SourceLink.GitHub','System.Memory','System.Drawing.Common','runtime.osx.10.10-x64.CoreCompat.System.Drawing','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.Analyzers'};target='net8.0-windows'
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

if kind=='svg':
    file=root/'Generators/Svg.Generators.csproj';tree=E.parse(file);group=E.SubElement(tree.getroot(),'ItemGroup')
    for name in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']:
        ref=E.SubElement(group,'Reference',Include=name)
        E.SubElement(ref,'HintPath').text='$(MSBuildBinPath)/Roslyn/bincore/'+name+'.dll'
        E.SubElement(ref,'Private').text='false'
    tree.write(file,encoding='utf-8',xml_declaration=True)

if kind=='svg':
    file=root/'Source/Svg.csproj';tree=E.parse(file);props=E.SubElement(tree.getroot(),'PropertyGroup')
    E.SubElement(props,'PublicSign').text='true'
    tree.write(file,encoding='utf-8',xml_declaration=True)
