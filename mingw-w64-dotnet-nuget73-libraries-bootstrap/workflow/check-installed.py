"""Verify actual NuGet archives and an isolated consumer from the candidate/installed prefix."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,xml.etree.ElementTree as E,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-nuget73-libraries-bootstrap';checks=doc/'checks';manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
runtime=prefix/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';plan=out/'validation-plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=(doc/'validation-source').as_posix(),validation_inputs_only=True)))
build=out/'validation-build';build.mkdir();shutil.copytree(runtime/'bin',build/'bin');shutil.copyfile(doc/'build-results.json',build/'results.json')
records=json.loads((doc/'build-results.json').read_text())['projects'];feed=prefix/'lib/dotnet/library-packs'
for record in records:
    name=record['assembly'];package=feed/(name.lower()+'.7.3.0-preview.1.11413.nupkg')
    with zipfile.ZipFile(package) as z:
        for ext in ['dll','pdb','xml']:assert z.read('lib/net10.0/'+name+'.'+ext)==(runtime/'bin'/(name+'.'+ext)).read_bytes()
        meta=E.fromstring(z.read(name+'.nuspec'));assert meta.find('./metadata/dependencies/group').get('targetFramework')=='net10.0'
        assert not any(n.endswith('.resources.dll') for n in z.namelist())
command=[sys.executable,'-X','utf8',checks/'check-closure.py',plan,build,out/'consumer',doc/'expected-localization.json']
with (out/'consumer.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=300)
assert r.returncode==0,r.returncode
text=(out/'consumer/execute.log').read_text(encoding='utf-8');assert 'upstream APIs=6615,resource values=10164' in text,text
# Exercise actual packaged dependency metadata through the NET10 source restore engine.
command2=[sys.executable,'-X','utf8',checks/'check-packaged-restore.py',out/'consumer/bin',prefix,out/'package-restore']
with (out/'package-restore.log').open('w',encoding='utf-8') as log:r2=subprocess.run(command2,stdout=log,stderr=subprocess.STDOUT,timeout=300)
assert r2.returncode==0,r2.returncode
(out/'results.json').write_text(json.dumps(dict(commands=[dict(command=[str(p) for p in command],exit_code=0),dict(command=[str(p) for p in command2],exit_code=0)],payload_files_verified=len(manifest),original_public_api_declarations_preserved=6615,raw_extra_api_comparison_performed=False,total_resource_values=10164,localized_satellites=104,eight_source_nuget_archive_assets_verified=True,actual_packaged_dependency_graph_restore_passed=True,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print(text.strip());print((out/'package-restore.log').read_text(encoding='utf-8'))
