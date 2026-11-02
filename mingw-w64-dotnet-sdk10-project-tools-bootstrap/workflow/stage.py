"""Stage the three original SDK10 project-tool assemblies and exact source dependencies."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);records=json.loads((root/'build/results.json').read_text());base=prefix/'lib/dotnet10/build-packs/sdk-project-tools-10.0.201-net10-bootstrap';binary=base/'bin';shutil.copytree(root/'build/bin',binary);doc=prefix/'share/doc/dotnet-sdk10-project-tools-bootstrap';checks=doc/'checks';checks.mkdir(parents=True);licenses=prefix/'share/licenses/dotnet-sdk10-project-tools-bootstrap';licenses.mkdir(parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assets=[]
for n in ['check.py','Check.cs','check-resources.py','CheckResources.cs','check-installed.py','MicrosoftAspNetCore.pubkey.hex']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for record in records['projects']:
 for rel in record['original_resources']:
  p=source/rel
  for f in [p,*sorted((p.parent/'xlf').glob(p.stem+'.*.xlf'))]:
   dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
p=source/'test/Microsoft.DotNet.TemplateLocator.Tests/Manifests/AndroidWorkloadManifest.json';dest=validation/p.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for src,name in [(root/'build/results.json','build-results.json'),(root/'source-audit.json','source-audit.json'),(root/'resource-check/results.json','resource-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'localized/results.json','localization-results.json'),(root/'plan/evaluated.json','evaluated-projects.json'),(root/'plan/source-inputs.json','source-inputs.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/name)
feed=installed/'lib/dotnet/library-packs'
for a in records['dependency_assets']:
 if 'archive' not in a:
  if a['id']=='Microsoft.DotNet.NativeWrapper':
   src=Path(a['output']);dest=binary/src.name;shutil.copyfile(src,dest);assets.append(dict(path=dest.relative_to(base).as_posix(),source_installed=src.relative_to(installed).as_posix(),sha256=sha(dest)))
  continue
 archive=Path(a['archive']);assert sha(archive)==a['archive_sha256'];dest=binary/Path(a['member']).name;shutil.copyfile(Path(a['output']),dest);assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=a['member'],sha256=sha(dest)))
 with zipfile.ZipFile(archive) as z:
  folder=Path(a['member']).parent.as_posix()+'/'
  for member in z.namelist():
   if member.startswith(folder) and member.endswith('.resources.dll'):
    path=Path(member);dest=binary/path.parent.name/path.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(z.read(member));assets.append(dict(path=dest.relative_to(base).as_posix(),source_archive=archive.name,source_archive_sha256=sha(archive),member=member,sha256=sha(dest)))
# MSBuild APIs and its source OOB runtime dependencies are supplied unchanged by the pinned host.
msbuild=installed/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap'
for p in msbuild.glob('*.dll'):
 if not (binary/p.name).exists():dest=binary/p.name;shutil.copyfile(p,dest);assets.append(dict(path=dest.relative_to(base).as_posix(),source_installed=p.relative_to(installed).as_posix(),sha256=sha(dest)))
fxr=installed/'lib/dotnet10/host/fxr/10.0.5/hostfxr.dll';dest=binary/'x64/hostfxr.dll';dest.parent.mkdir();shutil.copyfile(fxr,dest);assets.append(dict(path=dest.relative_to(base).as_posix(),source_installed=fxr.relative_to(installed).as_posix(),sha256=sha(dest)))
(doc/'source-dependency-assets.json').write_text(json.dumps(assets,indent=2)+'\n')
for owner in ['dotnet-msbuild18-bootstrap','dotnet-deployment-releases-bootstrap','dotnet-host10-bootstrap','dotnet-sdk10-cli-foundation-bootstrap','dotnet-roslyn53']:
 d=installed/'share/licenses'/owner;assert d.is_dir(),d;shutil.copytree(d,licenses/owner)
for name in ['LICENSE.TXT','ThirdPartyNotices.txt']:
 p=source/name
 if p.exists():shutil.copyfile(p,licenses/name)
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged three original NET10 project tools,26 satellites,source native hostfxr and',len(manifest),'payload files')
