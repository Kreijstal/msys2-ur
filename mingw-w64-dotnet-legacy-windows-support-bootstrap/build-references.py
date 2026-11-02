"""Compile original CoreFX reference sources with their original dependency versions."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

root,compiler=(Path(x).resolve() for x in sys.argv[1:]);here=Path(__file__).parent
baseline=json.loads((here/'inputs/published-reference-metadata.json').read_text());record=json.loads((root/'source-inputs.json').read_text())
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')));results={}
key=here/'inputs/Microsoft.snk'
for name,item in record['libraries'].items():
    folder=root/name;source=folder/'source';original=source/'src'/name/'ref'/(name+'.csproj');tree=E.parse(original)
    selected=[(original.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//{*}Compile')];assert all(p.is_file() for p in selected)
    build=folder/'contract';build.mkdir();expected=baseline[name+'.dll'];attrs={a['type']:a['arguments'] for a in expected['attributes']}
    version=expected['identity'].split('Version=')[1].split(',')[0]
    header='[assembly:System.Runtime.CompilerServices.ReferenceAssembly]\n[assembly:System.Reflection.AssemblyVersion('+json.dumps(version)+')]\n[assembly:System.Reflection.AssemblyFileVersion('+json.dumps(attrs['System.Reflection.AssemblyFileVersionAttribute'][0])+')]\n[assembly:System.CLSCompliant(true)]\n'
    (build/'BootstrapReferenceVersion.cs').write_text(header)
    dependencies=[]
    for identity in expected['references']:
        ident,rest=identity.split(', Version=');ver=rest.split(',')[0];p=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts')/ident/ver/(ident+'.dll');assert p.is_file();dependencies.append(p)
    output=build/(name+'.dll');args=['/nostdlib+','/target:library','/refonly','/unsafe+','/langversion:6','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"'+native(key)+'"','/runtimeMetadataVersion:v4.0.30319','/out:"'+native(output)+'"']+['/reference:"'+native(p)+'"' for p in dependencies]+['"'+native(p)+'"' for p in selected+[build/'BootstrapReferenceVersion.cs']]
    (build/'compile.rsp').write_text('\n'.join(args)+'\n');cmd=['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(build/'compile.rsp')]
    with (build/'compile.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert r.returncode==0,(name,(build/'compile.log').read_text()[-5000:])
    results[name]=dict(command=cmd,exit_code=r.returncode,original_source_sha256={p.relative_to(source).as_posix():sha(p) for p in selected},reference_source_project_sha256=sha(original),dependency_DLL_sha256={p.as_posix():sha(p) for p in dependencies},output_sha256=sha(output),original_reference_assembly_version=version,original_framework='netstandard1.3',source_CSharp_changes=0)
(root/'reference-build-results.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS original Registry and CodePages reference sources compiled with original contract identities')
