"""Verify candidate/installed payload and fresh consumer of original NET10 NuGet."""
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile

prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-nuget73-core-bootstrap';checks=doc/'checks';manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
runtime=prefix/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';plan=out/'validation-plan';plan.mkdir();(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=(doc/'validation-source').as_posix(),validation_inputs_only=True)))
for name in ['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel']:
    package=prefix/'lib/dotnet/library-packs'/(name.lower()+'.7.3.0-preview.1.11413.nupkg')
    with zipfile.ZipFile(package) as z:assert z.read('lib/net10.0/'+name+'.dll')==(runtime/'bin'/(name+'.dll')).read_bytes()
command=[sys.executable,'-X','utf8',checks/'check.py',plan,runtime,out/'consumer',doc/'expected-localization.json']
with (out/'consumer.log').open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240)
assert r.returncode==0,r.returncode
text=(out/'consumer/execute.log').read_text(encoding='utf-8');assert 'APIs=1497,neutral strings=392,upstream range vectors=19' in text,text
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in command],exit_code=0,payload_files_verified=len(manifest),original_public_api_declarations_verified=1497,total_neutral_and_localized_values=392,original_upstream_vectors=19,concurrent_owned_file_lock_operations=24,source_nuget_archive_asset_bytes_verified=True,full_nuget73_closure_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print(text.strip())
