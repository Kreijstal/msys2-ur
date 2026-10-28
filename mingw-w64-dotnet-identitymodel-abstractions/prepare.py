"""Retain original project/common imports and all source; freeze CI version metadata."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,xml.etree.ElementTree as E

source,out=(Path(p).resolve() for p in sys.argv[1:]);shutil.copytree(source,out)
here=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
name='Microsoft.IdentityModel.Abstractions';project='src/'+name+'/'+name+'.csproj'
original_cs={p.relative_to(source).as_posix():sha(p) for p in (source/'src'/name).rglob('*.cs')}
assert len(original_cs)==9
gold=json.loads((here/'published-metadata.json').read_text())[0]
assert gold['name']==name and gold['version']=='6.35.0.0'
key=source/'build/35MSSharedLib1024.snk';assert key.read_bytes().hex()==gold['public_key']
metadata=out/'src'/name/'Properties/AssemblyInfo.cs';text=metadata.read_text()
versions={'AssemblyVersion':gold['version'],'AssemblyFileVersion':gold['attributes']['AssemblyFileVersionAttribute'],
          'AssemblyInformationalVersion':gold['attributes']['AssemblyInformationalVersionAttribute']}
for attr,value in versions.items():
    before='[assembly: '+attr+'("0.0.1")]';assert text.count(before)==1,attr
    text=text.replace(before,'[assembly: '+attr+'("'+value+'")]')
metadata.write_text(text)
modified_metadata={'src/'+name+'/Properties/AssemblyInfo.cs':sha(metadata)}
removed=[]
for relative in ['build/common.props',project]:
    path=out/relative;tree=E.parse(path)
    for group in tree.getroot():
        for item in list(group):
            if item.tag=='PackageReference':
                assert item.get('Include') in ['Microsoft.SourceLink.GitHub','Microsoft.CodeAnalysis.FxCopAnalyzers']
                removed.append(item.get('Include'));group.remove(item)
    props=E.SubElement(tree.getroot(),'PropertyGroup')
    if relative=='build/common.props':
        values=dict(VersionPrefix='6.35.0',VersionSuffix='',Version='6.35.0',PublicSign='true',DelaySign='false',
            TargetFrameworks='net8.0',EnablePackageValidation='false',EnableNETAnalyzers='false',NuGetAudit='false',
            TreatWarningsAsErrors='false',ProduceReferenceAssembly='true',ImportDirectoryBuildProps='false')
    else:values=dict(IsTrimmable='false',TargetFrameworks='net8.0',PackageReadmeFile='README.md')
    for prop,value in values.items():E.SubElement(props,prop).text=value
    if relative==project:
        items=E.SubElement(tree.getroot(),'ItemGroup')
        attr=E.SubElement(items,'AssemblyAttribute',Include='System.Reflection.AssemblyMetadataAttribute')
        E.SubElement(attr,'_Parameter1').text='IsTrimmable';E.SubElement(attr,'_Parameter2').text='True'
        E.SubElement(items,'None',Include='../../../LICENSE.txt',Pack='true',PackagePath='LICENSE.txt')
        E.SubElement(items,'None',Include='../../../README.md',Pack='true',PackagePath='README.md')
        E.SubElement(items,'None',Include='../../../source-inventory.json',Pack='true',PackagePath='source-build/inventory.json')
        E.SubElement(items,'None',Include='obj/Release/net8.0/ref/'+name+'.dll',Pack='true',PackagePath='ref/net8.0/'+name+'.dll')
    E.indent(tree);tree.write(path,encoding='utf-8',xml_declaration=True)
(out/'Directory.Build.targets').write_text('''<Project><Target Name="CaptureOriginalCompilerInputs" BeforeTargets="CoreCompile"><WriteLinesToFile File="$(IntermediateOutputPath)compiler-inputs.txt" Lines="@(Compile-&gt;'%(FullPath)')" Overwrite="true" Encoding="UTF-8"/></Target></Project>\n''')
original_test=source/'test/Microsoft.IdentityModel.Abstractions.Tests/TelemetryEventDetailsTests.cs'
fixture=original_test.read_text();assert fixture.count('[Fact]')==6
assert fixture.count('var mock = new Mock<TelemetryEventDetails>();')==4
fixture=fixture.replace('using Xunit;','').replace('using Moq;','').replace('[Fact]','[OwnedFact]')
fixture=fixture.replace('var mock = new Mock<TelemetryEventDetails>();','var mock = new OwnedTelemetry();')
fixture=fixture.replace('mock.CallBase = true;','').replace('mock.Object','mock')
assert 'Moq' not in fixture and 'Mock<' not in fixture
(out/'UpstreamTests.cs').write_text(fixture)
record=dict(source_commit='c94c7fc235501d478221e979062bd8837a55575b',source_archive_sha256='c8bb5a2b1a946b98dc7165ed8e01439b76cc2d91c1b3ab168e613f0120b763f2',
 original_cs=original_cs,ci_version_metadata=modified_metadata,production_algorithm_changes=[],
 original_project_metadata={p:sha(source/p) for p in [project,'build/common.props','build/targets.props','build/dependencies.props','build/version.props','updateAssemblyInfo.ps1','buildConfiguration.xml']},
 prepared_project_metadata={p:sha(out/p) for p in [project,'build/common.props','Directory.Build.targets']},
 removed_build_only_package_references=removed,original_signing_key_sha256=sha(key),
 original_telemetry_test_sha256=sha(original_test),adapted_test_sha256=sha(out/'UpstreamTests.cs'),
 test_fixture_changes='Replace four Moq constructions/CallBase/Object with concrete owned subclass; six original assertion bodies and derived-type helpers retained')
(out/'source-inventory.json').write_text(json.dumps(record,indent=2)+'\n')
shutil.copy2(here/'README.md',out/'README.md')
feed=subprocess.check_output(['cygpath','-am','/clang64/lib/dotnet/library-packs'],text=True).strip() if shutil.which('cygpath') else '/clang64/lib/dotnet/library-packs'
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source-only" value="'+feed+'"/></packageSources></configuration>\n')
print('PASS all nine original C# inputs; only original CI assembly-version attributes changed; six upstream telemetry cases retained')
