"""Restore all four actual SDK support packages using installed source NuGet7.3."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
out=Path(sys.argv[1]).resolve();out.mkdir();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());feed=prefix/'lib/dotnet/library-packs';host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix();binary=out/'bin';binary.mkdir();assets=[]
names=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel','NuGet.Configuration','NuGet.Packaging','NuGet.Protocol','NuGet.DependencyResolver.Core','NuGet.ProjectModel','NuGet.Credentials','NuGet.Resolver','NuGet.Commands']
entries=[(n,'7.3.0-preview.1.11413','lib/net10.0/'+n+'.dll') for n in names]
entries += [('Newtonsoft.Json','13.0.3','lib/netstandard2.0/Newtonsoft.Json.dll'),('System.Security.Cryptography.Pkcs','8.0.1','runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'),('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll'),('Microsoft.Extensions.FileSystemGlobbing','6.0.0','lib/net8.0/Microsoft.Extensions.FileSystemGlobbing.dll'),('Microsoft.Extensions.FileProviders.Abstractions','6.0.0','lib/net8.0/Microsoft.Extensions.FileProviders.Abstractions.dll'),('Microsoft.Extensions.Primitives','6.0.0','lib/net8.0/Microsoft.Extensions.Primitives.dll')]
for name,version,member in entries:
    archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower())
    with zipfile.ZipFile(archive) as z:data=z.read(member)
    (binary/(name+'.dll')).write_bytes(data);assets.append(dict(package=name,version=version,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),member=member,member_sha256=hashlib.sha256(data).hexdigest()))
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/out:"'+native(binary/'SupportRestore.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+list(binary.glob('*.dll'))]+['"'+native(here/'SupportRestore.cs')+'"']
(out/'compile.rsp').write_text('\n'.join(args)+'\n');(binary/'SupportRestore.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),NUGET_SCRATCH=native(out/'scratch'),NUGET_HTTP_CACHE_PATH=native(out/'http-cache'),NUGET_PLUGINS_CACHE_PATH=native(out/'plugins-cache'));commands=[]
for label,cmd in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(out/'compile.rsp')]),('execute',[host,binary/'SupportRestore.dll',out/'owned-work',feed])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=240)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,installed_source_nuget_engine_assets=assets,actual_four_support_package_restore=True,original_framework_asset_selection_verified=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print((out/'execute.log').read_text(encoding='utf-8'))
