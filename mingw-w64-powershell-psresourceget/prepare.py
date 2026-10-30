"""Compile the complete original PSResourceGet project against the source.NET8 graph."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
inputs=json.loads((here/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,digest in inputs['original_src_inputs'].items():assert sha(source/path)==digest,path
project=source/'src/code/Microsoft.PowerShell.PSResourceGet.csproj';tree=E.parse(project);tree.getroot().attrib.pop('Sdk')
removed=[];framework=['System.Net.Http','Microsoft.CSharp','System.Web']
for group in tree.getroot().findall('ItemGroup'):
    for item in list(group):
        if item.tag=='PackageReference':
            name=item.get('Include')
            if name in framework or name=='PowerShellStandard.Library':removed.append(name);group.remove(item)
            else:item.set('Version','['+item.get('Version')+']')
        elif item.tag=='Reference':assert item.get('Include')=='System.Web';removed.append('System.Web');group.remove(item)
E.indent(tree);tree.write(out/'upstream.proj',encoding='utf-8',xml_declaration=True)
p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(ImportDirectoryBuildProps='false',ImportDirectoryBuildTargets='false',EnableDefaultItems='false',TargetFramework='net8.0').items():E.SubElement(props,k).text=v
E.SubElement(p,'Import',Project='upstream.proj');props=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net8.0',TargetFrameworks='',Version='1.1.1',InformationalVersion='1.1.0.1+44697aed1740126153a8d9dd0ef368261b2fe45c',IncludeSourceRevisionInInformationalVersion='false',GenerateDocumentationFile='true',GeneratePackageOnBuild='false',EnableNETAnalyzers='false',NuGetAudit='false',CopyLocalLockFileAssemblies='true').items():E.SubElement(props,k).text=v
items=E.SubElement(p,'ItemGroup');files=sorted((source/'src/code').rglob('*.cs'));assert len(files)==56
changed='src/code/ContainerRegistryServerAPICalls.cs';overlay=out/'overlays/ContainerRegistryServerAPICalls.cs';overlay.parent.mkdir()
data=(source/changed).read_bytes();before=b'new SortedDictionary<SemanticVersion, string>';after=b'new SortedDictionary<NuGet.Versioning.SemanticVersion, string>'
assert data.count(before)==1;overlay.write_bytes(data.replace(before,after))
for path in files:E.SubElement(items,'Compile',Include=os.path.relpath(overlay if path==source/changed else path,out).replace('\\','/'))
sma=os.environ['MINGW_PREFIX']+'/lib/dotnet/tools/powershell-module-test-host/System.Management.Automation.dll'
native=lambda value:subprocess.check_output(['cygpath','-am',value],text=True).strip() if shutil.which('cygpath') else value
reference=E.SubElement(items,'Reference',Include='System.Management.Automation');E.SubElement(reference,'HintPath').text=native(sma);E.SubElement(reference,'Private').text='false'
capture=E.SubElement(p,'Target',Name='CaptureOriginalCompilerInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer']:E.SubElement(capture,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
E.indent(p);E.ElementTree(p).write(out/'Library.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+native(os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs')+'"/></packageSources></configuration>\n')
r=dict(source_commit=inputs['source_commit'],source_archive_sha256=inputs['source_archive_sha256'],original_cs={path.relative_to(source).as_posix():sha(path) for path in files},original_module_assets={path:digest for path,digest in inputs['original_src_inputs'].items() if not path.startswith('src/code/')},original_project_metadata={'src/code/Microsoft.PowerShell.PSResourceGet.csproj':sha(project)},prepared_project_metadata={path:sha(out/path) for path in ['Library.csproj','upstream.proj']},production_cs_changes=[dict(path=changed,overlay='overlays/ContainerRegistryServerAPICalls.cs',original_sha256=sha(source/changed),prepared_sha256=sha(overlay),reason='Fully qualify the already-intended NuGet SemanticVersion constructor type because source SMA7.4 also exposes SemanticVersion')],framework_provided=framework,removed_package_or_framework_references=removed,source_engine_reference='complete source SMA7.4.20',source_dependencies={v.get('Include'):v.get('Version') for v in tree.iter('PackageReference')})
(out/'source-inventory.json').write_text(json.dumps(r,indent=2)+'\n')
print('PASS full56-input PSResourceGet source inventory:55 unchanged, one explicit NuGet type qualification; complete module assets and exact source dependencies')
