import json, re, sys
from pathlib import Path
import xml.etree.ElementTree as E
root=Path(sys.argv[1]); version=sys.argv[2]; removed=[]
# Prebuilt binaries: native libraries, executables, packages, and the
# precompiled effect (.mgfxo) and content (.xnb) files; the stock effects are
# rebuilt from their .fx sources by the source-built mgfxc in build().
binary={'.dll','.exe','.winmd','.nupkg','.obj','.lib','.a','.pdb','.so','.dylib','.jar','.mgfxo','.xnb','.resources'}
for path in sorted(root.rglob('*')):
    if path.is_file() and path.suffix.lower() in binary:
        removed.append(str(path.relative_to(root)));path.unlink()
(root/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
for nested in root.rglob('global.json'):nested.unlink()
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')

def edit_xml(file, refs, targets=(), framework=None):
    text=file.read_text(encoding='utf-8-sig')
    tree=E.ElementTree(E.fromstring(text))
    found=set()
    for group in tree.iter():
        for element in list(group):
            if element.tag=='PackageReference' and element.get('Include') in refs:
                found.add(element.get('Include'));group.remove(element)
            if element.tag=='Target' and element.get('Name') in targets:
                found.add(element.get('Name'));group.remove(element)
            if framework and element.tag in ('TargetFramework','TargetFrameworks'):element.text=framework
    tree.write(file,encoding='utf-8',xml_declaration=True)
    assert found==set(refs)|set(targets),(file,found)

# Build-only reference assemblies for net4x targets of the MSBuild task.
edit_xml(root/'Tools/MonoGame.Content.Builder.Task/MonoGame.Content.Builder.Task.csproj',{'Microsoft.NETFramework.ReferenceAssemblies'})
# The template package: JsonPoke (binary MSBuild task) only stamps the tool
# manifests below with the version; content-only package, no netstandard2.0
# reference pack needed.
templates=root/'external/MonoGame.Templates/CSharp'
edit_xml(templates/'MonoGame.Templates.CSharp.csproj',{'JsonPoke.MSBuild'},{'SetMGPackageReferenceVersions'},'net8.0')
manifest={'version':1,'isRoot':True,'tools':{'dotnet-mgcb':{'version':version,'commands':['mgcb']}}}
n=0
for path in templates.rglob('dotnet-tools.json'):
    path.write_text(json.dumps(manifest,indent=2)+'\n');n+=1
# Templates target the .NET 9 SDK upstream; this SDK is .NET 8.
m=0
for path in templates.rglob('*.csproj'):
    text=path.read_text(encoding='utf-8-sig')
    new=re.sub(r'<TargetFramework>net9\.0','<TargetFramework>net8.0',text)
    if new!=text:path.write_text(new,encoding='utf-8');m+=1
# string.Split([..], options) with a collection expression is ambiguous for
# the C# 12 compiler of SDK 8.0.1xx (C# 13 picks char[]); spell out char[].
k=0
for sub in ('MonoGame.Framework.Content.Pipeline','Tools'):
    for path in (root/sub).rglob('*.cs'):
        data=path.read_bytes()
        new=re.sub(rb"\.Split\(\[((?:'[^']*'\s*,?\s*)+)\],",lambda m:b'.Split(new char[] { '+m.group(1)+b' },',data)
        if new!=data:path.write_bytes(new);k+=1
print('Prepared MonoGame',version,'- removed',len(removed),'binary inputs; rewrote',n,'tool manifests and',m,'template projects for net8.0; rewrote Split([...]) in',k,'files')
