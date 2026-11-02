from pathlib import Path
import hashlib,json,subprocess,sys,zipfile
prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();doc=prefix/'share/doc/dotnet-deployment-releases-bootstrap';checks=doc/'checks';manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,h in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==h,rel
refs=json.loads((doc/'reference-build-results.json').read_text());refdir=out/'references';refdir.mkdir()
for r in refs['projects']:r['output']=(prefix/'lib/dotnet/reference-packs/sdk10-releases-vmr-44525024'/r['assembly']/r['package_version']/'netstandard2.0'/(r['assembly']+'.dll')).as_posix();assert hashlib.sha256(Path(r['output']).read_bytes()).hexdigest()==r['output_sha256']
(refdir/'results.json').write_text(json.dumps(refs)+'\n');build=out/'build';build.mkdir();name='Microsoft.Deployment.DotNet.Releases';version='2.0.0-preview.1.25612.105'
with zipfile.ZipFile(prefix/'lib/dotnet/library-packs'/(name.lower()+'.'+version+'.nupkg')) as z:
    for rel in z.namelist():
        if rel.startswith('lib/netstandard2.0/'):
            dest=build/rel.removeprefix('lib/netstandard2.0/');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(rel))
cmd=[sys.executable,'-X','utf8',checks/'check.py',doc/'validation-source',refdir,build,out/'consumer',doc/'expected-localization.json']
with (out/'consumer.log').open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240)
assert r.returncode==0,r.returncode
text=(out/'consumer.log').read_text(encoding='utf-8');assert 'cases=81,channels=10,releases=208,files=8289,CVEs=170,neutral strings=252,reference assemblies rejected=9' in text
(out/'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd],exit_code=0,payload_files_verified=len(manifest),source_runtime_consumers=['net8.0','net10.0'],reference_only_assemblies_runtime_rejected=9,unchanged_upstream_version_test_cases=81,original_product_channels=10,original_releases=208,original_release_files=8289,original_cves=170,resource_values=252,localized_satellites=13,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print(text)
