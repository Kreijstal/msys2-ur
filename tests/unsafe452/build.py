"""Assemble all original Unsafe4.5.2 runtime profiles from unchanged CoreFX IL."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
archive,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive)=='f8043a5f7853d2b667f75a3e530ba7b5e9c1a6651949d0ce2a00c044a6697b54'
source=out/'source';source.mkdir();hashes={};commit='02b11eeee1fbc5f3ef43a1452fe07efd25fa1715'
with tarfile.open(archive) as t:
 assert t.pax_headers['comment']==commit
 for m in t:
  name=m.name.partition('/')[2]
  if not m.isfile() or not (name.startswith('src/System.Runtime.CompilerServices.Unsafe/') or name in {'LICENSE.TXT','THIRD-PARTY-NOTICES.TXT','dir.props','dir.targets'}):continue
  data=t.extractfile(m).read();assert data[:2]!=b'MZ' and not name.endswith(('.dll','.exe','.pdb','.nupkg'))
  p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);hashes[name]=hashlib.sha256(data).hexdigest()
policy=E.parse(source/'src/System.Runtime.CompilerServices.Unsafe/dir.props');assert policy.findtext('.//{*}PackageVersion')=='4.5.2' and policy.findtext('.//{*}AssemblyVersion')=='4.0.4.1'
here=Path(__file__).parent;key=here/'inputs/Microsoft.snk';assert hashlib.sha1(key.read_bytes()).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
original=source/'src/System.Runtime.CompilerServices.Unsafe/src/System.Runtime.CompilerServices.Unsafe.il';assembler=Path('/clang64/bin/ilasm10.exe');commands=[];profiles={}
version=json.loads((here/'inputs/version-policy.json').read_text())['native_VERSIONINFO']
resource=out/'native-resource';resource.mkdir()
rc=['#pragma code_page(65001)','LANGUAGE 0,0','1 VERSIONINFO','FILEVERSION 4,6,26919,2','PRODUCTVERSION 0,0,0,0','FILEFLAGSMASK 0x3f','FILEFLAGS 0x0','FILEOS 0x4','FILETYPE 0x2','FILESUBTYPE 0x0','BEGIN','BLOCK "StringFileInfo"','BEGIN','BLOCK "000004b0"','BEGIN']
for k in ['CompanyName','FileDescription','FileVersion','InternalName','LegalCopyright','OriginalFilename','ProductVersion','ProductName','Comments','LegalTrademarks','PrivateBuild','SpecialBuild']:
 literal=json.dumps(version[k],ensure_ascii=True);literal=literal.replace('\\u','\\x');rc.append('VALUE '+json.dumps(k)+', L'+literal)
rc+=['END','END','BLOCK "VarFileInfo"','BEGIN','VALUE "Translation", 0, 1200','END','END']
(resource/'version.rc').write_text('\n'.join(rc)+'\n',encoding='utf-8')
def tool(label,cmd,cwd=None):
 with (out/(label+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(label,(out/(label+'.log')).read_text(errors='replace')[-5000:])
tool('rc',['/clang64/bin/llvm-rc.exe','-fo','version.res','version.rc'],resource)
tool('cvtres',['/clang64/bin/llvm-cvtres.exe','-machine:x86','-out:version.obj','version.res'],resource)

for tfm,include in [('netstandard1.0','netstandard1.0'),('netstandard2.0','netstandard'),('netcoreapp2.0','netcoreapp')]:
 folder=out/tfm;folder.mkdir();output=folder/'System.Runtime.CompilerServices.Unsafe.dll';header=original.parent/'include'/include
 cmd=[native(assembler),'-DLL','-DET','-DEBUG=OPT','-KEY='+native(key),'-INCLUDE='+native(header),'-RESOURCE='+native(resource/'version.obj'),'-OUTPUT='+native(output),native(original)]
 with (folder/'build.log').open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=result.returncode));assert result.returncode==0,(tfm,(folder/'build.log').read_text(errors='replace')[-5000:])
 profiles[tfm]=dict(original_include_directory=str(header.relative_to(source)),source_IL_sha256=sha(original),source_include_sha256=sha(header/'coreassembly.h'),DLL_sha256=sha(output),PDB_sha256=sha(output.with_suffix('.pdb')))
 print('PASS original Unsafe4.5.2 IL profile',tfm,flush=True)
references={}
for tfm in ['netstandard1.0','netstandard2.0']:
 folder=out/'ref'/tfm;folder.mkdir(parents=True)
 baseline=json.loads((here/'inputs'/('reference-'+tfm+'.json')).read_text())['System.Runtime.CompilerServices.Unsafe.dll']
 info=['[assembly:System.Reflection.AssemblyVersion("4.0.4.1")]','[assembly:System.Runtime.CompilerServices.ReferenceAssembly]']
 for attr in baseline['attributes']:
  if attr['type'].startswith('System.Reflection.') or attr['type']=='System.Security.AllowPartiallyTrustedCallersAttribute':
   info.append('[assembly:'+attr['type']+'('+','.join(json.dumps(v) for v in attr['arguments'])+')]')
 (folder/'Version.cs').write_text('\n'.join(info)+'\n')
 refs=([Path('/clang64/lib/dotnet/reference-packs/legacy-ns13-contracts-bootstrap/contracts/System.Runtime/4.0.0.0/System.Runtime.dll')] if tfm=='netstandard1.0' else sorted(Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll')))
 selected=source/'src/System.Runtime.CompilerServices.Unsafe/ref/System.Runtime.CompilerServices.Unsafe.cs'
 args=['/nostdlib+','/target:library','/unsafe+','/langversion:7.3','/warnaserror+','/nowarn:1701,1702','/publicsign+','/keyfile:"'+native(key)+'"','/win32res:"'+native(resource/'version.res')+'"','/out:"'+native(folder/'System.Runtime.CompilerServices.Unsafe.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(selected)+'"','"'+native(folder/'Version.cs')+'"']
 rsp=folder/'compile.rsp';rsp.write_text('\n'.join(args)+'\n')
 tool('reference-'+tfm,['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(rsp)])
 references[tfm]=dict(original_source_sha256=sha(selected),exact_reference_DLL_sha256={p.name:sha(p) for p in refs},output_sha256=sha(folder/'System.Runtime.CompilerServices.Unsafe.dll'))
(out/'results.json').write_text(json.dumps(dict(source_commit=commit,source_archive_sha256=sha(archive),original_file_sha256=hashes,production_source_changes=0,assembly_version='4.0.4.1',package_version='4.5.2',assembler='/clang64/bin/ilasm10.exe',assembler_sha256=sha(assembler),profiles=profiles,reference_profiles=references,native_VERSIONINFO=version,native_version_RC_sha256=sha(resource/'version.rc'),commands=commands,source_ILAsm10_bootstrap=True,original_buildtools_host_replayed=False,original_native_VERSIONINFO_resource_reconstructed=True,formal_package_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
