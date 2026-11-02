"""Audit original/linked metadata and execute with the installed native CLR10."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir()
here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dotnet='/clang64/lib/dotnet/dotnet.exe'
core=root/'corelib10-1/corelib';rewrite=root/'corelib10-1/rewrite'
installed=Path(sys.argv[3]).resolve() if len(sys.argv)>3 else None
product=installed or rewrite/'linked'
corerun=(installed/'corerun.exe') if installed else root/'coreclr-build/hosts/corerun/corerun.exe'
clr=Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
def run(command,log):
 with log.open('w') as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
metadata=core/'tools/metadata'
run([dotnet,'build',native(metadata/'Build.csproj'),'-c','Release','--configfile',native(core/'tools/NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],out/'metadata-build.log')
for name,path in [('raw',core/'lib/System.Private.CoreLib.dll'),('linked',product/'System.Private.CoreLib.dll')]:
 target=out/('metadata-'+name+'.json')
 run([dotnet,native(metadata/'bin/Release/net8.0/CoreLib10.MetadataCheck.dll'),native(path),native(root/'r/src/libraries/System.Private.CoreLib/src/Resources/Strings.resx')],target)
 record=json.loads(target.read_text());assert record['resource_strings']==1421 and record['assembly_references']==0
 if name=='linked':assert record['internal_calls']>0 and record['internal_calls_with_body']==0
 if not installed:shutil.copy2(target,core/target.name)
# Cecil reads all public signatures, generic constraints, resource bytes and PDBs.
audit=out/'api';audit.mkdir()
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=native(here/'inputs/AuditCoreLib.cs'))
r=E.SubElement(items,'Reference',Include='Mono.Cecil');E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/Mono.Cecil.dll'))
E.ElementTree(p).write(audit/'Build.csproj',encoding='utf-8',xml_declaration=True)
run([dotnet,'build',native(audit/'Build.csproj'),'-c','Release','--configfile',native(core/'tools/NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],out/'api-build.log')
run([dotnet,native(audit/'bin/Release/net8.0/Build.dll'),native(core/'lib/System.Private.CoreLib.dll'),native(product/'System.Private.CoreLib.dll')],out/'api-audit.json')
a=json.loads((out/'api-audit.json').read_text());assert a['public_api_unchanged'] and a['original_pdb_read_successfully'] and len(a['original_embedded_resources_unchanged'])==4
if not installed:shutil.copy2(out/'api-audit.json',rewrite/'api-audit.json')
layout=out/'native CLR10 λ';layout.mkdir()
for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']:shutil.copy2(clr/name,layout/name)
for name in ['System.Private.CoreLib.dll','System.Private.CoreLib.pdb']:shutil.copy2(product/name,layout/name)
shutil.copy2(corerun,layout/'corerun.exe')
args=['/nostdlib+','/target:exe','/optimize+','/deterministic+','/out:"'+native(layout/'ManagedProbe.dll')+'"','/reference:"'+native(layout/'System.Private.CoreLib.dll')+'"','"'+native(here/'inputs/ManagedProbe.cs')+'"']
(out/'probe.rsp').write_text('\n'.join(args)+'\n')
run([dotnet,native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')),'-noconfig','@'+native(out/'probe.rsp')],out/'probe-build.log')
subprocess.run(['/clang64/bin/python.exe',native(here/'check-managed.py'),native(out)],env=env,check=True)
record=json.loads((out/'results.json').read_text())
record.update(native_dependency_sha256={name:sha(clr/name) for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']},installed_product_checked=installed is not None,public_api_entries=a['public_api_entries'],original_resources_and_pdb_verified=True)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS original CoreLib metadata/API/resources/PDB and four managed CLR10 cases')
