"""Compile complete generated Framework4.6 reference contracts, never publisher DLLs."""
from pathlib import Path
import functools,hashlib,json,re,subprocess,sys,xml.etree.ElementTree as E
source,out,compiler=(Path(s).resolve() for s in sys.argv[1:]);assert not out.exists();out.mkdir()
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
key=bytes.fromhex('00000000000000000400000000000000');assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b77a5c561934e089';(out/'ECMA.public.snk').write_bytes(key)
here=Path(__file__).parent
policy=E.parse(here/'inputs/reference-build-policy.props')
no_warn=sorted(set(re.findall(r'CS([0-9]{4})',';'.join(e.text or '' for e in policy.findall('.//NoWarn')))))
assert {'0618','0809','0108','0169','0649'}<=set(no_warn)
records={};commands=[]
for name in ['mscorlib','System.Numerics']:
 original=source/(name+'.cs');assert original.is_file();output=out/(name+'.dll')
 text=original.read_text(encoding='utf-8-sig')
 # Signing instructions in the original metadata name an unavailable private
 # key. The reconstructed reference contract uses the original public key.
 text=re.sub(r'^\[assembly: (?:System\.Reflection\.)?(?:AssemblyKeyFile|AssemblyDelaySign|AssemblySignatureKey)\([^\n]*\n','',text,flags=re.M)
 usings=['System','System.Reflection','System.Resources','System.Runtime.CompilerServices','System.Runtime.InteropServices','System.Diagnostics']
 text=re.sub(r'^(\s*public )delegate ([^\n]*\*[^\n]*);',r'\1unsafe delegate \2;',text,flags=re.M)
 if name=='mscorlib':
  text,count=re.subn(r'^(\s*)(public Char this\[)',r'\1[System.Runtime.CompilerServices.IndexerName("Chars")]\n\1\2',text,flags=re.M);assert count==2,count
 native_policy=json.loads((here/'inputs/public-native-method-policy.json').read_text()) if name=='mscorlib' else {}
 for full,entry in native_policy.items():
  method=full.split('::')[1].split('(')[0]
  assert entry['attributes']==256 and entry['preserve_sig']
  pattern=r'^(\s*)(public static extern [^\n]*\b'+re.escape(method)+r'\([^\n]*\)) \{[^\n]*\}'
  def pinvoke(match):
   declaration=match[2]
   if 'System.Runtime.InteropServices.Marshal::' in full:
    attrs='[In, '+('Out, ' if method.startswith('Write') else '')+'MarshalAs(UnmanagedType.AsAny)] '
    declaration=declaration.replace('Object ptr',attrs+'Object ptr')
   return match[1]+'[DllImport('+json.dumps(entry['module'])+', EntryPoint='+json.dumps(entry['entry'])+')]\n'+match[1]+declaration+';'
  text,count=re.subn(pattern,pinvoke,text,flags=re.M);assert count==1,(full,count)
 selected=out/(name+'.cs');selected.write_text('\n'.join('using '+ns+';' for ns in usings)+'\n'+text)
 flags=['/nostdlib+','/target:library','/refonly','/unsafe+','/langversion:latest','/nullable:disable','/runtimemetadataversion:'+policy.findtext('.//RuntimeMetadataVersion'),'/warnaserror+','/nowarn:'+','.join(['1701','1702']+no_warn),'/publicsign+','/keyfile:"'+native(out/'ECMA.public.snk')+'"','/out:"'+native(output)+'"']
 if name!='mscorlib':flags+=['/reference:"'+native(out/'mscorlib.dll')+'"']
 flags+=['"'+native(selected)+'"']
 if name=='mscorlib':
  interfaces=source/'InternalInterfaces.cs';assert interfaces.is_file()
  # Imports are needed by the generated interface attribute spellings too.
  interface_source=out/'InternalInterfaces.cs';interface_source.write_text('\n'.join('using '+ns+';' for ns in usings)+'\n'+interfaces.read_text())
  flags+=['"'+native(interface_source)+'"']
 rsp=out/(name+'.rsp');rsp.write_text('\n'.join(flags)+'\n');cmd=['/clang64/lib/dotnet/dotnet.exe',native(compiler/'csc.dll'),'-noconfig','@'+native(rsp)]
 with (out/(name+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 commands.append(dict(command=cmd,exit_code=r.returncode));assert r.returncode==0,(name,(out/(name+'.log')).read_text(errors='replace')[-22000:])
 records[name]=dict(original_generated_source_sha256=sha(original),source_CSharp_sha256=sha(selected),output_sha256=sha(output));print('PASS complete source reference contract compiled',name,flush=True)
(out/'results.json').write_text(json.dumps(dict(contracts=records,commands=commands,published_DLL_executed_or_used_as_compiler_reference=False,generated_CSharp_contract_port=True,upstream_source_reference_contract_warning_policy=no_warn,original_public_API_equality_not_yet_verified=True,full_dependency_goal_complete=False),indent=2)+'\n')
