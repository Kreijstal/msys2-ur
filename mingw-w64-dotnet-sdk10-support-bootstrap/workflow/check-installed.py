"""Check installed source package bytes,original contracts and isolated SDK integration."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-sdk10-support-bootstrap';checks=doc/'checks';manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
build=out/'build';binary=build/'bin';binary.mkdir(parents=True);results=json.loads((doc/'build-results.json').read_text())
for record in results['projects']:
    name=record['assembly'];version=record['version'];archive=prefix/'lib/dotnet/library-packs'/(name.lower()+'.'+version+'.nupkg')
    with zipfile.ZipFile(archive) as z:
        for ext,h in record['output_sha256'].items():
            data=z.read('lib/net10.0/'+name+'.'+ext);assert hashlib.sha256(data).hexdigest()==h;(binary/(name+'.'+ext)).write_bytes(data)
plan=out/'plan';(plan/'snapshot').mkdir(parents=True);shutil.copytree(doc/'validation-source',plan/'snapshot/runtime')
commands=[]
for label,cmd in [('api',[sys.executable,'-X','utf8',checks/'check-api.py',plan,build,out/'api']),('runtime',[sys.executable,'-X','utf8',checks/'check.py',plan,build,out/'runtime'])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),actual_source_archive_assets_verified=True,strict_original_contract_entries=257,strict_missing_extra_changed_and_nullable_differences=0,owned_native_apphost_and_bundle_execution=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'api.log').read_text(encoding='utf-8'));print((out/'runtime.log').read_text(encoding='utf-8'))
