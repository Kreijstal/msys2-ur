"""Set up owned source-only runtime/generator/SDK/metadata consumers."""
from pathlib import Path
import shutil,subprocess,sys,xml.etree.ElementTree as E

here,out=(Path(p) for p in sys.argv[1:3])
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
config=E.Element('configuration');sources=E.SubElement(config,'packageSources');E.SubElement(sources,'clear')
E.SubElement(sources,'add',key='installed-source',value=native(Path('/clang64/lib/dotnet/library-packs')))
if len(sys.argv)>3:
    E.SubElement(sources,'add',key='new-source',value=native(Path(sys.argv[3])))
    mapping=E.SubElement(config,'packageSourceMapping')
    E.SubElement(E.SubElement(mapping,'packageSource',key='new-source'),'package',pattern='System.Text.Json')
    E.SubElement(E.SubElement(mapping,'packageSource',key='installed-source'),'package',pattern='*')
E.ElementTree(config).write(out/'NuGet.config',encoding='utf-8',xml_declaration=True)
for folder,filename,refs in [('', 'Check.cs',[('System.Text.Json','8.0.5'),('Microsoft.CodeAnalysis.CSharp','4.9.2')]),
                           ('sample','SdkSample.cs',[('System.Text.Json','8.0.5')]),
                           ('tools','InspectApi.cs',[('Microsoft.CodeAnalysis.CSharp','4.9.2')]),
                           ('pe','InspectAssemblyMetadata.cs',[])]:
    target=out/folder;target.mkdir(exist_ok=True)
    shutil.copy2(here/filename,target/filename)
    p=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(p,'PropertyGroup')
    for key,value in dict(TargetFramework='net8.0',OutputType='Exe',UseAppHost='false',EnableDefaultItems='false',
        EnableNETAnalyzers='false',NuGetAudit='false',WarningsAsErrors='CS9057;CS8032;AD0001').items():E.SubElement(props,key).text=value
    items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=filename)
    for name,version in refs:E.SubElement(items,'PackageReference',Include=name,Version='['+version+']')
    if folder=='sample':
        E.SubElement(props,'EmitCompilerGeneratedFiles').text='true'
        E.SubElement(items,'RuntimeHostConfigurationOption',Include='System.Text.Json.JsonSerializer.IsReflectionEnabledByDefault',Value='false')
        capture=E.SubElement(p,'Target',Name='CaptureSelectedAnalyzer',BeforeTargets='CoreCompile')
        E.SubElement(capture,'WriteLinesToFile',File='analyzer-inputs.txt',Lines="@(Analyzer->'%(FullPath)')",Overwrite='true')
    E.indent(p);E.ElementTree(p).write(target/'Check.csproj',encoding='utf-8',xml_declaration=True)
