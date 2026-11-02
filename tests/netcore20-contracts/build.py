"""Build the selected original NETCore2.0 reference graph from CoreFX8321 source."""
from pathlib import Path
import functools,hashlib,json,os,re,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='f5ebd955cac6ff630689bf6cee2f2c2ffe30b1c7b22c4106d12bb3982abc6c69'
baseline=json.loads((here/'inputs/netcore20-published-metadata.json').read_text());source=out/'source';source.mkdir();hashes={}
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']=='8321c729934c0f8be754953439b88e6e1c120c24'
 entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
 wanted={'dir.props','src/dir.props','src/dir.targets','dir.targets','LICENSE.TXT','THIRD-PARTY-NOTICES.TXT'}
 for file in baseline:
  name=file.removesuffix('.dll');wanted.update(n for n in entries if n.startswith('src/'+name+'/ref/') or n=='src/'+name+'/dir.props')
 for n in wanted:
  assert n in entries,n;file=source/n;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(t.extractfile(entries[n]).read());hashes[n]=sha(file)
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());outputs={};records={};commands=[];env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')))
def build(file):
 if file in outputs:return
 item=baseline[file];name=file.removesuffix('.dll');project=source/'src'/name/'ref'/(name+'.csproj');tree=E.parse(project);refs=[]
 for r in item['references']:
  dep=r.split(', Version=')[0]+'.dll';assert dep in baseline;build(dep);refs.append(outputs[dep])
 selected=[(project.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//{*}Compile')];assert selected and all(p.is_file() for p in selected)
 folder=out/'build'/name;folder.mkdir(parents=True);ref=out/'ref'/file;ref.parent.mkdir(exist_ok=True)
 av=item['identity'].split('Version=')[1].split(',')[0];assert E.parse(source/'src'/name/'dir.props').findtext('.//{*}AssemblyVersion')==av
 info=['[assembly:System.Reflection.AssemblyVersion('+json.dumps(av)+')]']
 for attr in item['attributes']:
  n=attr['type']
  if n.startswith('System.Reflection.') or n in ['System.CLSCompliantAttribute','System.Security.AllowPartiallyTrustedCallersAttribute','System.Runtime.CompilerServices.ReferenceAssemblyAttribute']:
   values=[v.lower() if n=='System.CLSCompliantAttribute' else json.dumps(v) for v in attr['arguments']];info.append('[assembly:'+n+'('+','.join(values)+')]')
 version=folder/'Version.cs';version.write_text('\n'.join(info)+'\n')
 # Preserve the original reference-source and project warning suppressions.
 warnings=['1701','1702']
 for node in E.parse(source/'dir.props').findall('.//{*}PropertyGroup'):
  if node.get('Condition')=="'$(IsReferenceAssembly)' == 'true'":
   for w in node.findall('{*}NoWarn'):warnings.extend(x for x in re.split('[;,]',w.text.replace('$(NoWarn)','')) if x)
 for w in tree.findall('.//{*}NoWarn'):warnings.extend(x for x in re.split('[;,]',w.text.replace('$(NoWarn)','')) if x)
 flags=['/nostdlib+','/target:library','/refonly','/unsafe+','/nullable:disable','/langversion:7.3','/deterministic+','/warnaserror+','/nowarn:'+','.join(warnings),'/publicsign+','/keyfile:"'+native(here/'inputs/Microsoft.snk')+'"','/out:"'+native(ref)+'"','/runtimeMetadataVersion:v4.0.30319']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in selected+[version]]
 rsp=folder/'compile.rsp';rsp.write_text('\n'.join(flags)+'\n');cmd=['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(rsp)]
 with (folder/'compile.log').open('w') as log:r=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(name,(folder/'compile.log').read_text(errors='replace')[-10000:])
 outputs[file]=ref;records[file]=dict(original_CSharp_inputs={str(p.relative_to(source)):sha(p) for p in selected},reference_sha256={p.name:sha(p) for p in refs},original_NoWarn=warnings,DLL_sha256=sha(ref));print('PASS source reference compilation',file,flush=True)
for file in baseline:build(file)
(out/'results.json').write_text(json.dumps(dict(source_commit='8321c729934c0f8be754953439b88e6e1c120c24',source_archive_sha256=sha(archive),original_file_sha256=hashes,original_CSharp_changes=0,libraries=records,commands=commands,reference_only=True,original_buildtools_host_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n')
