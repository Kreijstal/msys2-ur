"""Verify every original compiler/task/policy input in a completed framework build."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,xml.etree.ElementTree as E
root=Path(sys.argv[1]).resolve();plan=Path(sys.argv[2]).resolve();source=root/'r'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((plan/'build-status.json').read_text());projects=json.loads((plan/'projects.json').read_text());evaluation=json.loads((plan/'evaluated.json').read_text())
assert set(status)<=set(projects) and len(projects)==190
native_source=next(iter(evaluation.values()))['properties']['BootstrapOriginalProjectDirectory'].replace('\\','/').split('/r/')[0]+'/r/'
native_plan=subprocess.check_output(['cygpath','-am',str(plan)],text=True).strip().replace('\\','/')
original={};generated={};references={};policy_inputs={};installed_tools={}
def source_path(value):
 # Build records use MSYS paths for source inputs, while evaluation records retain native paths.
 value=value.replace('\\','/')
 p=Path(value)
 if p.is_relative_to(source):return Path(os.path.normpath(p)).relative_to(source).as_posix()
 value=value.replace('\\','/')
 if value.lower().startswith(native_source.lower()):return os.path.normpath(value[len(native_source):]).replace('\\','/')
 return None
for name,entry in status.items():
 for filename,digest in entry.get('generation_inputs_sha256',{}).items():
  rel=source_path(filename);assert rel is not None and sha(source/rel)==digest,(name,filename)
  original[rel]=digest
 for filename,digest in entry['compiled_sources_sha256'].items():
  rel=source_path(filename)
  if rel is not None:assert sha(source/rel)==digest,(name,rel);original[rel]=digest
  else:
   path=Path(filename);assert path.is_relative_to(plan) and sha(path)==digest,(name,path);generated[str(path.relative_to(plan))]=digest
 for filename,digest in entry['reference_sha256'].items():assert sha(Path(filename))==digest,(name,filename);references[filename]=digest
 product=plan/('stubs' if entry['kind']=='stub' else 'lib')/(name.removeprefix('stub:')+'.dll');assert sha(product)==entry['output_sha256'],name
 actual=json.loads((plan/'steps'/name.replace(':','-')/'actual-inputs.json').read_text())
 # Record the exact installed generators, compiler and facade-task closure.
 # Their separate source package audits establish provenance, not this archive.
 import re
 for value in re.findall(r'^/analyzer:"([^"]+)"', (plan/'steps'/name.replace(':','-')/'compile.rsp').read_text(),re.M):
  file=Path(subprocess.check_output(['cygpath','-u',value],text=True).strip())
  installed_tools[str(file)]=sha(file)
 for item in actual['Items']['EmbeddedResource']:
  rel=source_path(item['FullPath'])
  if rel is not None:original[rel]=sha(source/rel);policy_inputs[rel]=original[rel]
  else:
   value=item['FullPath'].replace('\\','/')
   assert value.lower().startswith(native_plan.lower()+'/'),(name,item)
   file=plan/value[len(native_plan)+1:];assert file.is_file(),(name,item)
   generated[str(file.relative_to(plan))]=sha(file)
 for kind in ['AdditionalFiles','AsnXml','ILLinkDescriptorsXmls','ILLinkSubstitutionsXmls','ILLinkLinkAttributesXmls','ILLinkDescriptorsLibraryBuildXml','ILLinkSuppressionsLibraryBuildXml']:
  for item in evaluation[name]['items'][kind]:
   value=item['full_path'] or item['identity']
   if not value.startswith('/') and not (len(value)>1 and value[1]==':'):
    value=str((source/projects[name]['project']).parent/value)
   rel=source_path(value)
   if rel is not None:original[rel]=sha(source/rel);policy_inputs[rel]=original[rel]
   else:
    value=value.replace('\\','/')
    assert value.lower().startswith(native_plan.lower()+'/'),(name,kind,item)
    file=plan/value[len(native_plan)+1:];assert file.is_file(),(name,kind,item)
    generated[str(file.relative_to(plan))]=sha(file)
for name,digest in json.loads((plan/'source-projects.json').read_text()).items():assert sha(source/name)==digest,name;original[name]=digest
for name in projects.values():original[name['project']]=sha(source/name['project'])
for file in [source/'src/tools/illink/src/ILLink.Tasks'/name for name in ['CombineLinkerXmlFiles.cs','ComputeManagedAssemblies.cs','CreateRuntimeRootDescriptorFile.cs','LinkTask.cs','Utils.cs']]:original[file.relative_to(source).as_posix()]=sha(file)
archive=root/'runtime-v10.0.5.tar.gz';assert sha(archive)=='1692acae5e3adfd625452fbc9db4fd4e982c10e38189358ae245c74dd5514d7a';found={}
with tarfile.open(archive) as tar:
 for member in tar:
  name=member.name.partition('/')[2]
  if name in original:found[name]=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
differences={name:dict(expected=digest,archive=found.get(name)) for name,digest in original.items() if found.get(name)!=digest}
if differences:(plan/'compiler-source-audit-failures.json').write_text(json.dumps(differences,indent=2)+'\n')
assert not differences,('Pinned original compiler/project/target/task source inputs differ',list(differences.items())[:12])
arcade=root/'arcade-runtime10-4bf37ce6.tar.gz'
assert sha(arcade)=='82f5f6dd63c0dcf3c0fc49b282207db5d889d9cc0939589d43b16c7fcfdf7d66'
arcade_inputs={}
files={
 'src/Microsoft.DotNet.Arcade.Sdk/src/GenerateResxSource.cs':plan/'tools/GenerateResxSource.cs',
 'src/Microsoft.DotNet.Arcade.Sdk/tools/GenerateResxSource.targets':plan/'tools/GenerateResxSource.targets',
 'src/Microsoft.DotNet.Arcade.Sdk/tools/StrongName.props':plan/'tools/StrongName.props',
}
for filename in ['GenerateFileFromTemplate.cs','MSBuildListSplitter.cs']:
 files['src/Microsoft.DotNet.Build.Tasks.Templating/src/'+filename]=plan/'tools/Templating'/filename
version_project=E.parse(root/'version-build/Build.csproj')
version_file=version_project.find('.//Compile').get('Include')
# This task lives in the frozen workflow, outside the runtime source tree.
version_bytes=None
with tarfile.open(arcade) as tar:
 for member in tar:
  name=member.name.partition('/')[2]
  if name in files:
   digest=hashlib.sha256(tar.extractfile(member).read()).hexdigest()
   assert sha(files[name])==digest,name;arcade_inputs[name]=digest
  if name=='src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs':
   version_bytes=tar.extractfile(member).read()
assert set(arcade_inputs)==set(files)
assert hashlib.sha256(version_bytes).hexdigest()=='7740ecad63add6b83cdca96b60ebb9c44ff4ece302833a8e5d2a9f43307cf0b7'
version_path=Path(subprocess.check_output(['cygpath','-u',version_file],text=True).strip())
assert version_path.read_bytes()==version_bytes
arcade_inputs['src/Microsoft.DotNet.Arcade.Sdk/src/CalculateAssemblyAndFileVersions.cs']=sha(version_path)
for folder in [Path('/clang64/lib/dotnet/tool-packs/genfacades-10.0.5-bootstrap'),Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap'),Path('/clang64/lib/dotnet/compiler-packs/roslyn-vb-4.9.2')]:
 assert folder.is_dir(),folder
 for file in folder.rglob('*'):
  if file.is_file():installed_tools[str(file)]=sha(file)
record=dict(completed_projects=len(status),total_planned_projects=190,shipping_implementation_outputs=sum(v['kind']!='stub' for v in status.values()),private_seed_outputs=sum(v['kind']=='stub' for v in status.values()),original_runtime_archive_inputs_verified=len(original),original_resource_additional_and_policy_inputs_verified=len(policy_inputs),original_arcade_task_target_and_key_inputs_verified=arcade_inputs,generated_input_hashes_verified=len(generated),actual_reference_hashes_verified=len(references),installed_source_tool_package_inputs_sha256=installed_tools,installed_tool_source_provenance_audited_by_separate_dependency_packages=True,all_original_source_hashes_match=True,all_recorded_reference_and_output_hashes_match=True,original_sources=original,generated_sources=generated,full_managed_framework_compilation_complete=len(status)==190,full_framework_execution_complete=False,full_dependency_goal_complete=False)
(plan/'compiler-source-audit.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS original archive compiler/project/task inputs and all recorded generated/reference/output hashes:',len(status),'of190 planned projects')
