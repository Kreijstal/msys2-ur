"""Stage a complete isolated NET10 framework from audited source outputs."""
from pathlib import Path
import hashlib,json,shutil,sys

plan=Path(sys.argv[1]).resolve();destination=Path(sys.argv[2]).resolve()
assert not destination.exists(),destination
status=json.loads((plan/'build-status.json').read_text())
assert len(status)==190 and sum(v['kind']!='stub' for v in status.values())==171
audit=json.loads((plan/'compiler-source-audit.json').read_text())
assert audit['full_managed_framework_compilation_complete']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
framework=destination/'shared/Microsoft.NETCore.App/10.0.5'
framework.mkdir(parents=True)
origins={};runtime_assets={};native_assets={}
def copy(source,target):
 assert source.is_file(),source
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 assert sha(source)==sha(target)
 origins[target.relative_to(destination).as_posix()]=dict(source=str(source),sha256=sha(source))
for name,item in sorted(status.items()):
 if item['kind']=='stub':continue
 source=plan/'lib'/(name+'.dll');assert sha(source)==item['output_sha256'],name
 copy(source,framework/source.name)
 runtime_assets[source.name]=dict(assemblyVersion=item['assembly_version'],fileVersion=item['file_version'])
corelib=Path('/clang64/lib/dotnet-bootstrap10/corelib/10.0.5/System.Private.CoreLib.dll')
copy(corelib,framework/corelib.name)
runtime_assets[corelib.name]=dict(assemblyVersion='10.0.0.0',fileVersion='10.0.526.11800')
for folder,names in [('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5',
 ['coreclr.dll','clrjit.dll','mscorrc.dll','clretwrc.dll']),
 ('/clang64/lib/dotnet-bootstrap10/native-libraries/10.0.5',
 ['System.IO.Compression.Native.dll','System.Globalization.Native.dll']),
 ('/clang64/lib/dotnet10-bootstrap',['hostpolicy.dll'])]:
 for name in names:
  copy(Path(folder)/name,framework/name)
  native_assets[name]=dict(fileVersion='10.0.526.11800')
host=Path('/clang64/lib/dotnet10-bootstrap')
copy(host/'dotnet.exe',destination/'dotnet.exe')
copy(host/'hostfxr.dll',destination/'host/fxr/10.0.5/hostfxr.dll')
target='.NETCoreApp,Version=v10.0/win-x64';package='Microsoft.NETCore.App.Runtime.win-x64/10.0.5'
deps=dict(runtimeTarget=dict(name=target,signature=''),compilationOptions={},
 targets={'.NETCoreApp,Version=v10.0':{},target:{package:dict(runtime=runtime_assets,native=native_assets)}},
 libraries={package:dict(type='package',serviceable=True,sha512='')})
(framework/'Microsoft.NETCore.App.deps.json').write_text(json.dumps(deps,indent=2)+'\n')
(framework/'Microsoft.NETCore.App.runtimeconfig.json').write_text(json.dumps(dict(
 runtimeOptions=dict(tfm='net10.0')),indent=2)+'\n')
(destination/'source-payload.json').write_text(json.dumps(dict(
 managed_assemblies=172,private_seed_assemblies=0,source_files=origins,
 runtime_metadata_origin='source build adapter; actual assembly versions from build records',
 full_runtime_compatibility_verified=False,full_sdk10_built=False,powershell76_built=False,
 full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS isolated framework layout: 172 managed assemblies, 7 native framework DLLs and source host')
