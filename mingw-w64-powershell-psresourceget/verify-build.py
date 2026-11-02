"""Gate the full original module, exact NuGet type qualification and source references."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys,zipfile

source,out,cache=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
r=json.loads((out/'source-inventory.json').read_text());original_prefix=native(source)+'/';own=native(out)+'/'
actual={};generated={};overlays={}
for value in (out/'obj/Release/net8.0/Compile.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/')
    if value.lower().startswith(original_prefix.lower()):
        path=value[len(original_prefix):];assert path in r['original_cs'];actual[path]=sha(source/path)
    else:
        assert value.lower().startswith(own.lower()),value
        path=value[len(own):]
        if path=='overlays/ContainerRegistryServerAPICalls.cs':
            change,=r['production_cs_changes'];assert change['overlay']==path
            data=(source/change['path']).read_bytes();before=b'new SortedDictionary<SemanticVersion, string>';after=b'new SortedDictionary<NuGet.Versioning.SemanticVersion, string>'
            assert data.count(before)==1 and (out/path).read_bytes()==data.replace(before,after)
            assert sha(out/path)==change['prepared_sha256'];actual[change['path']]=sha(source/change['path']);overlays[change['path']]=sha(out/path)
        else:
            assert path in ['obj/Release/net8.0/Library.AssemblyInfo.cs','obj/Release/net8.0/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'];generated[path]=sha(out/path)
assert actual==r['original_cs'] and len(actual)==56 and len(generated)==2 and len(overlays)==1
for mapping in ['original_module_assets','original_project_metadata']:
    for path,digest in r[mapping].items():assert sha(source/path)==digest
for path,digest in r['prepared_project_metadata'].items():assert sha(out/path)==digest
cache_prefix=native(cache)+'/'
framework=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31');framework_prefix=native(framework)+'/'
sma=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll');sma_native=native(sma)
refs=[];engines=[]
for value in (out/'obj/Release/net8.0/ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines():
    value=value.replace('\\','/')
    if value.lower().startswith(cache_prefix.lower()):
        path=value[len(cache_prefix):];origin='source-cache';file=cache/path
        dependency,version=path.split('/')[:2]
        with zipfile.ZipFile(cache/dependency/version/(dependency+'.'+version+'.nupkg')) as z:assert file.read_bytes()==z.read('/'.join(path.split('/')[2:]))
    elif value.lower().startswith(framework_prefix.lower()):path=value[len(framework_prefix):];origin='source-framework';file=framework/path
    else:assert value.lower()==sma_native.lower(),value;path=sma.name;origin='source-engine';file=sma;engines.append(sha(sma))
    refs.append(dict(origin=origin,path=path,sha256=sha(file)))
assert len(engines)==1
name='Microsoft.PowerShell.PSResourceGet'
r.update(actual_original_compile_items=actual,actual_overlay_compile_items=overlays,generated_sdk_metadata=generated,actual_references=refs,source_engine_sha256=engines[0],
 implementation_sha256=sha(out/'bin/Release/net8.0'/(name+'.dll')),reference_sha256=sha(out/'obj/Release/net8.0/ref'/(name+'.dll')),documentation_sha256=sha(out/'bin/Release/net8.0'/(name+'.xml')))
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS all56 source inputs, exact NuGet type-qualification overlay, complete module assets, two SDK metadata files and actual source engine/dependency references')
