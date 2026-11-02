"""Compare every production/generation input to the pinned original source archive."""
from pathlib import Path
import hashlib,json,sys,tarfile,zipfile
archive,root=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();expected={}
for profile in ['windows-release','generic-release','asn1-release']:
 d=json.loads((root/profile/'results.json').read_text())
 for n,h in d['original_selected_cs_sha256'].items():assert n not in expected or expected[n]==h;expected[n]=h
for d in json.loads((root/'interop/audit-results.json').read_text())['projects'].values():
 for n,h in d['original_cs_sha256'].items():assert n not in expected or expected[n]==h;expected[n]=h
for name in ['System.Security.Cryptography.Pkcs','System.Formats.Asn1']:
 for rel in ['src/'+name+'.csproj','ref/'+name+'.csproj','ref/'+name+'.cs','ref/'+name+'.netcoreapp.cs','src/Resources/Strings.resx','Directory.Build.props','src/CompatibilitySuppressions.xml']:
  p=root/'r/src/libraries'/name/rel
  if p.is_file():expected[p.relative_to(root/'r').as_posix()]=sha(p)
asn=json.loads((root/'asn-build2/results.json').read_text());assert asn['generated_models']==59
for n,d in asn['inputs'].items():expected[n]=d['xml_sha256'];expected[n+'.cs']=d['original_generated_sha256']
for n in ['src/libraries/Directory.Build.targets','src/libraries/Directory.Build.props','src/libraries/NetCoreAppLibrary.props','eng/Versions.props','eng/versioning.targets','src/libraries/Common/src/System/Security/Cryptography/Asn1/AsnXml.targets','src/libraries/Common/src/System/Security/Cryptography/Asn1/asn.xslt','src/libraries/Common/src/System/Security/Cryptography/Asn1/asn.xsd','src/libraries/Common/src/System/Security/Cryptography/Asn1Reader/System.Security.Cryptography.Asn1Reader.Shared.projitems']:expected[n]=sha(root/'r'/n)
seen=set()
with tarfile.open(archive) as t:
 for m in t:
  n=m.name.partition('/')[2]
  if m.isfile() and n in expected:assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==expected[n],n;seen.add(n)
assert seen==set(expected)
for plan in ['plan','plan-generic','plan-asn1']:
 d=next(iter(json.loads((root/plan/'evaluated.json').read_text()).values()));assert 'DEBUG' not in d['properties']['DefineConstants'].split(';')
with zipfile.ZipFile(root/'feed/system.security.cryptography.pkcs.9.0.11.nupkg') as z:
 for profile,member in [('windows','runtimes/win/lib/net9.0/'),('generic','lib/net9.0/')]:
  for ext in ['dll','pdb']:assert z.read(member+'System.Security.Cryptography.Pkcs.'+ext)==(root/(profile+'-release')/('System.Security.Cryptography.Pkcs.'+ext)).read_bytes()
 assert z.read('lib/net9.0/System.Security.Cryptography.Pkcs.xml')==(root/'documentation/System.Security.Cryptography.Pkcs.xml').read_bytes()
(root/'source-audit.json').write_text(json.dumps(dict(original_archive_inputs_verified=len(seen),original_input_sha256=expected,asn_models_regenerated=59,original_production_cs_changes=0,release_symbols_verified=True,private_asn1_built_and_executed=True,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS',len(seen),'original source/project/resource/generation inputs;both release profiles and package bytes')
