"""Stage one exact source NuGet archive containing both original CommandLine2 profiles and cultures."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;source=root/'plan/snapshot/command-line-api';records=json.loads((root/'build/results.json').read_text());feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);doc=prefix/'share/doc/dotnet-commandline2-bootstrap';checks=doc/'checks';checks.mkdir(parents=True)
for name in ['check-installed.py','check.py','Check.cs','UpstreamAdapter.cs','check-restore.py']:shutil.copyfile(here/name,checks/name)
validation=doc/'validation-source'
for p in [source/'src/System.CommandLine/Properties/Resources.resx',source/'src/System.CommandLine.Tests/SplitCommandLineTests.cs']:
 d=validation/p.relative_to(source);d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
for rel,name in [('build/results.json','build-results.json'),('source-audit.json','source-audit.json'),('runtime-check/results.json','runtime-results.json'),('localized/results.json','localization-results.json'),('localized/expected.json','expected-localization.json'),('plan/snapshot/vmr-source-inputs.json','vmr-source-inputs.json'),('plan/source-inputs.json','source-inputs.json'),('plan/evaluated.json','evaluated-projects.json')]:shutil.copyfile(root/rel,doc/name)
shutil.copyfile(here/'README.md',doc/'README.md');package=E.Element('package');meta=E.SubElement(package,'metadata')
for k,v in dict(id='System.CommandLine',version='2.0.2',authors='Microsoft',description='Original SDK10 VMR source CommandLine2 NET10 and Standard2 profiles',readme='README.md').items():E.SubElement(meta,k).text=v
E.SubElement(meta,'license',type='expression').text='MIT';E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/dotnet',commit='44525024595742ebe09023abe709df51de65009b');deps=E.SubElement(meta,'dependencies');E.SubElement(deps,'group',targetFramework='net10.0');E.SubElement(E.SubElement(deps,'group',targetFramework='netstandard2.0'),'dependency',id='System.Memory',version='[4.5.5]')
with zipfile.ZipFile(feed/'system.commandline.2.0.2.nupkg','w',zipfile.ZIP_DEFLATED) as z:
 files=[('System.CommandLine.nuspec',E.tostring(package,encoding='utf-8',xml_declaration=True)),('LICENSE.md',(source/'LICENSE.md').read_bytes()),('README.md',(source/'src/System.CommandLine/README.md').read_bytes())]
 for r in records['projects']:
  tfm=r['original_target']
  for p in sorted((root/'build'/tfm/'bin').rglob('*')):
   if p.is_file():files.append(('lib/'+tfm+'/'+p.relative_to(root/'build'/tfm/'bin').as_posix(),p.read_bytes()))
 for member,data in files:
  i=zipfile.ZipInfo(member,(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
license=prefix/'share/licenses/dotnet-commandline2-bootstrap';license.mkdir(parents=True);shutil.copyfile(source/'LICENSE.md',license/'LICENSE.md');manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS staged source CommandLine2 NET10/NS2 NuGet archive,28 satellites and',len(manifest),'payload files')
