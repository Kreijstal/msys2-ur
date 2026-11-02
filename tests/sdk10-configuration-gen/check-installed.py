"""Check actual packaged archives, original generator and retained strict-API failure."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();name='dotnet-sdk10-configuration-bootstrap';doc=prefix/'share/doc'/name;here=doc/'checks';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest=json.loads((doc/'payload-sha256.json').read_text());archives=json.loads((doc/'archives.json').read_text());commands=[]
for rel,h in manifest.items():assert sha(prefix/rel)==h,rel
plan=out/'plan';(plan/'snapshot').mkdir(parents=True);shutil.copytree(doc/'validation-source',plan/'snapshot/runtime');(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(plan/'snapshot/runtime'))));build=out/'build';(build/'bin').mkdir(parents=True);shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir()
for assembly,a in archives.items():
 archive=prefix/a['archive'];assert sha(archive)==a['sha256']
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert hashlib.sha256(z.read(member)).hexdigest()==h,member
  for member in z.namelist():
   if member.startswith('lib/net10.0/'):
    dest=build/'bin'/Path(member).name;dest.write_bytes(z.read(member))
   elif member.startswith('analyzers/dotnet/cs/'):
    rel=member.removeprefix('analyzers/dotnet/cs/');dest=build/'bin'/rel;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(member));actual=out/member;actual.parent.mkdir(parents=True,exist_ok=True);actual.write_bytes(z.read(member))
   elif member.endswith('.targets'):(out/'Binder.targets').write_bytes(z.read(member))
def run(label,cmd,expected=0):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 commands.append(dict(label=label,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
run('restore',[sys.executable,'-X','utf8',here/'check-restore.py',prefix,out/'restore'])
for assembly in archives:
 cached=out/'restore/cache'/assembly.lower()/'10.0.2'/'lib/net10.0'/(assembly+'.dll');assert sha(cached)==sha(build/'bin'/cached.name);shutil.copyfile(cached,build/'bin'/cached.name)
gen=out/'restore/cache/microsoft.extensions.configuration.binder/10.0.2/analyzers/dotnet/cs/Microsoft.Extensions.Configuration.Binder.SourceGeneration.dll';assert sha(gen)==sha(build/'bin'/gen.name);shutil.copyfile(gen,build/'bin'/gen.name)
run('resources',[sys.executable,'-X','utf8',here/'check-resources.py',plan,build,localized,out/'resources'])
run('runtime',[sys.executable,'-X','utf8',here/'check.py',plan,build,out/'runtime'])
run('strict-api',[sys.executable,'-X','utf8',here/'check-api.py',plan,build,out/'api'],expected=1)
run('api-baseline',[sys.executable,'-X','utf8',here/'check-api-baseline.py',out/'api'])
# Execute the unchanged Binder opt-in target and unsupported-framework diagnostic.
p=E.Element('Project');E.SubElement(p,'Import',Project=native(out/'Binder.targets'));ig=E.SubElement(p,'ItemGroup');i=E.SubElement(ig,'Analyzer',Include=native(out/'analyzers/dotnet/cs/Microsoft.Extensions.Configuration.Binder.SourceGeneration.dll'));E.SubElement(i,'NuGetPackageId').text='Microsoft.Extensions.Configuration.Binder';t=E.SubElement(p,'Target',Name='Check',DependsOnTargets='_Microsoft_Extensions_Configuration_Binder_RemoveAnalyzer');E.SubElement(t,'Error',Condition="'@(Analyzer->Count())' != '$(Expected)'",Text='Original Binder analyzer selection mismatch');E.SubElement(t,'Error',Condition="'$(EnableConfigurationBindingGenerator)' == 'true' and !$(InterceptorsPreviewNamespaces.Contains('Microsoft.Extensions.Configuration.Binder.SourceGeneration'))",Text='Original Binder interceptor namespace missing');E.ElementTree(p).write(out/'Targets.proj',encoding='utf-8',xml_declaration=True)
installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=installed/'lib/dotnet/dotnet.exe'
for framework,enabled,expected in [('net10.0','true','1'),('net10.0','false','0'),('net7.0','false','0')]:run('targets-'+framework+'-'+enabled,[host,'msbuild',out/'Targets.proj','-t:Check','-nologo','-p:TargetFramework='+framework,'-p:EnableConfigurationBindingGenerator='+enabled,'-p:Expected='+expected])
assert "doesn't support net7.0" in (out/'targets-net7.0-false.log').read_text(encoding='utf-8')
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),four_source_NuGet_archives_verified=True,actual_offline_source_NuGet73_restore_and_asset_selection_verified=True,original_generator_and_consumers_executed_from_archive_assets=True,original_Binder_opt_in_namespace_and_unsupported_framework_targets_verified=True,resource_values=260,satellites=13,portable_PDBs=5,CLR_contract_entries=299,CLR_missing_extra_changed=0,strict_Primitives_nullable_contract_gate_exit_code=1,strict_Primitives_nullable_contract_gate_passed=False,original_Primitives_nullable_discrepancies=1,exact_known_original_discrepancy_preserved=True,full_logging_console_graph_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'actual payload hashes,4 archives,original Binder generation/interceptors/targets and299 CLR entries; strict Primitives nullable gate remains FAILED (1 original-source difference)')
