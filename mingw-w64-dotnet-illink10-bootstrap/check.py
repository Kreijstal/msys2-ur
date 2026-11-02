"""Run real app/library linking and execute and inspect the rewritten outputs."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E
root,prepared,out=(Path(p).resolve() for p in sys.argv[1:4]);tool=Path(sys.argv[4]).resolve() if len(sys.argv)==5 else prepared/'illink/bin/Release/net8.0'
assert not out.exists();out.mkdir();here=Path(__file__).resolve().parent
base=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
def native(p):
 p=Path(p).resolve()
 if p.is_relative_to(root):return base+'/'+p.relative_to(root).as_posix()
 return subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();dotnet='/clang64/lib/dotnet/dotnet.exe'
env=dict(os.environ,DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
commands=[]
def run(command,log,extra=None,code=0):
 with log.open('w') as f:r=subprocess.run(command,env=dict(env,**(extra or {})),stdout=f,stderr=subprocess.STDOUT,timeout=180)
 commands.append(dict(command=command,exit_code=r.returncode,log=str(log.relative_to(out))))
 assert r.returncode==code,(r.returncode,log)
 return r.returncode
run([dotnet,native(tool/'illink.dll'),'--help'],out/'help.log',dict(COREHOST_TRACE='1',COREHOST_TRACEFILE=native(out/'host.trace')))
trace=(out/'host.trace').read_text().lower().replace('\\','/')
for name in ['System.Collections.Immutable','System.Reflection.Metadata']:
 assert (native(tool/(name+'.dll')).lower()) in trace,('Wrong tool provider',name)
for name,inputs,exe in [('OwnedApp',['OwnedApp.cs'],True),('OwnedLibrary',['OwnedLibrary.cs'],False),('LibraryRunner',['LibraryRunner.cs'],True),('AuditLibrary',['AuditLibrary.cs'],True)]:
 folder=out/name;folder.mkdir();tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
 for k,v in dict(TargetFramework='net8.0',OutputType='Exe' if exe else 'Library',AssemblyName=name,UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',DebugType='portable',UseSharedCompilation='false',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(pg,k).text=v
 items=E.SubElement(tree,'ItemGroup')
 for p in inputs:E.SubElement(items,'Compile',Include=native(here/'inputs'/p))
 if name=='AuditLibrary':E.SubElement(E.SubElement(items,'Reference',Include='Mono.Cecil'),'HintPath').text=native(tool/'Mono.Cecil.dll')
 if name=='OwnedApp':
  (folder/'owned.txt').write_text('π λ source resource\n');E.SubElement(items,'EmbeddedResource',Include='owned.txt',LogicalName='Owned.Resource')
 E.indent(tree);E.ElementTree(tree).write(folder/'Build.csproj',encoding='utf-8',xml_declaration=True)
 run([dotnet,'build',native(folder/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],out/(name+'-build.log'))
framework=Path('/clang64/lib/dotnet/shared/Microsoft.NETCore.App/8.0.31');results={}
for name,mode in [('OwnedApp','entrypoint'),('OwnedLibrary','library')]:
 source=out/name/'bin/Release/net8.0';linked=out/(name+'-linked');rsp=out/(name+'.rsp')
 args=['-a',native(source/(name+'.dll')),mode,'-out',native(linked),'-d',native(source),'-d',native(framework),'--trim-mode','skip','--action','link',name,'--skip-unresolved','true','--ignore-link-attributes','true','-b','true']
 rsp.write_text('\n'.join('"'+a+'"' for a in args)+'\n')
 run([dotnet,native(tool/'illink.dll'),'@'+native(rsp)],out/(name+'-rewrite.log'))
 assert (linked/(name+'.dll')).is_file() and sha(linked/(name+'.dll'))!=sha(source/(name+'.dll'))
 assert (linked/(name+'.pdb')).is_file()
 if name=='OwnedApp':
  shutil.copyfile(source/(name+'.runtimeconfig.json'),linked/(name+'.runtimeconfig.json'))
  run([dotnet,native(linked/(name+'.dll'))],out/(name+'-run.log'))
 else:
  run([dotnet,native(out/'AuditLibrary/bin/Release/net8.0/AuditLibrary.dll'),native(source/(name+'.dll')),native(linked/(name+'.dll'))],out/'library-api-audit.json')
  run([dotnet,native(out/'LibraryRunner/bin/Release/net8.0/LibraryRunner.dll'),native(linked/(name+'.dll'))],out/'library-run.log')
 results[name]=dict(mode=mode,input_sha256=sha(source/(name+'.dll')),linked_sha256=sha(linked/(name+'.dll')),linked_pdb_sha256=sha(linked/(name+'.pdb')))
# Malformed roots must propagate a failure status through the original CLI.
with (out/'invalid-root.log').open('w') as f:bad=subprocess.run([dotnet,native(tool/'illink.dll'),'-a',native(out/'missing.dll')],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60)
assert bad.returncode!=0
result=dict(formal_pacman_installed=len(sys.argv)==5,tool_directory=native(tool),actual_source_metadata10_and_immutable10_host_paths_verified=True,app_and_library_original_linker_modes_passed=True,reflection_generic_resources_and_symbols_passed=True,library_public_surface_and_constraints_verified=True,linked_outputs_executed=True,invalid_root_exit_code=bad.returncode,rewrites=results,commands=commands,library_api_audit=json.loads((out/'library-api-audit.json').read_text()),original_net10_host_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS source ILLink10 app/library rewrites, source10 host providers, linked execution, library API/generic/resource/symbol and invalid-root checks')
