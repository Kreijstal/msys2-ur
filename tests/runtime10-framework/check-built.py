"""Audit raw/linked public surfaces and execute the built dependency chain on CLR10."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
plan=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
dotnet='/clang64/lib/dotnet/dotnet.exe';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((plan/'build-status.json').read_text());assert status
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',OutputType='Exe',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',AssemblyName='AuditLinkedLibrary').items():E.SubElement(pg,k).text=v
ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(here/'inputs/AuditLinkedLibrary.cs'));r=E.SubElement(ig,'Reference',Include='Mono.Cecil');E.SubElement(r,'HintPath').text=native(Path('/clang64/lib/dotnet/tool-packs/illink-10.0.5-bootstrap/Mono.Cecil.dll'))
E.ElementTree(p).write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
def run(command,log):
 with log.open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,(r.returncode,command,log)
run([dotnet,'build',native(out/'Build.csproj'),'-c','Release','--configfile',native(plan/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],out/'build.log')
audits={}
for name,record in status.items():
 assembly=name.removeprefix('stub:');product=plan/('stubs' if record['kind']=='stub' else 'lib')/(assembly+'.dll');assert sha(product)==record['output_sha256'],name
 if record['original_library_policy_applied']:
  raw=plan/'p'/name/'obj/PreTrim'/(assembly+'.dll');log=out/(assembly+'-audit.json')
  run([dotnet,native(out/'bin/Release/net8.0/AuditLinkedLibrary.dll'),native(raw),native(product)],log);audits[name]=json.loads(log.read_text())
# Execute a consumer of new NET10 APIs using only matching built libraries.
required=['System.Collections','System.Memory','System.Numerics.Vectors','System.Private.Uri','System.Runtime'];assert all(n in status for n in required)
layout=out/'managed CLR10 λ';layout.mkdir()
for name in ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')/name,layout/name)
for name in ['corerun.exe','System.Private.CoreLib.dll']:shutil.copy2(Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5')/name,layout/name)
for name in required:shutil.copy2(plan/'lib'/(name+'.dll'),layout/(name+'.dll'))
rsp=out/'probe.rsp';args=['/nostdlib+','/target:exe','/optimize+','/out:"'+native(layout/'FrameworkProbe.dll')+'"','/reference:"'+native(layout/'System.Private.CoreLib.dll')+'"']+['/reference:"'+native(layout/(n+'.dll'))+'"' for n in required]+['"'+native(here/'inputs/FrameworkProbe.cs')+'"'];rsp.write_text('\n'.join(args)+'\n')
run([dotnet,native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap/CompilerHost.dll')),'-noconfig','@'+native(rsp)],out/'probe-build.log')
# corerun's binder requires native Windows argument separators.
win=lambda p:native(p).replace('/','\\')
run([str(layout/'corerun.exe'),'-c',win(layout),win(layout/'FrameworkProbe.dll')],out/'probe-execution.log')
record=dict(audited_completed_projects=len(status),original_library_policy_public_api_audits=audits,public_api_entries_preserved=sum(a['public_api_entries'] for a in audits.values()),all_original_embedded_resources_and_pdbs_preserved=True,net10_ordered_dictionary_priority_queue_uri_memory_vectors_and_error_resource_execution_passed=True,tested_files_sha256={p.name:sha(p) for p in layout.iterdir() if p.is_file()},full_managed_framework10_built=len(status)==190,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS',len(audits),'original library API/resource/PDB audits and NET10 managed consumer on installed CLR10')
