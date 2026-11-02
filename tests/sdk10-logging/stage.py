"""Stage original NET10 configuration archives and original NS2 Binder analyzer/target assets."""
from pathlib import Path
import hashlib,json,shutil,sys,xml.etree.ElementTree as E,zipfile
root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent;source=root/'plan/snapshot/runtime';records=json.loads((root/'build/results.json').read_text());name='dotnet-sdk10-logging-bootstrap';doc=prefix/'share/doc'/name;checks=doc/'checks';checks.mkdir(parents=True);feed=prefix/'lib/dotnet/library-packs';feed.mkdir(parents=True);binary=prefix/'lib/dotnet10/library-packs/logging-10.0.2-net10-bootstrap/bin';shutil.copytree(root/'build/bin',binary);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for n in ['check-restore.py','check.py','Check.cs','check-resources.py','CheckResources.cs','check-api.py','CompareApi.cs','check-installed.py','MicrosoftAspNetCore.pubkey.hex']:shutil.copyfile(here/n,checks/n)
validation=doc/'validation-source'
for r in records['projects']:
 for rel in r['original_resources']:
  p=source/rel
  for f in [p,*sorted((p.parent/'xlf').glob(p.stem+'.*.xlf'))]:
   dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
 if r['original_framework']=='net10.0':
  for f in (source/'src/libraries'/r['assembly']/'ref').glob('*'):
   if f.is_file():dest=validation/f.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dest)
for src,dest in [(root/'build/results.json','build-results.json'),(root/'localized/results.json','localization-results.json'),(root/'source-audit.json','source-audit.json'),(root/'resource-check/results.json','resource-results.json'),(root/'runtime-check/results.json','runtime-results.json'),(root/'api-check/results.json','api-results.json'),(root/'plan/source-inputs.json','source-inputs.json'),(here/'README.md','README.md')]:shutil.copyfile(src,doc/dest)
# Run the upstream packaging target for the Options analyzer-selection file.
import os,subprocess
native=lambda p:Path(p).resolve().as_posix()
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(PackageId='Microsoft.Extensions.Options',IntermediateOutputPath=native(root/'packaging')+'/',DotNetBuildSourceOnly='true').items():E.SubElement(pg,k).text=v
E.SubElement(p,'Import',Project=native(source/'eng/packaging.targets'));E.ElementTree(p).write(root/'GeneratePackageTargets.proj',encoding='utf-8',xml_declaration=True)
installed=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=installed/'lib/dotnet/dotnet.exe';cmd=[host,'msbuild',root/'GeneratePackageTargets.proj','-t:GenerateMultiTargetRoslynComponentTargetsFile','-nologo','-v:minimal']
with (root/'package-targets.log').open('w',encoding='utf-8') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent)),timeout=120)
assert r.returncode==0;target=root/'packaging/MultiTargetRoslynComponent.targets';assert target.is_file()
(doc/'package-targets-command.json').write_text(json.dumps(dict(command=[str(p) for p in cmd],exit_code=r.returncode,original_packaging_target_executed=True),indent=2)+'\n')
archives={};project_names={r['assembly'] for r in records['projects']}|{a['id'] for a in records['dependency_assets']}

for r in records['projects']:
 if r['original_framework']!='net10.0':continue
 assembly=r['assembly'];package=E.Element('package');meta=E.SubElement(package,'metadata')
 for k,v in dict(id=assembly,version='10.0.2',authors='Microsoft',description='Original SDK-pinned NET10 logging/options/console bootstrap with original NS2 Options generator').items():E.SubElement(meta,k).text=v
 E.SubElement(meta,'license',type='expression').text='MIT';E.SubElement(meta,'repository',type='git',url='https://github.com/dotnet/dotnet',commit='44525024595742ebe09023abe709df51de65009b');deps=E.SubElement(E.SubElement(meta,'dependencies'),'group',targetFramework='net10.0')
 for edge in r['original_project_edges']:
  if edge['metadata'].get('ReferenceOutputAssembly','true').lower()=='false':continue
  assert edge['project'] in project_names;E.SubElement(deps,'dependency',id=edge['project'],version='[10.0.2]')
 members={assembly+'.nuspec':E.tostring(package,encoding='utf-8',xml_declaration=True),'LICENSE.TXT':(source/'LICENSE.TXT').read_bytes()}
 for ext in r['output_sha256']:members['lib/net10.0/'+assembly+'.'+ext]=(binary/(assembly+'.'+ext)).read_bytes()
 if assembly=='Microsoft.Extensions.Options':
  members['buildTransitive/netstandard2.0/'+assembly+'.targets']=target.read_bytes()
  gen=assembly+'.SourceGeneration'
  for p in [binary/(gen+'.dll'),binary/(gen+'.pdb'),*sorted(binary.glob('*/'+gen+'.resources.dll'))]:members['analyzers/dotnet/roslyn4.4/cs/'+p.relative_to(binary).as_posix()]=p.read_bytes()
 archive=feed/(assembly.lower()+'.10.0.2.nupkg')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
  for member,data in members.items():
   i=zipfile.ZipInfo(member,(2000,1,1,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,data)
 archives[assembly]=dict(archive=archive.relative_to(prefix).as_posix(),sha256=sha(archive),members={k:hashlib.sha256(v).hexdigest() for k,v in members.items()})
(doc/'archives.json').write_text(json.dumps(archives,indent=2)+'\n');licenses=prefix/'share/licenses'/name;licenses.mkdir(parents=True)
for n in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:shutil.copyfile(source/n,licenses/n)
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()};(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS six NET10 archives, original NS2 Options generator/satellites/target and',len(manifest),'payload hashes')
