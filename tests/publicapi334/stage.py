"""Stage the source-built NS2 analyzer package, all generated policy assets and checks."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import xml.etree.ElementTree as E
import zipfile

root, prefix = (Path(p).resolve() for p in sys.argv[1:])
prefix.mkdir()
here = Path(__file__).resolve().parent
name = 'dotnet-publicapi334-bootstrap'
doc = prefix / 'share/doc' / name
doc.mkdir(parents=True)
feed = prefix / 'lib/dotnet/library-packs'
feed.mkdir(parents=True)
binary = prefix / 'lib/dotnet/compiler-packs/publicapi-analyzers-3.3.4-ns2-bootstrap'
shutil.copytree(root / 'build/bin', binary)
source = root / 'build/snapshot/source'
config = root / 'package-config'
package_id = 'Microsoft.CodeAnalysis.PublicApiAnalyzers'
package = E.Element('package')
meta = E.SubElement(package, 'metadata')
for key, value in dict(id=package_id, version='3.3.4', authors='Microsoft', developmentDependency='true', description='Source-built original NS2 PublicApiAnalyzers; source Roslyn4.4 and NET10 compiler bootstrap; legacy host compatibility unverified', readme='README.md').items():
    E.SubElement(meta, key).text = value
E.SubElement(meta, 'license', type='expression').text = 'MIT'
E.SubElement(meta, 'repository', type='git', url='https://github.com/dotnet/roslyn-analyzers', commit='22ea6422f85b05ca0793cc3b76375487be407f5d')
members = {package_id + '.nuspec': E.tostring(package, encoding='utf-8', xml_declaration=True), 'README.md': (here / 'README.md').read_bytes(), 'License.txt': (source / 'License.txt').read_bytes()}
for path in sorted(binary.rglob('*')):
    if path.is_file():members['analyzers/dotnet/' + path.relative_to(binary).as_posix()] = path.read_bytes()
for folder, target in [('rulesets','rulesets'),('editorconfig','editorconfig'),('globalconfig','buildTransitive/config'),('build','buildTransitive'),('documentation','documentation')]:
    for path in sorted((config / folder).rglob('*')):
        if path.is_file():members[target + '/' + path.relative_to(config / folder).as_posix()] = path.read_bytes()
for filename in ['install.ps1','uninstall.ps1']:
    members['tools/' + filename] = (config / 'source/assets' / filename).read_bytes()
members['ThirdPartyNotices.txt'] = (config / 'source/assets/ThirdPartyNotices.txt').read_bytes()
members['documentation/Analyzer Configuration.md'] = (config / 'source/docs/Analyzer Configuration.md').read_bytes()
archive = feed / (package_id.lower() + '.3.3.4.nupkg')
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for member, data in sorted(members.items()):
        item = zipfile.ZipInfo(member, (2000,1,1,0,0,0))
        item.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(item, data)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(doc / 'archives.json').write_text(json.dumps(dict(archive=archive.relative_to(prefix).as_posix(), sha256=sha(archive), members={n:hashlib.sha256(b).hexdigest() for n,b in members.items()}), indent=2)+'\n')
for src, dest in [('build/results.json','build-results.json'),('localized/results.json','localization-results.json'),('localized/expected.json','resource-expected.json'),('resources-check/results.json','resource-results.json'),('metadata-check/results.json','metadata-results.json'),('cli-check/results.json','cli-results.json'),('codefix-check/results.json','codefix-results.json'),('package-config/results.json','package-config-results.json'),('package-config-comparison.json','package-config-comparison.json'),('source-audit.json','source-audit.json')]:
    shutil.copyfile(root / src, doc / dest)
for filename in ['README.md','0001-qualify-compatibility-nullability-enum.patch','0002-preserve-warning-policy-with-bootstrap-roslyn.patch','port.py']:
    shutil.copyfile(here / filename, doc / filename)
checks = doc / 'checks'
checks.mkdir()
for filename in ['restore-package.py','check-installed.py','check-cli.py','check-codefix.py','CheckCodeFix.cs','check-resources.py','CheckResources.cs']:
    shutil.copyfile(here / filename, checks / filename)
licenses = prefix / 'share/licenses' / name
licenses.mkdir(parents=True)
shutil.copyfile(source / 'License.txt', licenses / 'License.txt')
shutil.copyfile(config / 'source/assets/ThirdPartyNotices.txt', licenses / 'ThirdPartyNotices.txt')
manifest = {p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc / 'payload-sha256.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('PASS source-built NuGet archive with',len(members),'members and',len(manifest),'installed payload hashes')
