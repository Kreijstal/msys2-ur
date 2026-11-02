"""Build Memory's exact Standard1.1 Interop reference from pinned source."""
from pathlib import Path
import functools,hashlib,json,os,re,runpy,subprocess,sys,tarfile,xml.etree.ElementTree as E

sbrp,corefx,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(sbrp)=='2b3136fab488246d0289e622797094e7c2eb29b35f67a9a5cd1312ef3ddfca79'
assert sha(corefx)=='986a512c70d55ed7a1ed8cbb9d8323017c9cc83e77e95e833c7b91f42e4ef601'
prefix='src/referencePackages/src/system.runtime.interopservices/4.3.0/'
selected={prefix+'ref/netstandard1.1/System.Runtime.InteropServices.cs',prefix+'System.Runtime.InteropServices.4.3.0.csproj','src/SourceBuildAssemblyMetdata.cs','src/referencePackages/Directory.Build.props','LICENSE.txt'}
originals={}
for archive,wanted,tag,commit in [(sbrp,selected,'sbrp','5aeee2738338530a92d7f6caa2c7d5f569fed3c4'),(corefx,{'src/System.Runtime.InteropServices/ref/System.Runtime.InteropServices.cs','src/System.Runtime.InteropServices/ref/System.Runtime.InteropServices.csproj','LICENSE','THIRD-PARTY-NOTICES'},'corefx','9688ddbb62c04189cac4c4a06e31e93377dccd41')]:
 with tarfile.open(archive) as t:
  assert t.pax_headers['comment']==commit
  for m in t:
   name=m.name.partition('/')[2]
   if m.isfile() and name in wanted:
    file=out/'source'/tag/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(t.extractfile(m).read());originals[tag+'/'+name]=sha(file)
 assert len([n for n in originals if n.startswith(tag+'/')])==len(wanted)
raw=out/'source/sbrp'/prefix/'ref/netstandard1.1/System.Runtime.InteropServices.cs'
text=raw.read_text(encoding='utf-8-sig');assert 'AssemblyVersionAttribute("4.0.0.0")' in text
assert 'netstandard1.1' in E.parse(out/'source/sbrp'/prefix/'System.Runtime.InteropServices.4.3.0.csproj').findtext('.//TargetFrameworks').split(';')
ported=out/'Interop.Ported.cs';ported.write_text(runpy.run_path(str(here/'port-interop.py'))['port'](text,(out/'source/corefx/src/System.Runtime.InteropServices/ref/System.Runtime.InteropServices.cs').read_text(encoding='utf-8-sig')))
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip())
baseline=json.loads((here/'inputs/published-interop-ns11.json').read_text())['System.Runtime.InteropServices.dll'];matrix=json.loads((here/'inputs/source-contract-build-matrix.json').read_text());closure=set()
def select(key):
 if key in closure:return
 closure.add(key)
 for r in matrix[key]['references']:
  name,v=r.split(', Version=');select(name+'/'+v.split(',')[0])
for r in baseline['references']:
 name,v=r.split(', Version=');select(name+'/'+v.split(',')[0])
contracts=Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts');refs=[contracts/k/(k.split('/')[0]+'.dll') for k in sorted(closure)]
assert all(p.is_file() for p in refs)
warnings=['1701','1702']
for node in E.parse(out/'source/sbrp/src/referencePackages/Directory.Build.props').iter('NoWarn'):warnings.extend(x for x in re.split('[;,]',node.text.replace('$(NoWarn)','')) if x)
ref=out/'ref';ref.mkdir();dll=ref/'System.Runtime.InteropServices.dll'
inputs=[ported,out/'source/sbrp/src/SourceBuildAssemblyMetdata.cs']
args=['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:latest','/deterministic+','/warnaserror+','/nowarn:'+','.join(warnings),'/publicsign+','/keyfile:"'+native(here/'inputs/Microsoft.snk')+'"','/out:"'+native(dll)+'"','/runtimeMetadataVersion:v4.0.30319']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in inputs]
rsp=out/'compile.rsp';rsp.write_text('\n'.join(args)+'\n');command=['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(rsp)]
with (out/'compile.log').open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
assert result.returncode==0,(out/'compile.log').read_text(errors='replace')
record=dict(original_file_sha256=originals,generated_port_sha256=sha(ported),source_reference_sha256={native(p):sha(p) for p in refs},original_source_files_modified_in_place=0,generated_source_port_restores_four_attributes_and_three_COM_structs=True,reference_only=True,original_NoWarn=warnings,command=command,exit_code=result.returncode,DLL_sha256=sha(dll),original_buildtools_host_replayed=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS source Interop4.0.0.0 reference compilation; metadata validation remains required')
