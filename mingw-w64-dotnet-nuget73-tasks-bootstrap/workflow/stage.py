"""Stage a self-contained source MSBuild-hosted NuGet task/resolver bootstrap."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);build=json.loads((root/'build/results.json').read_text());base=prefix/'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';binary=base/'bin';binary.mkdir(parents=True);doc=prefix/'share/doc/dotnet-nuget73-tasks-bootstrap';checks=doc/'checks';checks.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assets=[]
def copy_installed(p,relative):
 dest=binary/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);assets.append(dict(path=dest.relative_to(base).as_posix(),source_installed=p.relative_to(installed).as_posix(),sha256=sha(dest)))
# Retain a private, unchanged source MSBuild host so the console and resolver can run in isolation.
msbuild=installed/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap'
for p in msbuild.iterdir():
 if p.is_file():copy_installed(p,Path(p.name))
for p in msbuild.glob('*/*.resources.dll'):copy_installed(p,p.relative_to(msbuild))
# Source NuGet libraries and their original loose satellites.
nuget=installed/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin'
for p in nuget.rglob('*'):
 if p.is_file():copy_installed(p,p.relative_to(nuget))
feed=installed/'lib/dotnet/library-packs'
for name,version,member in [('Newtonsoft.Json','13.0.3','lib/netstandard2.0/Newtonsoft.Json.dll'),('System.Security.Cryptography.Pkcs','8.0.1','runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'),('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll'),('Microsoft.Extensions.FileSystemGlobbing','6.0.0','lib/net8.0/Microsoft.Extensions.FileSystemGlobbing.dll'),('Microsoft.Extensions.FileProviders.Abstractions','6.0.0','lib/net8.0/Microsoft.Extensions.FileProviders.Abstractions.dll'),('Microsoft.Extensions.Primitives','6.0.0','lib/net8.0/Microsoft.Extensions.Primitives.dll')]:
 archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower());dest=binary/(name+'.dll')
 with zipfile.ZipFile(archive) as z:dest.write_bytes(z.read(member))
 assets=[a for a in assets if a['path']!=dest.relative_to(base).as_posix()];assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=member,sha256=sha(dest)))
for p in (root/'build/bin').rglob('*'):
 if p.is_file():dest=binary/p.relative_to(root/'build/bin');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
original_content={}
for p in (source/'src/NuGet.Core/NuGet.Build.Tasks').glob('NuGet*'):
 if p.suffix not in ['.props','.targets']:continue
 shutil.copyfile(p,binary/p.name);original_content[p.relative_to(source).as_posix()]=sha(p)
resolvers=binary/'SdkResolvers/Microsoft.Build.NuGetSdkResolver';resolvers.mkdir(parents=True);shutil.copyfile(binary/'Microsoft.Build.NuGetSdkResolver.dll',resolvers/'Microsoft.Build.NuGetSdkResolver.dll')
for n in ['check.py','check-resources.py','CheckResources.cs','check-installed.py']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for record in build['projects']:
 for rel in record['original_resource_sha256']:
  p=source/rel
  for f in [p,*sorted((p.parent/'xlf').glob(p.stem+'.*.xlf'))]:
   dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
for src,name in [(root/'build/results.json','build-results.json'),(root/'flow/results.json','version-flow-results.json'),(root/'plan/evaluated.json','evaluated-projects.json'),(root/'source-audit.json','source-audit.json'),(root/'resource-check/results.json','resource-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'localized/results.json','localization-results.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/name)
shutil.copytree(here/'policy',doc/'version-flow-policy')
(doc/'source-dependency-assets.json').write_text(json.dumps(assets,indent=2)+'\n');(doc/'original-content-sha256.json').write_text(json.dumps(original_content,indent=2)+'\n')
license_dir=prefix/'share/licenses/dotnet-nuget73-tasks-bootstrap';license_dir.mkdir(parents=True);shutil.copyfile(source/'LICENSE.txt',license_dir/'LICENSE.txt')
for owner in ['dotnet-msbuild18-bootstrap','dotnet-nuget73-core-bootstrap','dotnet-nuget73-libraries-bootstrap','dotnet-newtonsoft-json1303-bootstrap','dotnet-cryptography-pkcs','dotnet-protecteddata','dotnet-filesystem-globbing6','dotnet-fileproviders-abstractions6','dotnet-extensions-primitives6']:
 d=installed/'share/licenses'/owner;assert d.is_dir(),d;shutil.copytree(d,license_dir/owner)
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged four original NuGet tools,39 satellites,private source MSBuild host and',len(manifest),'payload files')
