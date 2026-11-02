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
if kind=='toolkit-highperformance':
    # SourceLink, StyleCop and Nerdbank.GitVersioning are build-time only; versions are passed explicitly instead of computed from git history.
    files=[root/'Directory.Build.props',root/'Microsoft.Toolkit.HighPerformance/Microsoft.Toolkit.HighPerformance.csproj']
    expected={'Microsoft.SourceLink.AzureRepos.Git','Microsoft.SourceLink.GitHub','StyleCop.Analyzers','Nerdbank.GitVersioning'};target='net8.0'
    # Only the net8.0 targeting pack is available: build the net5.0 flavour (the closest original TFM) by giving net8.0
    # the exact per-TFM constants upstream's net5.0 build gets (NET5_0 is implicit there; it gates the .NET 5 code paths).
    project=files[1];text=project.read_text(encoding='utf-8-sig')
    old=""" <When Condition=" '$(TargetFramework)' == 'net5.0' ">
      <PropertyGroup>
        <DefineConstants>NETSTANDARD2_1_OR_GREATER;SPAN_RUNTIME_SUPPORT</DefineConstants>"""
    assert text.count(old)==1
    text=text.replace(old,old.replace("'net5.0'","'net8.0'").replace('SPAN_RUNTIME_SUPPORT<','SPAN_RUNTIME_SUPPORT;NET5_0<'))
    # net8.0's reference assemblies declare Unsafe.AsRef/MemoryMarshal.CreateReadOnlySpan with 'ref readonly' parameters,
    # which C# 9 cannot call with 'in' arguments (CS8773); compile with net8.0's default language version instead.
    assert text.count('<LangVersion>9.0</LangVersion>')==1
    project.write_text(text.replace('<LangVersion>9.0</LangVersion>','<LangVersion>12.0</LangVersion>'),encoding='utf-8')
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
