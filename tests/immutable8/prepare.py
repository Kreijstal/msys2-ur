"""Prepare the exact Immutable8.0.0 original NET8 project and shared source policy."""
from pathlib import Path
import copy,hashlib,json,sys,tarfile,xml.etree.ElementTree as E
archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent;native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tarfile.open(archive) as t:t.extractall(out/'snapshot',filter='data')
snapshot=out/'snapshot';source=snapshot/'runtime';libs=source/'src/libraries';manifest=json.loads((snapshot/'source-inputs.json').read_text())
assert manifest['source_commit']=='5535e31a712343a63f5d7d796cd874e563e5ac14'
for rel,meta in manifest['files'].items():assert sha(source/rel)==meta['sha256'],rel
projects={'System.Collections.Immutable':('System.Collections.Immutable/src/System.Collections.Immutable.csproj','net8.0')}
shared=E.Element('Project')
for item in E.parse(libs/'Directory.Build.targets').getroot():
 if item.tag in {'ItemGroup','Choose'} and any(s in E.tostring(item,encoding='unicode') for s in ['NullableAttributes.cs','ExceptionPolyfills.cs','PlatformAttributes.cs','System\\ObsoleteAttribute.cs','System\\Index.cs']):shared.append(copy.deepcopy(item))
E.ElementTree(shared).write(out/'original-shared-sources.targets',encoding='utf-8',xml_declaration=True)
wrappers={};policies={}
for name,(rel,tfm) in projects.items():
 original=libs/rel;folder=out/name;folder.mkdir();isgen=tfm=='netstandard2.0'
 def clone(path,dest):
  tree=E.parse(path);root=tree.getroot();root.attrib.pop('Sdk',None)
  for item in tree.iter():
   for attr,value in list(item.attrib.items()):
    value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(path.parent)+'/')
    if item.tag in {'Compile','EmbeddedResource','ProjectReference'} and attr in {'Include','Exclude','Remove','Update'}:
     parts=[]
     for part in value.split(';'):
      if part and not any(p in part for p in ['$(','@(','%(']) and not Path(part).is_absolute():part=native(path.parent/part)
      parts.append(part)
     value=';'.join(parts)
    if item.tag=='Import' and attr=='Project' and not any(s in value for s in ['$(','@(','%(']):
     imported=(path.parent/value).resolve();target=folder/imported.name;clone(imported,target);value=native(target)
    item.set(attr,value)
  tree.write(dest,encoding='utf-8',xml_declaration=True)
 clone(original,folder/'upstream.proj')
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 values=dict(Configuration='Release',TargetFramework=tfm,TargetFrameworkIdentifier='.NETStandard' if isgen else '.NETCoreApp',TargetFrameworkVersion='v2.0' if isgen else 'v8.0',NetCoreAppCurrent='net8.0',NetCoreAppPrevious='net7.0',NetCoreAppMinimum='net6.0',NetFrameworkMinimum='net462',NetCoreAppToolCurrent='net8.0',DotNetBuildSourceOnly='true',ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableDefaultCompileItems='false',EnableDefaultEmbeddedResourceItems='false',EnableNETAnalyzers='false',NuGetAudit='false',CommonPath=native(libs/'Common/src')+'/',LibrariesProjectRoot=native(libs)+'/',CoreLibSharedDir=native(libs/'System.Private.CoreLib/src')+'/',RepositoryEngineeringDir=native(source/'eng')+'/',DefaultLanguageSourceExtension='.cs',RootNamespace=name,AssemblyName=name,Nullable='enable',StrongNameKeyId='Microsoft',GenerateDocumentationFile='false' if isgen else 'true',TreatWarningsAsErrors='true',CLSCompliant='false' if isgen else 'true')
 for k,v in values.items():E.SubElement(pg,k).text=v
 E.SubElement(p,'Import',Project=native(source/'eng/Versions.props'))
 # Respect each original project's explicit default-item policy.
 if E.parse(original).findtext('.//EnableDefaultItems')=='true':
  ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(original.parent)+'/**/*.cs',Exclude=native(original.parent)+'/obj/**;'+native(original.parent)+'/bin/**')
 E.SubElement(p,'Import',Project=native(folder/'upstream.proj'));E.SubElement(p,'Import',Project=native(out/'original-shared-sources.targets'))
 resx=original.parent/'Resources/Strings.resx'
 if resx.exists():
  pg=E.SubElement(p,'PropertyGroup');E.SubElement(pg,'StringResourcesPath').text=native(resx);E.SubElement(p,'Import',Project=native(source/'eng/resources.targets'))
 # Retain the original libraries policy for nullable diagnostics on non-CoreApp profiles.
 for group in E.parse(libs/'Directory.Build.targets').getroot().findall('PropertyGroup'):
  for setting in group.findall('NoWarn'):
   if setting.get('Condition')=="'$(TargetFrameworkIdentifier)' != '.NETCoreApp'":E.SubElement(p,'PropertyGroup').append(copy.deepcopy(setting))
 wrapper=folder/(name+'.csproj');E.ElementTree(p).write(wrapper,encoding='utf-8',xml_declaration=True);wrappers[name]=dict(path=native(wrapper),framework=tfm)
 assert E.parse(libs/'System.Collections.Immutable/Directory.Build.props').findtext('.//StrongNameKeyId')=='Microsoft'
 policies[name]=dict(original_project=original.relative_to(source).as_posix(),original_project_sha256=sha(original),framework=tfm,key='Microsoft',generator=isgen)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n');(out/'source-inputs.json').write_text(json.dumps(dict(source_root=native(source),source_archive_sha256=sha(archive),source_manifest=manifest,original_projects=policies,original_production_source_changes=0,full_dependency_goal_complete=False),indent=2)+'\n');print('PASS prepared original Immutable8.0.0 NET8 profile')
