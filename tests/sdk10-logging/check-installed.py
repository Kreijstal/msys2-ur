"""Verify actual source archives, offline restore, generated Options and logging consumers."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,xml.etree.ElementTree as E,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();name='dotnet-sdk10-logging-bootstrap';doc=prefix/'share/doc'/name;here=doc/'checks';native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest=json.loads((doc/'payload-sha256.json').read_text());archives=json.loads((doc/'archives.json').read_text());commands=[]
for rel,h in manifest.items():assert sha(prefix/rel)==h,rel
plan=out/'plan';(plan/'snapshot').mkdir(parents=True);shutil.copytree(doc/'validation-source',plan/'snapshot/runtime');(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(plan/'snapshot/runtime'))));build=out/'build';(build/'bin').mkdir(parents=True);shutil.copyfile(doc/'build-results.json',build/'results.json');localized=out/'localized';localized.mkdir();shutil.copyfile(doc/'localization-results.json',localized/'results.json')
for assembly,a in archives.items():
 archive=prefix/a['archive'];assert sha(archive)==a['sha256']
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(a['members'])
  for member,h in a['members'].items():assert hashlib.sha256(z.read(member)).hexdigest()==h,member
  for member in z.namelist():
   if member.startswith('lib/net10.0/'):
    dest=build/'bin'/Path(member).name;dest.write_bytes(z.read(member))
   elif member.startswith('analyzers/dotnet/roslyn4.4/cs/'):
    rel=member.removeprefix('analyzers/dotnet/roslyn4.4/cs/');dest=build/'bin'/rel;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(member));actual=out/member;actual.parent.mkdir(parents=True,exist_ok=True);actual.write_bytes(z.read(member))
   elif member.endswith('.targets'):(out/'Options.targets').write_bytes(z.read(member))
def run(label,cmd):
 with (out/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 commands.append(dict(label=label,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('restore',[sys.executable,'-X','utf8',here/'check-restore.py',prefix,out/'restore'])
(build/'dependency-assets').mkdir()
restored=json.loads((out/'restore/results.json').read_text())['restored_source_archive_sha256']
for assembly in restored:
 cached=out/'restore/cache'/assembly.lower()/'10.0.2'/'lib/net10.0'/(assembly+'.dll')
 if assembly in archives:
  assert sha(cached)==sha(build/'bin'/cached.name);shutil.copyfile(cached,build/'bin'/cached.name)
 else:shutil.copyfile(cached,build/'dependency-assets'/cached.name)
gen=out/'restore/cache/microsoft.extensions.options/10.0.2/analyzers/dotnet/roslyn4.4/cs/Microsoft.Extensions.Options.SourceGeneration.dll';assert sha(gen)==sha(build/'bin'/gen.name);shutil.copyfile(gen,build/'bin'/gen.name)
run('resources',[sys.executable,'-X','utf8',here/'check-resources.py',plan,build,localized,out/'resources'])
run('runtime',[sys.executable,'-X','utf8',here/'check.py',plan,build,out/'runtime'])
run('strict-api',[sys.executable,'-X','utf8',here/'check-api.py',plan,build,out/'api'])
p=E.Element('Project');E.SubElement(p,'Import',Project=native(out/'Options.targets'));ig=E.SubElement(p,'ItemGroup');i=E.SubElement(ig,'Analyzer',Include=native(out/'analyzers/dotnet/roslyn4.4/cs/Microsoft.Extensions.Options.SourceGeneration.dll'));E.SubElement(i,'NuGetPackageId').text='Microsoft.Extensions.Options';t=E.SubElement(p,'Target',Name='Check',DependsOnTargets='_Microsoft_Extensions_OptionsAnalyzerMultiTargeting;_Microsoft_Extensions_OptionsRemoveAnalyzers');E.SubElement(t,'Error',Condition="'@(Analyzer->Count())' != '$(Expected)'",Text='Original Options analyzer selection mismatch');E.ElementTree(p).write(out/'Targets.proj',encoding='utf-8',xml_declaration=True)
installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=installed/'lib/dotnet/dotnet.exe'
for supports,disabled,expected in [('true','false','1'),('false','false','0'),('true','true','0')]:run('targets-'+supports+'-'+disabled,[host,'msbuild',out/'Targets.proj','-t:Check','-nologo','-p:SupportsRoslynComponentVersioning='+supports,'-p:DisableMicrosoftExtensionsOptionsSourceGenerator='+disabled,'-p:Expected='+expected])
api=json.loads((out/'api/results.json').read_text());assert all(p['exit_code']==0 for p in api['projects'].values())
resource=json.loads((out/'resources/results.json').read_text())
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),source_NuGet_archives_verified=len(archives),actual_offline_source_NuGet73_restore_and_asset_selection_verified=True,restored_package_count=len(restored),original_Options_generator_and_runtime_consumers_executed_from_archive_assets=True,original_Options_analyzer_versioning_and_disable_targets_executed=True,resource_values=resource['exact_values'],satellites=resource['satellite_assemblies'],portable_PDBs=resource['portable_pdb_associations'],CLR_contract_entries=sum(p['comparison']['expected_entries'] for p in api['projects'].values()),strict_six_component_CLR_and_nullable_contracts_passed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(manifest),'payload files,',len(archives),'source archives,',len(restored),'restored packages, original Options generator/runtime/resources/targets and six strict API comparisons')
