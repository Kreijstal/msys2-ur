"""Audit unchanged reference source selections and exact selected dependency graph."""
from pathlib import Path
import functools,hashlib,json,re,subprocess,sys,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();facade=Path(sys.argv[2]).resolve();here=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record=json.loads((root/'results.json').read_text());fr=json.loads((facade/'results.json').read_text());baseline=json.loads((here/'inputs/netcore20-published-metadata.json').read_text())
assert record['source_commit']=='8321c729934c0f8be754953439b88e6e1c120c24' and record['original_CSharp_changes']==0 and record['reference_only']
assert set(record['libraries'])==set(baseline) and all(c['exit_code']==0 for c in record['commands']+fr['commands'])
for n,h in record['original_file_sha256'].items():assert sha(root/'source'/n)==h
native=functools.lru_cache(None)(lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip());unique=set()
for file,item in record['libraries'].items():
 name=file.removesuffix('.dll');project=root/'source/src'/name/'ref'/(name+'.csproj');tree=E.parse(project);selected=[(project.parent/e.get('Include').replace('\\','/')).resolve() for e in tree.findall('.//{*}Compile')];unique.update(selected)
 assert item['original_CSharp_inputs']=={str(p.relative_to(root/'source')):sha(p) for p in selected}
 refs=[root/'ref'/(r.split(', Version=')[0]+'.dll') for r in baseline[file]['references']];assert item['reference_sha256']=={p.name:sha(p) for p in refs}
 warnings=['1701','1702']
 for node in E.parse(root/'source/dir.props').findall('.//{*}PropertyGroup'):
  if node.get('Condition')=="'$(IsReferenceAssembly)' == 'true'":
   for w in node.findall('{*}NoWarn'):warnings.extend(x for x in re.split('[;,]',w.text.replace('$(NoWarn)','')) if x)
 for w in tree.findall('.//{*}NoWarn'):warnings.extend(x for x in re.split('[;,]',w.text.replace('$(NoWarn)','')) if x)
 assert item['original_NoWarn']==warnings
 actual=(root/'build'/name/'compile.rsp').read_text().splitlines();assert '/nostdlib+' in actual and '/refonly' in actual and '/warnaserror+' in actual and '/nowarn:'+','.join(warnings) in actual
 assert {s for s in actual if s.startswith('/reference:')}=={'/reference:"'+native(p)+'"' for p in refs}
 assert {s for s in actual if s.startswith('"')}=={'"'+native(p)+'"' for p in selected+[root/'build'/name/'Version.cs']}
 assert sha(root/'ref'/file)==item['DLL_sha256']
assert len(list((root/'ref').glob('*.dll')))==10 and sha(root/'ref/netstandard.dll')==fr['facade_sha256']
assert fr['source_helper_sha256']==sha(here/'inputs/FacadePort.cs') and fr['declarative_metadata_sha256']==sha(here/'inputs/netstandard20-forwarders.json')
assert fr['original_forwarders']==2417 and fr['original_reference_scopes']==86 and not fr['published_DLL_executed_or_used_as_compiler_reference'] and not fr['published_implementation_bodies_copied']
result=dict(original_source_files_verified=len(record['original_file_sha256']),unique_original_CSharp_inputs=len(unique),original_CSharp_changes=0,original_compile_selections_and_source_dependency_reference_bytes_verified=True,original_reference_warning_policy_preserved=True,source_contracts=9,original_API_entries=sum(len(v['api']) for v in baseline.values()),facade_original_forwarders=2417,facade_original_reference_scopes=86,facade_source_metadata_port=True,reference_DLL_sha256={p.name:sha(p) for p in sorted((root/'ref').glob('*.dll'))},original_buildtools_host_replayed=False,complete_NETCore2_targeting_pack_registered=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
