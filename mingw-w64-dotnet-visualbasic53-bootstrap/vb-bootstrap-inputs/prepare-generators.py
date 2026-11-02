"""Prepare only original SDK5.3 VB generators on the source NET8 bootstrap host."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys
import xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
common=Path(os.path.commonpath([source,out]))
base=subprocess.check_output(['cygpath','-am',str(common)],text=True).strip() if shutil.which('cygpath') else str(common)
def native(p):return base.rstrip('/')+'/'+Path(p).resolve().relative_to(common).as_posix()
settings=E.parse(source/'eng/targets/Settings.props')
def key_value(name):
 value=next(e.text for e in settings.iter(name));seen={name}
 while re.fullmatch(r'\$\((\w+)\)',value):
  name=value[2:-1];assert name not in seen;seen.add(name);value=next(e.text for e in settings.iter(name))
 assert re.fullmatch('[0-9a-fA-F]+',value);return value
key=bytes.fromhex(key_value('MicrosoftSharedPublicKey'))
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Roslyn.public.snk').write_bytes(key)
removed=[]
# Native directory enumeration avoids tens of thousands of MSYS stat calls.
scan="import os,json,sys; print(json.dumps([os.path.join(d,f) for d,_,fs in os.walk(sys.argv[1]) for f in fs if os.path.splitext(f)[1].lower() in {'.dll','.exe','.pdb','.nupkg','.resources','.res','.obj','.lib'}]))"
binaries=json.loads(subprocess.check_output(['/clang64/bin/python.exe','-c',scan,native(source)],text=True))
assert not binaries,('Source must already be binary-clean',binaries)
(out/'removed-binaries.json').write_text(json.dumps(removed,indent=2)+'\n')
manifest={};localizations=[]
def project(name,vb=True,executable=False):
 folder=out/name;folder.mkdir();p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
 values=dict(TargetFramework='net8.0',AssemblyName=name,OutputType='Exe' if executable else 'Library',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',GenerateDocumentationFile='false',Version='5.3.0-2.26113.113',AssemblyVersion='5.3.0.0',FileVersion='5.3.0.0',InformationalVersion='5.3.0-2.26113.113+2333221c0564852ee5ceac9c622a0b14e864d76e',IncludeSourceRevisionInInformationalVersion='false')
 if vb:values.update(RootNamespace='',LangVersion='latest',VBRuntime='Embed',MyType='Empty',OptionExplicit='On',OptionInfer='On',OptionCompare='Binary',OptionStrict='On',RemoveIntegerChecks='true',NoWarn='40057;42014')
 else:values.update(LangVersion='12.0',Nullable='enable')
 for k,v in values.items():E.SubElement(props,k).text=v
 items=E.SubElement(p,'ItemGroup')
 if vb:
  for name in ['Microsoft.VisualBasic','System','System.Collections','System.Collections.Generic','System.Diagnostics','System.Linq']:E.SubElement(items,'Import',Include=name)
  # Preserve upstream eng/targets/Imports.targets: WorkAroundDotnetSdk10591.
  target=E.SubElement(p,'Target',Name='RemoveEmbeddedVbRuntimeReferences',AfterTargets='ResolveTargetingPackAssets')
  E.SubElement(E.SubElement(target,'ItemGroup'),'Reference',Remove='@(Reference)',Condition="'%(FileName)' == 'Microsoft.VisualBasic' or '%(FileName)' == 'Microsoft.VisualBasic.Core'")
 return folder,p,props,items
def save(folder,p,vb=True):
 target=E.SubElement(p,'Target',Name='CaptureActualCompilerInputs',BeforeTargets='CoreCompile')
 for kind in ['Compile','ReferencePath','Analyzer']:
  E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true')
 E.indent(p);E.ElementTree(p).write(folder/('Library.vbproj' if vb else 'Library.csproj'),encoding='utf-8',xml_declaration=True)
tools=source/'src/Tools/Source/CompilerGeneratorTools/Source'
for name,upstream,vb in [('VBSyntaxGenerator','VisualBasicSyntaxGenerator',True),('VBErrorFactsGenerator','VisualBasicErrorFactsGenerator',True),('BoundTreeGenerator','BoundTreeGenerator',False)]:
 folder,p,props,items=project(name,vb,True);files=sorted((tools/upstream).rglob('*.vb' if vb else '*.cs'))
 if vb:
  E.SubElement(props,'RootNamespace').text='Microsoft.CodeAnalysis.VisualBasic.Internal.'+name
 if name=='VBSyntaxGenerator':
  E.SubElement(props,'OptionStrict').text='Off'
  E.SubElement(props,'StartupObject').text='Microsoft.CodeAnalysis.VisualBasic.Internal.VBSyntaxGenerator.Program'
  files.extend(source/'src/Compilers/VisualBasic/Portable'/r for r in ['Declarations/DeclarationModifiers.vb','Syntax/SyntaxKind.vb'])
  for ns in ['System.Collections.ObjectModel','System.Xml.Linq']:E.SubElement(items,'Import',Include=ns)
  E.SubElement(items,'EmbeddedResource',Include=native(tools/upstream/'VBSyntaxModelSchema.xsd'),LogicalName='VBSyntaxModelSchema.xsd')
 for f in files:E.SubElement(items,'Compile',Include=native(f))
 manifest[name]=dict(source_files=len(files));save(folder,p,vb)


prefix=Path('/clang64/lib/dotnet/library-packs')
feed=subprocess.check_output(['cygpath','-am',str(prefix)],text=True).strip()
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
(out/'generator-projects.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared original SDK5.3 VB generator projects:',manifest)
