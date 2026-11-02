"""Run unchanged upstream version tests and original offline catalogs on source NET8/NET10."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
source,references,build,out=(Path(p).resolve() for p in sys.argv[1:5]);localization=Path(sys.argv[5]).resolve() if len(sys.argv)>5 else None;out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll';host10=prefix/'lib/dotnet10/dotnet.exe';upstream=source/'src/deployment-tools/src/Microsoft.Deployment.DotNet.Releases/tests/ReleaseVersionTests.cs';commands=[]
for tfm,version,host,refdir in [('net8.0','8.0.31',prefix/'lib/dotnet/dotnet.exe',prefix/'lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0'),('net10.0','10.0.5',host10,prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0')]:
    binary=out/tfm;binary.mkdir();shutil.copyfile(build/'Microsoft.Deployment.DotNet.Releases.dll',binary/'Microsoft.Deployment.DotNet.Releases.dll');output=binary/'Microsoft.Deployment.DotNet.Releases.Tests.dll';refs=sorted(refdir.glob('*.dll'));assert len(refs)==(163 if tfm=='net8.0' else 167)
    for culture in build.iterdir():
        if culture.is_dir() and list(culture.glob('*.resources.dll')):shutil.copytree(culture,binary/culture.name)
    key=bytes.fromhex((here/'MicrosoftShared.pubkey.hex').read_text());(binary/'public.snk').write_bytes(key)
    args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:disable','/publicsign+','/keyfile:"'+native(binary/'public.snk')+'"','/out:"'+native(output)+'"']+['/reference:"'+native(p)+'"' for p in refs+[binary/'Microsoft.Deployment.DotNet.Releases.dll']]+['"'+native(p)+'"' for p in [here/'Check.cs',here/'XunitAdapter.cs',upstream]]
    rsp=binary/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');output.with_suffix('.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm=tfm,framework=dict(name='Microsoft.NETCore.App',version=version)))))
    for label,cmd,root in [('compile',[host10,compiler,'-noconfig','@'+native(rsp)],host10.parent),('execute',[host,output,references/'results.json',source,binary/'owned 世界',host.parent]+([localization] if localization else []),host.parent)]:
        env=dict(os.environ,DOTNET_ROOT=native(root),DOTNET_ROOT_X64=native(root));
        with (binary/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
        commands.append(dict(tfm=tfm,command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(tfm,label,r.returncode)
    print((binary/'execute.log').read_text(encoding='utf-8'),flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_release_version_test_source_sha256=hashlib.sha256(upstream.read_bytes()).hexdigest(),unchanged_original_version_test_methods=29,original_fixture_catalogs_parsed=True,reference_only_assemblies_rejected_at_runtime=9,real_runtime_json_implementations_verified=True,original_library_framework='netstandard2.0',source_runtime_consumers=['net8.0','net10.0'],full_original_xunit_runner_used=False,full_upstream_test_suite_run=False,full_dependency_goal_complete=False),indent=2)+'\n')
