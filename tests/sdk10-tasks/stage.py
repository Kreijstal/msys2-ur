"""Stage original NET10 build tasks/APICompat with source dependency provenance and validation fixtures."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;plan=root/'plan';build=root/'build';source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']);records=json.loads((build/'results.json').read_text());native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());base=prefix/'lib/dotnet10/build-packs/sdk-10.0.201-net10-bootstrap';binary=base/'bin';shutil.copytree(build/'bin',binary);doc=prefix/'share/doc/dotnet-sdk10-tasks-bootstrap';checks=doc/'checks';checks.mkdir(parents=True);validation=doc/'validation-source';owners=prefix/'share/licenses/dotnet-sdk10-tasks-bootstrap';owners.mkdir(parents=True)
for n in ['check.py','check-resources.py','CheckResources.cs','check-installed.py']:shutil.copyfile(here/n,checks/n)
for record in records['projects']:
 for rel in record['original_resources']:
  p=source/rel
  for file in [p,*sorted((p.parent/'xlf').glob(p.stem+'.*.xlf'))]:
   target=validation/file.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
for src,name in [(build/'results.json','build-results.json'),(root/'source-audit.json','source-audit.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'resource-check/results.json','resource-results.json'),(root/'localized/results.json','localization-results.json'),(plan/'source-inputs.json','source-inputs.json'),(plan/'evaluated.json','evaluated-projects.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/name)
# Preserve original task content in its source layout without claiming a complete SDK layout.
content={}
folders=['src/Tasks/Microsoft.NET.Build.Tasks/sdk','src/Tasks/Microsoft.NET.Build.Tasks/targets','src/Tasks/Microsoft.NET.Build.Extensions.Tasks/msbuildExtensions','src/Tasks/Microsoft.NET.Build.Extensions.Tasks/msbuildExtensions-ver','src/Tasks/Common/targets','src/Compatibility/ApiCompat/Microsoft.DotNet.ApiCompat.Task']
for folder in folders:
 for p in sorted((source/folder).rglob('*')):
  if not p.is_file() or (folder.endswith('Microsoft.DotNet.ApiCompat.Task') and p.suffix not in {'.props','.targets'}):continue
  rel=p.relative_to(source);dest=base/'original-content'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);content[rel.as_posix()]=sha(p)
(doc/'original-content-sha256.json').write_text(json.dumps(content,indent=2)+'\n')
assets=[];feed=installed/'lib/dotnet/library-packs'
for asset in records['dependency_assets']:
 if 'archive' not in asset:continue # MSBuild API/runtime stays in the source MSBuild host.
 archive=Path(asset['archive']);assert sha(archive)==asset['archive_sha256'];name=Path(asset['member']).name;dest=binary/name;shutil.copyfile(Path(asset['output']),dest);assert sha(dest)==asset['output_sha256'];assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=asset['member'],sha256=sha(dest)))
 with zipfile.ZipFile(archive) as z:
  for member in z.namelist():
   path=Path(member)
   if member.startswith(str(Path(asset['member']).parent).replace('\\','/')+'/') and path.name.endswith('.resources.dll'):
    dest=binary/path.parent.name/path.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(member));assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=member,sha256=sha(dest)))
   if 'license' in path.name.lower() and not member.endswith('/'):
    dest=owners/asset['id']/path.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(member))
# NuGet source packages keep translations in their shared loose pack, not each NuGet archive.
nuget=installed/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin'
for p in sorted(nuget.glob('*/*.resources.dll')):
 dest=binary/p.parent.name/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest);assets.append(dict(path=dest.relative_to(base).as_posix(),installed_source=p.relative_to(installed).as_posix(),sha256=sha(dest)))
for name,version,member in [('System.Security.Cryptography.Pkcs','8.0.1','runtimes/win/lib/net8.0/System.Security.Cryptography.Pkcs.dll'),('System.Security.Cryptography.ProtectedData','8.0.0','lib/net8.0/System.Security.Cryptography.ProtectedData.dll')]:
 archive=next(p for p in feed.iterdir() if p.name.lower()==f'{name}.{version}.nupkg'.lower())
 with zipfile.ZipFile(archive) as z:
  dest=binary/(name+'.dll');dest.write_bytes(z.read(member));assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=member,sha256=sha(dest)))
  for item in z.namelist():
   if 'license' in Path(item).name.lower() and not item.endswith('/'):
    d=owners/name/Path(item).name;d.parent.mkdir(exist_ok=True);d.write_bytes(z.read(item))
# Installed source owner license files supplement the embedded archive licenses.
for owner in ['dotnet-nuget73-core-bootstrap','dotnet-nuget73-libraries-bootstrap','dotnet-roslyn53','dotnet-sdk10-support-bootstrap','dotnet-deployment-releases-bootstrap','dotnet-newtonsoft-json1303-bootstrap','dotnet-cryptography-pkcs']:
 source_license=installed/'share/licenses'/owner
 assert source_license.is_dir(),source_license
 for p in source_license.rglob('*'):
  if p.is_file():dest=owners/owner/p.relative_to(source_license);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for name in ['LICENSE.TXT','ThirdPartyNotices.txt']:
 p=source/name
 if p.exists():shutil.copyfile(p,owners/name)
(doc/'source-dependency-assets.json').write_text(json.dumps(assets,indent=2)+'\n');manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged',len(manifest),'payload files,',len(content),'original task content files and',len(assets),'source dependency assets')
