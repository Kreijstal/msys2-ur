"""Evaluate the original servicing Asn1 NET9 source profile without retargeting."""
from pathlib import Path
import copy,hashlib,json,sys,xml.etree.ElementTree as E
source,out=(Path(p).resolve() for p in sys.argv[1:]);assert not out.exists();out.mkdir(parents=True)
libs=source/'src/libraries';original=libs/'System.Formats.Asn1/src/System.Formats.Asn1.csproj'
# Native Python keeps Windows paths usable by the source-built MSBuild evaluator.
native=lambda p:Path(p).resolve().as_posix()
body=original.read_text(encoding='utf-8-sig').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
project=E.fromstring(body);project.attrib.pop('Sdk')
for item in project.iter():
 if item.tag in {'Compile','ProjectReference','EmbeddedResource'}:
  for attr in ['Include','Remove','Update']:
   value=item.get(attr,'').replace('\\','/')
   if value and '$(' not in value:item.set(attr,native(original.parent/value))
E.ElementTree(project).write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
shared=E.Element('Project')
for item in E.parse(libs/'Directory.Build.targets').getroot():
 if item.tag in {'ItemGroup','Choose'} and any(n in E.tostring(item,encoding='unicode') for n in ['NullableAttributes.cs','PlatformAttributes.cs','System\\ObsoleteAttribute.cs','System\\Index.cs']):shared.append(copy.deepcopy(item))
assert len(shared)==4
E.ElementTree(shared).write(out/'original-shared-sources.targets',encoding='utf-8',xml_declaration=True)
wrapper=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(wrapper,'PropertyGroup')
for k,v in dict(Configuration='Release',TargetFramework='net9.0',TargetFrameworkIdentifier='.NETCoreApp',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',NetCoreAppCurrent='net9.0',NetCoreAppPrevious='net8.0',NetCoreAppMinimum='net8.0',NetFrameworkMinimum='net462',TargetOS='windows',TargetsWindows='true',TargetArchitecture='x64',CommonPath=native(libs/'Common/src')+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/',LibrariesProjectRoot=native(libs)+'/',IsSourceProject='true').items():E.SubElement(pg,k).text=v
E.SubElement(wrapper,'Import',Project='upstream.proj');E.SubElement(wrapper,'Import',Project='original-shared-sources.targets')
E.ElementTree(wrapper).write(out/'Evaluate.csproj',encoding='utf-8',xml_declaration=True)
(out/'wrappers.json').write_text(json.dumps({'System.Formats.Asn1':native(out/'Evaluate.csproj')},indent=2)+'\n',encoding='utf-8')
(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_commit='fa7cdded37981a97cec9a3e233c4a6af58a91c57',original_project_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),original_shared_policy_sha256=hashlib.sha256((libs/'Directory.Build.targets').read_bytes()).hexdigest(),original_target='net9.0',original_production_source_changes=0,formal_package_built=False,full_dependency_goal_complete=False),indent=2)+'\n',encoding='utf-8')
print('Prepared original NET9 Asn1 project model')
