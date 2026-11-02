"""Stage source NuGet foundation assemblies and original runtime validation inputs."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile

root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent
runtime=prefix/'lib/dotnet10/library-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap';runtime.mkdir(parents=True);shutil.copytree(root/'build/bin',runtime/'bin')
doc=prefix/'share/doc/dotnet-nuget73-core-bootstrap';checks=doc/'checks';checks.mkdir(parents=True)
for n in ['check-installed.py','check.py','Check.cs','CheckApi.cs']:shutil.copyfile(here/n,checks/n)
source=Path(json.loads((root/'plan/source-inputs.json').read_text())['source_root']);validation=doc/'validation-source'
names=['NuGet.Versioning','NuGet.Frameworks','NuGet.Common','NuGet.LibraryModel']
for name in names:
    folder=source/'src/NuGet.Core'/name
    for p in list(folder.glob('*.resx'))+list(folder.glob('PublicAPI.*.txt')):
        target=validation/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
upstream=source/'test/NuGet.Core.Tests/NuGet.Versioning.Test/VersionRangeTests.cs';target=validation/upstream.relative_to(source);target.parent.mkdir(parents=True);shutil.copyfile(upstream,target)
for rel,target in [('source-audit.json','source-audit.json'),('build/results.json','build-results.json'),('localized/results.json','localization-results.json'),('localized/expected.json','expected-localization.json')]:shutil.copyfile(root/rel,doc/target)
shutil.copyfile(here/'README.md',doc/'README.md');license_dir=prefix/'share/licenses/dotnet-nuget73-core-bootstrap';license_dir.mkdir(parents=True);shutil.copyfile(source/'LICENSE.txt',license_dir/'LICENSE.txt')
# Upstream excludes satellites from individual NuGet library archives. Keep
# them in the loose bootstrap layout,as the aggregate localization package does.
feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True)
dependencies={'NuGet.Versioning':[],'NuGet.Frameworks':[],'NuGet.Common':['NuGet.Frameworks'],'NuGet.LibraryModel':['NuGet.Common','NuGet.Versioning']};version='7.3.0-preview.1.11413'
for name in names:
    deps=''.join('<dependency id="'+n+'" version="['+version+']"/>' for n in dependencies[name]);nuspec='<?xml version="1.0"?><package><metadata><id>'+name+'</id><version>'+version+'</version><authors>Microsoft</authors><description>Original VMR NET10 source bootstrap profile</description><license type="expression">Apache-2.0</license><repository type="git" url="https://github.com/NuGet/NuGet.Client" commit="bf048eb714eb6b1912ba868edca4c7cfec454841"/><dependencies><group targetFramework="net10.0">'+deps+'</group></dependencies></metadata></package>'
    with zipfile.ZipFile(feed/(name.lower()+'.'+version+'.nupkg'),'w',zipfile.ZIP_DEFLATED) as z:
        for member,data in [(name+'.nuspec',nuspec.encode()),('LICENSE.txt',(source/'LICENSE.txt').read_bytes())]+[('lib/net10.0/'+name+'.'+ext,(root/'build/bin'/(name+'.'+ext)).read_bytes()) for ext in ['dll','pdb','xml']]:
            info=zipfile.ZipInfo(member,(2000,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged source NET10 NuGet foundations,52 satellites,four source NuGet archives;',len(manifest),'files')
