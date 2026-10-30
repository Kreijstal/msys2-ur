"""Keep original MSAL projects/globs/imports and replay the complete net6 branch on net8."""
import os
from pathlib import Path
import hashlib,json,shutil,struct,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);here=Path(__file__).resolve().parent
inputs=json.loads((here/'source-inputs.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for spec in inputs.values():
    for path,digest in spec['original_project_tree_sha256'].items():assert sha(source/path)==digest,path
shutil.copytree(source,out);names=list(inputs)
gold={name:json.loads((here/(name+'.metadata.json')).read_text())[0] for name in names}
key=(source/'build/MSAL.snk').read_bytes();assert key[0]==7 and key[8:12]==b'RSA2'
bits=struct.unpack_from('<I',key,12)[0];blob=bytes([6])+key[1:8]+b'RSA1'+key[12:20+bits//8]
public=struct.pack('<III',0x2400,0x8004,len(blob))+blob
assert all(m['public_key']==public.hex() and m['version']=='4.61.3.0' for m in gold.values())
removed=[];modified=[]
def save(tree,path):
    E.indent(tree);tree.write(out/path,encoding='utf-8',xml_declaration=True);modified.append(path)
def properties(tree,values):
    group=E.SubElement(tree.getroot(),'PropertyGroup')
    for k,v in values.items():E.SubElement(group,k).text=v
for path in ['Directory.Build.props','src/Directory.Build.props']:
    tree=E.parse(source/path)
    for group in tree.getroot():
        for item in list(group):
            if item.tag=='PackageReference':
                assert item.get('PrivateAssets')=='All'
                assert item.get('Include') in ['Microsoft.VisualStudio.Threading.Analyzers','Microsoft.CodeAnalysis.NetAnalyzers','Microsoft.SourceLink.GitHub']
                removed.append(item.get('Include'));group.remove(item)
    if path=='Directory.Build.props':
        properties(tree,dict(MsalClientSemVer='4.61.3',Version='4.61.3',AssemblyVersion=gold[names[0]]['version'],
            FileVersion=gold[names[0]]['attributes']['AssemblyFileVersionAttribute'],
            InformationalVersion=gold[names[0]]['attributes']['AssemblyInformationalVersionAttribute'],
            RepositoryUrl='https://github.com/AzureAD/microsoft-authentication-library-for-dotnet',
            IncludeSourceRevisionInInformationalVersion='false',EnableNETAnalyzers='false',NuGetAudit='false',
            GeneratePackageOnBuild='false',ProduceReferenceAssembly='true',EmitCompilerGeneratedFiles='true'))
    save(tree,path)
tree=E.parse(source/'Directory.Packages.props')
versions={'Microsoft.IdentityModel.Abstractions':'[6.35.0]','System.Security.Cryptography.ProtectedData':'[8.0.0]','System.Text.Json':'[8.0.5]'}
for item in tree.iter('PackageVersion'):
    if item.get('Include') in versions:item.set('Version',versions.pop(item.get('Include')))
group=E.SubElement(tree.getroot(),'ItemGroup')
for name,version in versions.items():E.SubElement(group,'PackageVersion',Include=name,Version=version)
save(tree,'Directory.Packages.props')
for name in names:
    path='src/client/'+name+'/'+name+'.csproj';tree=E.parse(source/path)
    for prop in tree.iter('TargetFrameworkNet6'):prop.text='net8.0'
    for group in tree.getroot():
        condition=group.get('Condition','')
        if 'TargetFrameworkNet6Android' in condition or 'TargetFrameworkNet6Ios' in condition:
            group.set('Condition',"'$(TargetFramework)' != '' and ("+condition+")")
        for item in list(group):
            if item.tag!='PackageReference':continue
            dependency=item.get('Include')
            if dependency in ['System.Diagnostics.DiagnosticSource','Microsoft.CodeAnalysis.RulesetToEditorconfigConverter']:
                if dependency!='System.Diagnostics.DiagnosticSource':removed.append(dependency)
                group.remove(item)
    properties(tree,dict(TargetFrameworks='net8.0',IsTrimmable='false',EnableTrimAnalyzer='false'))
    if name=='Microsoft.Identity.Client':
        items=E.SubElement(tree.getroot(),'ItemGroup')
        E.SubElement(items,'PackageReference',Include='System.Text.Json')
        attribute=E.SubElement(items,'AssemblyAttribute',Include='System.Reflection.AssemblyMetadataAttribute')
        E.SubElement(attribute,'_Parameter1').text='IsTrimmable';E.SubElement(attribute,'_Parameter2').text='True'
    save(tree,path)
targets=E.Element('Project');target=E.SubElement(targets,'Target',Name='CaptureOriginalBuildInputs',BeforeTargets='CoreCompile')
for kind in ['Compile','ReferencePath','Analyzer','EmbeddedResource']:
    E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)'+kind+'.txt',Lines='@('+kind+"->'%(FullPath)')",Overwrite='true',Encoding='UTF-8')
for prop in ['DefineConstants','SignAssembly','PublicSign','IsTrimmable']:
    E.SubElement(target,'WriteLinesToFile',File='$(IntermediateOutputPath)'+prop+'.txt',Lines='$('+prop+')',Overwrite='true',Encoding='UTF-8')
E.ElementTree(targets).write(out/'Directory.Build.targets',encoding='utf-8',xml_declaration=True);modified.append('Directory.Build.targets')
(out/'global.json').write_text(json.dumps({'sdk':{'version':'8.0.131','rollForward':'disable'}},indent=2)+'\n');modified.append('global.json')
# The published Windows build embeds the same original directives with CRLF.
directive='src/client/Microsoft.Identity.Client/Properties/Microsoft.Identity.Client.rd.xml'
data=(source/directive).read_bytes();(out/directive).write_bytes(data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'));modified.append(directive)
feed=subprocess.check_output(['cygpath','-am',os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs'],text=True).strip() if shutil.which('cygpath') else os.environ['MINGW_PREFIX']+'/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="installed-source" value="'+feed+'"/></packageSources></configuration>\n')
metadata=['Directory.Build.props','src/Directory.Build.props','Directory.Packages.props','global.json','build/platform_and_feature_flags.props']+[f'src/client/{n}/{n}.csproj' for n in names]
record=dict(source_commit='88df64013795d4e3716e1f677600f8164ffdb542',source_archive_sha256=inputs[names[0]]['source_archive_sha256'],
 original_project_trees={n:inputs[n]['original_project_tree_sha256'] for n in names},
 original_project_metadata={p:sha(source/p) for p in metadata},prepared_project_metadata={p:sha(out/p) for p in modified},
 original_signing_key_sha256=sha(source/'build/MSAL.snk'),production_cs_changes=[],removed_build_only_packages=removed,
 framework_provided=['System.Diagnostics.DiagnosticSource','System.IO.FileSystem.AccessControl (inactive netstandard2.0 branch)'],
 selected_original_framework='net6.0',retargeted_framework='net8.0',source_dependencies={'Microsoft.IdentityModel.Abstractions':'6.35.0','System.Text.Json':'8.0.5','System.Security.Cryptography.ProtectedData':'8.0.0'})
(out/'source-inventory.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS complete original MSAL/cache projects, unmodified C#, original NET6 feature/platform selection, open signing key and frozen release versions')
