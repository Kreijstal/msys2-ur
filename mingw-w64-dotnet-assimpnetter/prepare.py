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
if kind=='assimpnetter':
    # Polyfill/System.Memory/Unsafe only apply to the net472/net48/netstandard2.1 targets that are not built here.
    files=[root/'AssimpNet/AssimpNet.csproj'];expected={'Polyfill','System.Memory','System.Runtime.CompilerServices.Unsafe'};target='net8.0'
    # Do not pack the (deleted) prebuilt libs/Assimp/<rid> natives or build/AssimpNetter.targets, which copies them into
    # consumers' output; the native library is MSYS2's $MINGW_PREFIX/bin/libassimp-6.dll (see 0001 patch).
    tree=E.parse(files[0]);dropped=[]
    for group in tree.iter('ItemGroup'):
        for element in list(group):
            include=element.get('Include','')
            if element.tag in {'Content','None'} and ('libs\\Assimp' in include or include=='AssimpNetter.targets'):
                dropped.append(include);group.remove(element)
    assert sorted(dropped)==['..\\libs\\Assimp\\**','..\\libs\\Assimp\\**','AssimpNetter.targets'],dropped
    tree.write(files[0],encoding='utf-8',xml_declaration=True)
    (root/'AssimpNet/AssimpNetter.targets').unlink()
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
