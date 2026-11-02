"""Build the original 4.4 csc command-line inputs against source NS2 libraries."""
from pathlib import Path
import hashlib
import json
import os
import posixpath
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E

archive,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='9edb8c430576c5f5b27032afe8f79c74508b0150e03406a7a4ca6f218e03fd11'
with tarfile.open(archive) as t:
    assert t.pax_headers['comment']=='1ce8866c9de4c2d67351ef6863699dee03b0804a'
    entries={m.name.partition('/')[2]:m for m in t if m.isfile()}
    project='src/Compilers/CSharp/csc/CscCommandLine.projitems'
    shared=E.fromstring(t.extractfile(entries[project]).read())
    selected={project}
    for item in shared.findall('.//{*}Compile'):
        relative=posixpath.normpath(item.get('Include').replace('$(MSBuildThisFileDirectory)',posixpath.dirname(project)+'/').replace('\\','/'))
        assert relative in entries and not relative.startswith('../')
        selected.add(relative)
    source=out/'original-source'
    for name in selected:
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(t.extractfile(entries[name]).read())
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
here=Path(__file__).parent
key=bytes.fromhex((here/'inputs/MicrosoftShared.pubkey.hex').read_text())
assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='31bf3856ad364e35'
(out/'Compiler.public.snk').write_bytes(key)
original=source/'src/Compilers/CSharp/csc/CscCommandLine.projitems';shared=E.parse(original)
tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');props=E.SubElement(tree,'PropertyGroup')
for name,value in dict(TargetFramework='net8.0',OutputType='Exe',AssemblyName='csc',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',Nullable='enable',LangVersion='preview',AllowUnsafeBlocks='true',Version='4.4.0',AssemblyVersion='4.4.0.0',FileVersion='4.4.0.0',InformationalVersion='4.4.0+1ce8866c9de4c2d67351ef6863699dee03b0804a',IncludeSourceRevisionInInformationalVersion='false',SignAssembly='true',PublicSign='true',AssemblyOriginatorKeyFile='Compiler.public.snk',StartupObject='Microsoft.CodeAnalysis.CSharp.CommandLine.Program',TreatWarningsAsErrors='true',CscToolPath=native(Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.0.0-bootstrap')),CscToolExe='csc50.cmd').items():E.SubElement(props,name).text=value
items=E.SubElement(tree,'ItemGroup');files={}
for item in shared.findall('.//{*}Compile'):
    path=Path(item.get('Include').replace('$(MSBuildThisFileDirectory)',str(original.parent)+'/').replace('\\','/')).resolve()
    assert path.is_file() and path.is_relative_to(source.resolve())
    E.SubElement(items,'Compile',Include=native(path));files[path.relative_to(source.resolve()).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
for package in ['Microsoft.CodeAnalysis.Common','Microsoft.CodeAnalysis.CSharp']:E.SubElement(items,'PackageReference',Include=package,Version='[4.4.0]')
E.indent(tree);E.ElementTree(tree).write(out/'Tool.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(Path('/clang64/lib/dotnet/library-packs'))+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
subprocess.run(['/clang64/lib/dotnet/dotnet.exe','build',native(out/'Tool.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,check=True)
compiler=out/'bin/Release/net8.0'
(compiler/'csc44.cmd').write_bytes(('@echo off\r\n"'+native(Path('/clang64/lib/dotnet/dotnet.exe'))+'" "%~dp0csc.dll" %*\r\nexit /b %errorlevel%\r\n').encode())
(out/'source-inputs.json').write_text(json.dumps(dict(source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),source_commit='1ce8866c9de4c2d67351ef6863699dee03b0804a',original_csc_compile_items=files,original_csc_source_changes=0,library_packages=['Microsoft.CodeAnalysis.Common/4.4.0','Microsoft.CodeAnalysis.CSharp/4.4.0'],original_cli_host_retargeted_to_NET8_bootstrap=True),indent=2)+'\n')
print('PASS original source csc4.4 bootstrap host',len(files),'unchanged compile inputs')
