"""Audit original Tasks16 compile selection, original SDK policy and source dependency assets."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E,zipfile
root=Path(sys.argv[1]).resolve();source=root/'source';record=json.loads((root/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,digest in record['original_file_sha256'].items():assert sha(source/name)==digest,name
policy_file=source/'arcade'/record['Arcade_policy_original_file'];assert sha(policy_file)==record['Arcade_policy_original_file_sha256']
for name,projection in record['original_Windows_resource_CRLF_projections'].items():
 raw=(source/name).read_bytes();generated=root/projection['generated_path'];assert sha(source/name)==projection['original_sha256']
 assert generated.read_bytes()==raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
 assert sha(generated)==projection['Windows_CRLF_projection_sha256']
assert record['original_Arcade_CSharp_NoWarn']==['1701','1702','1705','1591']
posix=lambda p:Path(subprocess.check_output(['cygpath','-au',p],text=True).strip()).resolve()
def enabled(condition):
 if not condition:return True
 condition=condition.replace(' ','')
 values={"$(TargetFrameworkIdentifier)=='.NETFramework'":False,"'$(TargetFrameworkIdentifier)'=='.NETFramework'":False,"'$(TargetFrameworkIdentifier)'!='.NETFramework'":True,"'$(MonoBuild)'=='true'":False,"'$(MonoBuild)'!='true'":True}
 assert condition in values,condition
 return values[condition]
original=source/'src/Tasks/Microsoft.Build.Tasks.csproj';expected=set()
for group in E.parse(original).getroot():
 if group.tag!='ItemGroup' or not enabled(group.get('Condition')):continue
 for item in group:
  if item.tag=='Compile' and enabled(item.get('Condition')):
   assert item.get('Include') and not item.get('Remove')
   expected.update(p.resolve() for p in original.parent.glob(item.get('Include').replace('\\','/')))
for name in ['FileSystemSources.proj','DebuggingSources.proj']:
 path=source/'src/Shared'/name
 for item in E.parse(path).findall('.//Compile'):
  value=item.get('Include').replace('$(MSBuildThisFileDirectory)','').replace('\\','/');expected.update(p.resolve() for p in path.parent.glob(value))
obj=root/'obj/Release/netstandard2.0';actual={posix(p) for p in (obj/'Compile.txt').read_text().splitlines() if p}
assert {p for p in actual if p.is_relative_to(source)}==expected,(actual^expected)
extras=actual-expected;assert len(extras)==2 and root/'BootstrapVersion.cs' in extras
policy=(obj/'policy.txt').read_text().replace('\n',';').strip(';').split('|');assert policy[0]=='netstandard2.0' and policy[-2:]==['7.3','true']
assert {'MICROSOFT_BUILD_TASKS','STANDALONEBUILD','RUNTIME_TYPE_NETCORE','FEATURE_RUNTIMEINFORMATION','FEATURE_PROCESSSTARTINFO_ENVIRONMENT','USE_MSBUILD_DLL_EXTN','WORKAROUND_COREFX_19110'}.issubset(set(policy[1].split(';')))
assert not set(policy[1].split(';'))&{'DEBUG','THISASSEMBLY','FEATURE_APPDOMAIN','FEATURE_XAML_TYPES'}
expected_warnings=[]
for index,file in enumerate([source/'Directory.Build.props',source/'src/Directory.Build.props']):
 for node in E.parse(file).iter():
  if node.tag.rsplit('}',1)[-1]=='NoWarn':expected_warnings.extend(x for x in node.text.replace('$(NoWarn)','').split(';') if x)
 if index==0:expected_warnings.extend(record['original_Arcade_CSharp_NoWarn'])
assert policy[2].split(';')==expected_warnings,(policy[2],expected_warnings)
assert not (obj/'Analyzer.txt').read_text().strip()
assets=json.loads((root/'obj/project.assets.json').read_text());assert not assets.get('logs');cache=posix(next(iter(assets['packageFolders'])))
versions=dict(record['exact_original_dependency_versions']);versions.update({'System.Text.Encoding.CodePages':'4.0.1','NETStandard.Library':'2.0.3','Microsoft.NETCore.Platforms':'1.1.0'})
assert set(assets['libraries'])=={n+'/'+v for n,v in versions.items()},assets['libraries'].keys()
reference_paths={posix(p) for p in (obj/'ReferencePath.txt').read_text().splitlines() if p};verified=set();dependency_archives={}
for ident,item in assets['libraries'].items():
 name=ident.lower().replace('/','.')+'.nupkg';archive=cache/item['path']/name;upstream=Path('/clang64/lib/dotnet/library-packs')/name;assert archive.read_bytes()==upstream.read_bytes();dependency_archives[ident]=sha(archive)
 with zipfile.ZipFile(archive) as z:
  for member in z.namelist():
   path=cache/item['path']/member
   if member.endswith('.dll') and path in reference_paths:assert path.read_bytes()==z.read(member);verified.add(path)
assert verified==reference_paths
package=root/'feed/Microsoft.Build.Tasks.Core.16.0.461.nupkg'
with zipfile.ZipFile(package) as z:
 metadata=E.fromstring(z.read('Microsoft.Build.Tasks.Core.nuspec')).find('{*}metadata');assert metadata.findtext('{*}id')=='Microsoft.Build.Tasks.Core' and metadata.findtext('{*}version')=='16.0.461'
 assert metadata.find('{*}repository').get('commit')==record['source_commit']
 deps={d.get('id'):d.get('version') for d in metadata.findall('.//{*}dependency')};assert deps=={n:'['+v+']' for n,v in record['exact_original_dependency_versions'].items()},deps
 assert [n for n in z.namelist() if n.endswith('.dll')]==['lib/netstandard2.0/Microsoft.Build.Tasks.Core.dll']
 assert z.read('lib/netstandard2.0/Microsoft.Build.Tasks.Core.dll')==(root/'bin/Release/netstandard2.0/Microsoft.Build.Tasks.Core.dll').read_bytes()
 assert z.read('lib/netstandard2.0/Microsoft.Build.Tasks.Core.pdb')==(root/'bin/Release/netstandard2.0/Microsoft.Build.Tasks.Core.pdb').read_bytes()
 assert z.read('lib/netstandard2.0/Microsoft.Build.Tasks.Core.xml')==(root/'obj/Release/netstandard2.0/Microsoft.Build.Tasks.Core.xml').read_bytes()
 for license in ['LICENSE','THIRDPARTYNOTICES.txt']:assert z.read(license)==(source/license).read_bytes()
 members={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
resources={}
for path in original.parent.rglob('*.resx'):resources[str(path.relative_to(source))]={e.get('name'):e.findtext('value') for e in E.parse(path).findall('data')}
path=source/'src/Shared/Resources/Strings.shared.resx';resources[str(path.relative_to(source))]={e.get('name'):e.findtext('value') for e in E.parse(path).findall('data')}
report=dict(original_source_files_verified=len(record['original_file_sha256']),original_CSharp_inputs=len(expected),production_CSharp_changes=0,original_NS2_feature_guards=True,actual_compiler_policy=policy,original_Arcade_CSharp_NoWarn=record['original_Arcade_CSharp_NoWarn'],Arcade_policy_original_file_sha256=record['Arcade_policy_original_file_sha256'],original_Arcade_version_manifest_discrepancy_resolved=False,exact_original_dependency_versions=record['exact_original_dependency_versions'],original_NS2_references_pruned_to_BCL=record['original_NS2_references_pruned_to_BCL'],pruning_requires_exact_API_and_dependency_identity_checks=True,all_actual_reference_DLL_bytes_verified_against_source_archives=True,source_dependency_archive_sha256=dependency_archives,source_resource_strings=resources,original_Windows_resource_CRLF_projections=record['original_Windows_resource_CRLF_projections'],raw_original_resources_modified_in_place=False,package_sha256=sha(package),archive_members=members,NET472_profile_built=False,original_Arcade_Nerdbank_GenAPI_toolchain_replayed=False,full_dependency_goal_complete=False)
(root/'producer-audit.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS original Tasks16 source selection/SDK warning policy, exact reference archives and NS2 package;',len(expected),'original CSharp inputs')
