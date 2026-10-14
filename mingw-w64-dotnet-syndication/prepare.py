import json, sys, subprocess, tarfile
from pathlib import Path
import xml.etree.ElementTree as E
archive,root=map(Path,sys.argv[1:]);root.mkdir(parents=True,exist_ok=True)
with tarfile.open(archive) as tar:
    selected=[m for m in tar.getmembers() if '/src/libraries/System.ServiceModel.Syndication/src/' in m.name or m.name.endswith('/src/libraries/Common/src/System/SR.cs') or m.name.endswith('/LICENSE.TXT')]
    assert all(not m.isfile() or Path(m.name).suffix.lower() in {'.cs','.csproj','.props','.targets','.resx','.txt','.xlf','.xml','.md'} for m in selected)
    tar.extractall(root,members=selected,filter='data')
runtime=next(root.glob('runtime-*'))
module=runtime/'src/libraries/System.ServiceModel.Syndication/src'
def win(path):return subprocess.check_output(['cygpath','-m',str(path.resolve())],text=True).strip()
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
(root/'Microsoft.public.snk').write_bytes(bytes.fromhex((root.parent/'Microsoft.pubkey.hex').read_text()))
(root/'LICENSE.TXT').write_bytes((runtime/'LICENSE.TXT').read_bytes())
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for k,v in {'TargetFramework':'net8.0','AssemblyName':'System.ServiceModel.Syndication','RootNamespace':'System.ServiceModel.Syndication','Version':'10.0.3','AssemblyVersion':'10.0.0.0','FileVersion':'10.0.3.0','EnableDefaultCompileItems':'false','EnableDefaultEmbeddedResourceItems':'false','Nullable':'enable','SignAssembly':'true','PublicSign':'true','AssemblyOriginatorKeyFile':win(root/'Microsoft.public.snk'),'PackageLicenseExpression':'MIT'}.items():E.SubElement(props,k).text=v
items=E.SubElement(project,'ItemGroup')
original=E.parse(module/'System.ServiceModel.Syndication.csproj');files=[]
for item in original.iter('Compile'):
    relative=item.get('Include');path=module/relative.replace('\\','/');assert path.is_file(),path
    E.SubElement(items,'Compile',Include=win(path));files.append(relative)
assert len(files)>40
E.SubElement(items,'Compile',Include=win(runtime/'src/libraries/Common/src/System/SR.cs'))
E.SubElement(items,'Compile',Include=win(root/'SR.Generated.cs'))
logical='System.ServiceModel.Syndication.Strings'
E.SubElement(items,'EmbeddedResource',Include=win(module/'Resources/Strings.resx'),LogicalName=logical+'.resources')
lines=['namespace System { internal static partial class SR {','private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager("'+logical+'", typeof(SR).Assembly);']
for data in E.parse(module/'Resources/Strings.resx').iter('data'):
    name=data.get('name');lines.append('internal static string '+name+' => GetResourceString('+json.dumps(name)+');')
lines.append('}}');(root/'SR.Generated.cs').write_text('\n'.join(lines)+'\n')
E.indent(project);E.ElementTree(project).write(root/'Syndication.csproj',encoding='utf-8',xml_declaration=True)
(root/'source-files.json').write_text(json.dumps(files,indent=2)+'\n')
(root/'removed-binaries.json').write_text('[]\n')
print('Selected and configured',len(files),'original source inputs plus original common SR implementation and original string resources')
