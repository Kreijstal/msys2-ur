"""Gate original NET6 selection, C# bytes, actual signing/references and JSON generator."""
import os
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile

source,out,cache=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip().replace('\\','/')
own_prefix=native(out)+'/';cache_prefix=native(cache)+'/'
framework=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31');framework_prefix=native(framework)+'/'
r=json.loads((out/'source-inventory.json').read_text());records={}
for name,tree in r['original_project_trees'].items():
    folder=out/'src/client'/name;original=source/'src/client'/name;intermediate=folder/'obj/Release/net8.0'
    all_cs={p.relative_to(source).as_posix() for p in original.rglob('*.cs')}
    if name=='Microsoft.Identity.Client':
        prefix='src/client/'+name+'/'
        expected={p for p in all_cs if not p.startswith(prefix+'Platforms/') and not (p.startswith(prefix+'Resources/') and '/' not in p[len(prefix+'Resources/'):])}
        expected.discard(prefix+'PlatformsCommon/PlatformNotSupported/ApiConfig/SystemWebViewOptions.cs')
        project=E.parse(original/(name+'.csproj'));selected=[]
        for group in project.getroot().findall('ItemGroup'):
            if group.get('Condition','').strip()!="'$(TargetFramework)' == '$(TargetFrameworkNet6)'":continue
            for item in group.findall('Compile'):
                if item.get('Include'):
                    relative=item.get('Include').removeprefix('$(PathToMsalSources)\\').replace('\\','/')
                    assert relative.endswith('/**/*.cs');relative=relative[:-len('**/*.cs')]
                    selected.append(relative);expected|={p for p in all_cs if p.startswith(prefix+relative)}
                else:assert item.get('Remove')=='$(PathToMsalSources)\\json\\**\\*.*'
        assert len(selected)==5
        expected={p for p in expected if not p.startswith(prefix+'json/')}
        flags=set((intermediate/'DefineConstants.txt').read_text(encoding='utf-8-sig').replace(';','\n').split())
        assert {'NET_CORE','SUPPORTS_CONFIDENTIAL_CLIENT','SUPPORTS_CUSTOM_CACHE','SUPPORTS_BROKER','SUPPORTS_WIN32','SUPPORTS_OTEL','SUPPORTS_SYSTEM_TEXT_JSON'}<=flags
    else:expected=all_cs;flags=set()
    actual={};generated={}
    for value in (intermediate/'Compile.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/');assert value.lower().startswith(own_prefix.lower()),value
        path=value[len(own_prefix):]
        if path in tree:
            assert path.endswith('.cs') and sha(out/path)==sha(source/path);actual[path]=sha(out/path)
        else:
            assert path in [str(intermediate.relative_to(out)).replace('\\','/')+'/'+name+'.AssemblyInfo.cs',str(intermediate.relative_to(out)).replace('\\','/')+'/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs'],path
            generated[path]=sha(out/path)
    assert set(actual)==expected and len(generated)==2,(name,len(actual),len(expected))
    assert (intermediate/'SignAssembly.txt').read_text(encoding='utf-8-sig').strip().lower()=='true'
    assert (intermediate/'PublicSign.txt').read_text(encoding='utf-8-sig').strip().lower() in ['', 'false']
    refs=[]
    for value in (intermediate/'ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/')
        if value.lower().startswith(cache_prefix.lower()):
            path=value[len(cache_prefix):];origin='source-cache';file=cache/path
            dependency,version=path.split('/')[:2]
            assert dependency in ['microsoft.identitymodel.abstractions','system.text.json','system.security.cryptography.protecteddata'],path
            with zipfile.ZipFile(cache/dependency/version/(dependency+'.'+version+'.nupkg')) as z:assert file.read_bytes()==z.read('/'.join(path.split('/')[2:]))
        elif value.lower().startswith(framework_prefix.lower()):path=value[len(framework_prefix):];origin='framework';file=framework/path
        else:
            path=value[len(own_prefix):];assert value.lower().startswith(own_prefix.lower()) and name=='Microsoft.Identity.Client.Extensions.Msal'
            assert path=='src/client/Microsoft.Identity.Client/bin/Release/net8.0/Microsoft.Identity.Client.dll';origin='original-source-project';file=out/path
            assert sha(file)==records['Microsoft.Identity.Client']['implementation_sha256']
        refs.append(dict(origin=origin,path=path,sha256=sha(file)))
    reference=folder/'obj/Release/net8.0/ref'/(name+'.dll');target=folder/'bin/Release/net8.0'
    records[name]=dict(actual_original_compile_items=actual,generated_sdk_metadata=generated,actual_references=refs,original_feature_flags=sorted(flags),
        implementation_sha256=sha(target/(name+'.dll')),reference_sha256=sha(reference),documentation_sha256=sha(target/(name+'.xml')))
    if name=='Microsoft.Identity.Client':
        generated_json={p.relative_to(out).as_posix():sha(p) for p in (intermediate/'generated').rglob('*.cs')};assert generated_json
        generators=[]
        for value in (intermediate/'Analyzer.txt').read_text(encoding='utf-8-sig').splitlines():
            value=value.replace('\\','/')
            if not value.endswith('/System.Text.Json.SourceGeneration.dll'):continue
            assert value.lower().startswith(cache_prefix.lower())
            path=value[len(cache_prefix):];assert path=='system.text.json/8.0.5/analyzers/dotnet/roslyn4.4/cs/System.Text.Json.SourceGeneration.dll'
            with zipfile.ZipFile(cache/'system.text.json/8.0.5/system.text.json.8.0.5.nupkg') as z:assert (cache/path).read_bytes()==z.read(path.split('/8.0.5/')[1])
            generators.append(dict(path=path,sha256=sha(cache/path)))
        assert len(generators)==1
        records[name].update(json_generated_files=generated_json,json_source_generators=generators)
        directive='src/client/Microsoft.Identity.Client/Properties/Microsoft.Identity.Client.rd.xml'
        assert (out/directive).read_bytes()==(source/directive).read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
for path,digest in r['original_project_metadata'].items():assert sha(source/path)==digest
for path,digest in r['prepared_project_metadata'].items():assert sha(out/path)==digest
r['projects']=records;(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS exact original NET6 branch/compiler bytes, all feature flags, full signing, source dependency references, SDK metadata and selected source JSON generator')
for name,record in records.items():print(name,len(record['actual_original_compile_items']),'original C# inputs')
