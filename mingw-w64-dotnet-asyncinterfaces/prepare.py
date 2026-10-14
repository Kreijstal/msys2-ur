from pathlib import Path
import subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[2]);root.mkdir(parents=True,exist_ok=True);source=root.parent
upstream=E.parse(source/'upstream.csproj')
assert any(e.get('Include')=='Microsoft.Bcl.AsyncInterfaces.Forwards.cs' for e in upstream.iter('Compile'))
key=root/'Open.public.snk';key.write_bytes(bytes.fromhex((source/'Open.pubkey.hex').read_text()))
def win(p):return subprocess.check_output(['cygpath','-m',str(p.resolve())],text=True).strip()
project=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(project,'PropertyGroup')
for name,value in {'TargetFramework':'net8.0','AssemblyName':'Microsoft.Bcl.AsyncInterfaces','PackageId':'Microsoft.Bcl.AsyncInterfaces','AssemblyVersion':'10.0.0.0','FileVersion':'10.0.12.0','EnableDefaultCompileItems':'false','SignAssembly':'true','PublicSign':'true','AssemblyOriginatorKeyFile':win(key)}.items():E.SubElement(props,name).text=value
E.SubElement(E.SubElement(project,'ItemGroup'),'Compile',Include=win(source/'Microsoft.Bcl.AsyncInterfaces.Forwards.cs'))
E.indent(project);E.ElementTree(project).write(root/'AsyncInterfaces.csproj',encoding='utf-8',xml_declaration=True)
(root/'global.json').write_text('{"sdk":{"version":"8.0.131","rollForward":"disable"}}\n')
(root/'removed-binaries.json').write_text('[]\n')
