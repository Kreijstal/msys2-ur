"""Evaluate original SDK Roslyn compiler projects for the original VMR NET10 profile."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

source=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
toolset=sys.argv[3:]==['--toolset']
assert not sys.argv[3:] or toolset,'usage: prepare-net10-projects.py SOURCE OUTPUT [--toolset]'
assert not out.exists();out.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
projects={
 'Microsoft.CodeAnalysis':'src/Compilers/Core/Portable/Microsoft.CodeAnalysis.csproj',
 'Microsoft.CodeAnalysis.CSharp':'src/Compilers/CSharp/Portable/Microsoft.CodeAnalysis.CSharp.csproj',
 'csc':'src/Compilers/CSharp/csc/AnyCpu/csc.csproj',
}
if toolset:
 projects.update({
  'Microsoft.CodeAnalysis.VisualBasic':'src/Compilers/VisualBasic/Portable/Microsoft.CodeAnalysis.VisualBasic.vbproj',
  'vbc':'src/Compilers/VisualBasic/vbc/AnyCpu/vbc.csproj',
  'VBCSCompiler':'src/Compilers/Server/VBCSCompiler/AnyCpu/VBCSCompiler.csproj',
 })
wrappers={};inputs={}
for name,relative in projects.items():
 original=source/relative;folder=out/name;folder.mkdir()
 tree=E.parse(original);tree.getroot().attrib.pop('Sdk',None)
 for item in tree.iter():
  if item.tag not in {'Compile','Import','ProjectReference','EmbeddedResource'}:continue
  for attr in ['Include','Remove','Update','Project']:
   if item.tag=='Import' and attr!='Project':continue
   value=item.get(attr)
   if not value:continue
   value=value.replace('\\','/').replace('$(MSBuildThisFileDirectory)',native(original.parent)+'/')
   if not any(token in value for token in ['$(', '@(', '%(']) and not value.startswith('/') and not (len(value)>1 and value[1]==':'):
    value=native(original.parent/value)
   item.set(attr,value)
 E.indent(tree);tree.write(folder/'upstream.proj',encoding='utf-8',xml_declaration=True)
 p=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(p,'PropertyGroup')
 values=dict(Configuration='Release',TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',
  TargetFrameworkVersion='v10.0',NetCurrent='net10.0',NetPrevious='net9.0',NetMinimum='net8.0',
  DotNetBuildSourceOnly='true',DotNetBuildFromVMR='true',ImportDirectoryBuildProps='false',
  ImportDirectoryBuildTargets='false',EnableDefaultItems='false',EnableDefaultCompileItems='false',
  RepositoryEngineeringDir=native(source/'eng')+'/',RepoRoot=native(source)+'/',
  RootNamespace=name,DefineConstants='TRACE;RELEASE;NET;NETCOREAPP;NET10_0;DOTNET_BUILD_FROM_SOURCE',
  DefaultLanguageSourceExtension='.vb' if original.suffix=='.vbproj' else '.cs')
 for k,v in values.items():E.SubElement(pg,k).text=v
 for n in ['eng/Versions.props','eng/Packages.props','eng/targets/TargetFrameworks.props']+(['eng/targets/Settings.props'] if toolset else []):
  E.SubElement(p,'Import',Project=native(source/n));inputs[n]=sha(source/n)
 if original.parent.name=='Portable':
  items=E.SubElement(p,'ItemGroup')
  E.SubElement(items,'Compile',Include=native(original.parent)+'/**/*'+values['DefaultLanguageSourceExtension'])
  E.SubElement(items,'EmbeddedResource',Include=native(original.parent)+'/**/*.resx')
 E.SubElement(p,'Import',Project='upstream.proj')
 E.indent(p);path=folder/original.name;E.ElementTree(p).write(path,encoding='utf-8',xml_declaration=True)
 wrappers[name]=native(path);inputs[relative]=sha(original)
(out/'wrappers.json').write_text(json.dumps(wrappers,indent=2)+'\n')
(out/'original-inputs.json').write_text(json.dumps(dict(source_root=str(source),
 original_inputs_sha256=inputs,requested_profile='DotNetBuildSourceOnly=true;DotNetBuildFromVMR=true;NetCurrent=net10.0',
 original_sources_written=False,compiled=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original Common/CSharp/csc NET10 VMR evaluation wrappers prepared')
