from pathlib import Path
import json,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]); root.mkdir(parents=True,exist_ok=True); inputs=root.parent
files=json.loads((inputs/'source-inputs.json').read_text())
(root/'Microsoft.public.snk').write_bytes(bytes.fromhex((inputs/'Microsoft.pubkey.hex').read_text()))
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
p=E.Element('Project',Sdk='Microsoft.NET.Sdk'); props=E.SubElement(p,'PropertyGroup')
for k,v in {'TargetFramework':'net8.0-windows','AssemblyName':'System.Threading.AccessControl','RootNamespace':'System.Threading.AccessControl','Version':'8.0.0','AssemblyVersion':'8.0.0.0','AllowUnsafeBlocks':'true','Nullable':'enable','SignAssembly':'true','PublicSign':'true','AssemblyOriginatorKeyFile':'Microsoft.public.snk','EnableDefaultCompileItems':'false','EnableDefaultEmbeddedResourceItems':'false'}.items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup')
for f in files:
    name=Path(f['path']).name
    if name.endswith('.cs'):E.SubElement(items,'Compile',Include='../'+name)
E.SubElement(items,'Compile',Include='SR.Generated.cs')
logical='System.Threading.AccessControl.Strings'
E.SubElement(items,'EmbeddedResource',Include='../Strings.resx',LogicalName=logical+'.resources')
lines=['namespace System { internal static partial class SR {','private static readonly System.Resources.ResourceManager ResourceManager = new System.Resources.ResourceManager("'+logical+'", typeof(SR).Assembly);']
for data in E.parse(inputs/'Strings.resx').iter('data'):
    name=data.get('name');lines.append('internal static string '+name+' => GetResourceString('+json.dumps(name)+');')
lines.append('}}');(root/'SR.Generated.cs').write_text('\n'.join(lines)+'\n')
E.indent(p);E.ElementTree(p).write(root/'Threading.csproj',encoding='utf-8',xml_declaration=True)
(root/'removed-binaries.json').write_text('[]\n')
