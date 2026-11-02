"""Reproduce every original ASN.1 source using the upstream XSLT and comparer."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();plan=Path(sys.argv[2]).resolve();out=Path(sys.argv[3]).resolve();out.mkdir()
source=root/'r';native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
e=json.loads((plan/'evaluated.json').read_text());projects=json.loads((plan/'projects.json').read_text());native_source=native(source)
def file(name,value):
 value=value.replace('\\','/')
 if value.lower().startswith(native_source.lower()+'/'):return source/value[len(native_source)+1:]
 return (source/projects[name]['project']).parent/value
inputs=[]
for name,entry in e.items():
 for item in entry['items']['AsnXml']:
  p=file(name,item['identity']);assert p.is_file() and Path(str(p)+'.cs').is_file(),p
  if p not in inputs:inputs.append(p)
assert len(inputs)==56,len(inputs)
common=source/'src/libraries/Common/src/System/Security/Cryptography/Asn1'
p=E.Element('Project');E.SubElement(p,'Import',Project=native(common/'AsnXml.targets'));t=E.SubElement(p,'Target',Name='RegenerateAndCompare')
for i,sourcefile in enumerate(inputs):
 target=out/(str(i)+'-'+sourcefile.stem+'.cs')
 E.SubElement(t,'XslTransformation',XslInputPath=native(common/'asn.xslt'),XmlInputPaths=native(sourcefile),OutputPaths=native(target))
 task=E.SubElement(t,'CompareFilesIgnoreLineEndings',GeneratedFile=native(target),ExistingFile=native(Path(str(sourcefile)+'.cs')))
 E.SubElement(task,'Output',TaskParameter='ContentsDiffer',PropertyName='Different'+str(i))
 E.SubElement(t,'Error',Condition="'$(Different"+str(i)+")'=='true'",Text='Original ASN.1 regeneration differs: '+sourcefile.name)
E.indent(p);project=out/'Regenerate.proj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),DOTNET_CLI_HOME=native(out/'cli-home'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
command=['/clang64/lib/dotnet/dotnet.exe','msbuild',native(project),'-nologo','-t:RegenerateAndCompare','-v:minimal']
with (out/'generate.log').open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(r.returncode,out/'generate.log')
record=dict(command=command,exit_code=0,original_xslt_sha256=sha(common/'asn.xslt'),original_target_and_comparer_sha256=sha(common/'AsnXml.targets'),original_generated_sources={p.relative_to(source).as_posix():dict(xml_sha256=sha(p),checked_in_cs_sha256=sha(Path(str(p)+'.cs')),fresh_generated_sha256=sha(out/(str(i)+'-'+p.stem+'.cs'))) for i,p in enumerate(inputs)},all56_match_ignoring_only_original_line_ending_policy=True,original_source_files_written=False,full_framework_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS all56 original ASN.1 XSLT outputs and original comparer; no original source writes')
