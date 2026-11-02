"""Verify source selection against pinned archives and actual tested package inputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();source=root/'r';out=root/'corelib10-1/corelib';here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=json.loads((out/'source-inputs.json').read_text());gen=json.loads((root/'corelib10-1/generator/source-inputs.json').read_text())
assert selection['production_cs_changes']==gen['production_source_changes']==0
assert len(selection['original_cs'])==1932 and len(gen['original_cs'])==9
expected={**selection['original_cs'],**gen['original_cs']}
for name,digest in expected.items():assert sha(source/name)==digest,name
for name in ['src/coreclr/System.Private.CoreLib/System.Private.CoreLib.csproj',gen['original_project'],'src/tools/illink/src/ILLink.Tasks/CreateRuntimeRootDescriptorFile.cs','src/libraries/System.Private.CoreLib/src/Resources/Strings.resx','src/coreclr/vm/namespace.h','src/coreclr/vm/corelib.h','src/coreclr/inc/cortypeinfo.h','src/coreclr/vm/rexcep.h','eng/illink.targets']:
 expected[name]=sha(source/name)
rewrite=json.loads((root/'corelib10-1/rewrite/rewrite-results.json').read_text());expected.update(rewrite['library_build_xml_sha256'])
assert rewrite['original_library_policy'] and rewrite['rewrite_exit_code']==0 and not rewrite['fcall_helper_used']
# Replay original archive membership and hashes, including project/resource/root inputs.
found={}
with tarfile.open(root/'runtime-v10.0.5.tar.gz') as archive:
 for member in archive:
  name=member.name.partition('/')[2]
  if name in expected:
   assert member.isfile(),name
   found[name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
assert found==expected,'Original archive compiler/root/policy inputs differ'
for filename,group in [('port-source-inputs.json','changed_files'),('corerun-source-inputs.json','files')]:
 record=json.loads((here/filename).read_text())
 for name,item in record[group].items():assert sha(source/name)==item['ported_sha256'],name
response=(out/'corelib.rsp').read_text();assert '/nostdlib+' in response and '/reference:' not in response
native_root=subprocess.check_output(['cygpath','-am',str(root)],text=True).strip()
for name in selection['original_cs']:assert '"'+native_root+'/r/'+name+'"' in response.replace('\\','/'),name
log=(out/'compile.log').read_text();assert all(t not in log for t in ['error CS','warning CS8784','warning CS8785'])
generated=out/'obj/generated';required=['Microsoft.Interop.LibraryImportGenerator/Microsoft.Interop.LibraryImportGenerator/LibraryImports.g.cs','System.Private.CoreLib.Generators/Generators.ProductVersionInfoGenerator/ProductVersionInfo.g.cs','System.Private.CoreLib.Generators/Generators.NativeRuntimeEventSourceGenerator/NativeRuntimeEventSource.g.cs']
for name in required:assert (generated/name).is_file() and (generated/name).stat().st_size>0,name
assert 'new Version(10, 0, 5)' in (generated/required[1]).read_text()
roots=[e.get('fullname') for e in E.parse(out/'obj/ILLink.Descriptors.xml').iter('type')];assert {'System.Object','System.__Canon'}<=set(roots)
metadata={n:json.loads((out/('metadata-'+n+'.json')).read_text()) for n in ['raw','linked']}
assert metadata['linked']['internal_calls_with_body']==0
managed=json.loads((root/'managed-check/results.json').read_text());assert managed['all_four_managed_cases_passed']
for name,digest in managed['native_dependency_sha256'].items():assert sha(Path('/clang64/lib/dotnet-bootstrap10/coreclr/10.0.5')/name)==digest
assert managed['tested_files_sha256']['System.Private.CoreLib.dll']==rewrite['linked_corelib_sha256']
assert managed['tested_files_sha256']['corerun.exe']==sha(root/'coreclr-build/hosts/corerun/corerun.exe')
selftest=(root/'corerun-selftest.log').read_text();assert selftest.strip(),selftest
# Only the native host is built here; runtime DLLs must come from the installed dependency.
assert not list((root/'coreclr-build').rglob('coreclr.dll'))
record=dict(source_runtime_version='10.0.5',original_corelib_cs=1932,original_corelib_generator_cs=9,original_generator_framework='netstandard2.0',original_generator_roslyn='4.14.0',archive_verified_inputs=len(found),production_cs_changes=0,all_original_source_hashes_match=True,original_runtime_root_types=len(roots),raw_metadata=metadata['raw'],linked_metadata=metadata['linked'],generated_sources_sha256={p.relative_to(generated).as_posix():sha(p) for p in generated.rglob('*.cs')},raw_compile_warning_lines=log.count(': warning '),native_runtime_from_installed_dependency=True,native_host_selftests_completed=True,full_original_illink_rewrite_completed=True,all_four_managed_cases_passed=True,full_runtime10_built=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'source-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS pinned original CoreLib/generator sources, no-reference compile, ILLink policy, metadata and installed-native managed execution')
