"""Require fresh module files and private dependencies to match source-built assets."""
import os
from pathlib import Path
import hashlib,json,sys,zipfile

module=Path(sys.argv[1]);sha=lambda b:hashlib.sha256(b).hexdigest();here=Path(__file__).resolve().parent
r=json.loads((module/'source-inventory.json').read_text());frozen=json.loads((here/'source-inputs.json').read_text())
assert r['source_commit']==frozen['source_commit'] and r['source_archive_sha256']==frozen['source_archive_sha256']
assert len(r['original_cs'])==56 and r['actual_original_compile_items']==r['original_cs']
assert r['original_cs']=={p:h for p,h in frozen['original_src_inputs'].items() if p.endswith('.cs')}
for path,digest in r['original_module_assets'].items():assert sha((module/path.removeprefix('src/')).read_bytes())==digest
files=json.loads((module/'module-files.json').read_text())
for path,digest in files.items():assert sha((module/path).read_bytes())==digest,path
name='Microsoft.PowerShell.PSResourceGet'
assert sha((module/(name+'.dll')).read_bytes())==r['implementation_sha256']
assert sha((module/'source-build/ref/net8.0'/(name+'.dll')).read_bytes())==r['reference_sha256']
assert sha((module/'source-build/docs'/(name+'.xml')).read_bytes())==r['documentation_sha256']
for path,digest in r['prepared_project_metadata'].items():assert sha((module/'source-build'/path).read_bytes())==digest
change,=r['production_cs_changes'];assert sha((module/'source-build'/change['overlay']).read_bytes())==change['prepared_sha256']
private=json.loads((module/'source-dependencies.json').read_text());assert len(private)==26
assert private['System.Security.Cryptography.Pkcs.dll']['asset']=='runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'
feed={p.name.lower():p for p in Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs').glob('*.nupkg')}
for filename,record in private.items():
    package,version=record['package'].rsplit('/',1);package_file=feed[package.lower()+'.'+version+'.nupkg']
    assert sha(package_file.read_bytes())==record['nuget_sha256']
    with zipfile.ZipFile(package_file) as z:
        assert z.read(record['asset'])==(module/'dependencies'/filename).read_bytes()
        assert sha(z.read(record['asset']))==record['sha256']
        for legal in record['licenses']:assert z.read(legal)==(module/'licenses'/package.lower()/version/legal).read_bytes()
    for legal in record['native_license_assets']:
        assert Path(legal['source']).read_bytes()==(module/legal['target']).read_bytes()
        assert sha((module/legal['target']).read_bytes())==legal['sha256']
    assert record['licenses'] or record['native_license_assets']
assert {p.name for p in (module/'dependencies').glob('*.dll')}==set(private)
engine=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll')
assert sha(engine.read_bytes())==r['source_engine_sha256']
if len(sys.argv)>2:
    other=Path(sys.argv[2]);assert (other/'module-files.json').read_bytes()==(module/'module-files.json').read_bytes()
    for path in files:assert (other/path).read_bytes()==(module/path).read_bytes(),path
print('PASS all restored/loose module files, original56-input/compiler/engine provenance, implementation/ref/XML and26 private source-built dependency/license payloads')
