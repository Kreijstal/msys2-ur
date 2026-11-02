"""Stage one exact-version source NuGet archive, validation fixtures and source provenance."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

prepared,checked,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir()
here=Path(__file__).resolve().parent;r=json.loads((prepared/'results.json').read_text());version=r['version'];name='dotnet-wcwidth'+version.split('.')[0]+'-sources'
doc=prefix/'share/doc'/name;checks=doc/'checks';checks.mkdir(parents=True)
feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);archive=prepared/'feed'/('wcwidth.sources.'+version+'.nupkg');shutil.copyfile(archive,feed/archive.name)
for filename in ['check.py','check-installed.py','Assertions.cs','RunTests.cs','ScalarCheck.cs','LoadScalar.cs','check-consumer.py','SDK.Microsoft.TemplateEngine.Cli.csproj','SDK.LICENSE.TXT']:
    shutil.copyfile(here/filename,checks/filename)
shutil.copyfile(prepared/'results.json',doc/'source-results.json');shutil.copyfile(checked/'results.json',doc/'producer-check-results.json');shutil.copyfile(here/'original-source-contracts.json',doc/'original-source-contracts.json');shutil.copyfile(here/'README.md',doc/'README.md')
fixtures=doc/'validation-source/src/Wcwidth.Tests';fixtures.mkdir(parents=True)
for file in (prepared/'source/src/Wcwidth.Tests').glob('*.cs'):shutil.copyfile(file,fixtures/file.name)
license=next(p for p in (prepared/'source').iterdir() if p.name.lower() in {'license','license.md','license.txt'});dest=prefix/'share/licenses'/name;dest.mkdir(parents=True);shutil.copyfile(license,dest/'LICENSE.txt')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS',name,version,'all original source-framework content and',len(manifest),'payload hashes')
