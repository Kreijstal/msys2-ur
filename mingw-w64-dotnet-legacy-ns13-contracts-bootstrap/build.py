"""Compile original reference-only contracts without framework substitutions."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

root,compiler=(Path(x).resolve() for x in sys.argv[1:]);record=json.loads((root/'source-inputs.json').read_text())
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
source=root/'source';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in record['original_file_sha256'].items():assert sha(source/name)==digest,name
key=Path(__file__).parent/'inputs/Microsoft.snk';assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
output=root/'contracts';output.mkdir();logs=root/'build';logs.mkdir();results={};outputs={}
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')))
for identity,library in record['libraries'].items():
    name=library['name'];version=library['assembly_version'];folder=output/name/version;folder.mkdir(parents=True)
    dependencies=set()
    def add(ident):
        if ident in dependencies:return
        dependencies.add(ident)
        for dep in record['libraries'][ident]['dependencies']:add(dep)
    for dep in library['dependencies']:add(dep)
    paths=[source/library['source'],source/'src/SourceBuildAssemblyMetdata.cs']
    if library.get('generated_port_source'):
        generated=root/library['generated_port_source'];assert sha(generated)==record['generated_source_sha256'][generated.name];paths[0]=generated
    if library.get('generated_assembly_attributes'):
        generated=root/library['generated_assembly_attributes'];assert sha(generated)==record['generated_source_sha256'][generated.name];paths.append(generated)
    selected={}
    for dep in sorted(dependencies):
        depname,depversion=dep.split('/')
        if depname not in selected or tuple(map(int,depversion.split('.')))>tuple(map(int,selected[depname].split('/')[1].split('.'))):selected[depname]=dep
    refs=[outputs[dep] for dep in sorted(selected.values())]
    assert all(p.is_file() for p in refs),(name,refs)
    args=['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:latest','/deterministic+','/warnaserror+','/nowarn:'+','.join(record['SDK_default_NoWarn']+record['original_NoWarn']),'/publicsign+','/keyfile:"'+native(key)+'"','/out:"'+native(folder/(name+'.dll'))+'"','/runtimeMetadataVersion:v4.0.30319']
    args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in paths]
    logdir=logs/name/version;logdir.mkdir(parents=True);rsp=logdir/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
    cmd=['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(rsp)]
    with (logdir/'compile.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode==0,(identity,(logdir/'compile.log').read_text()[-6500:])
    outputs[identity]=folder/(name+'.dll')
    results[identity]=dict(command=cmd,exit_code=r.returncode,original_source_sha256={str(p.relative_to(source)):sha(p) for p in paths if p.is_relative_to(source)},generated_source_sha256={p.name:sha(p) for p in paths if not p.is_relative_to(source)},references={p.name:sha(p) for p in refs},output_sha256=sha(outputs[identity]),original_framework=library['original_framework'],reference_only=True)
    (root/'build-results.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS source contract',identity,flush=True)
ref=root/'ref';ref.mkdir()
for name,identity in record['root_contracts'].items():(ref/(name+'.dll')).write_bytes(outputs[identity].read_bytes())
