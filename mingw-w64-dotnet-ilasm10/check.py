"""Exercise original Unsafe IL, resource layouts and executable IL with the exact assembler."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as E
from pe_resource import version_payload

root, unsafe_archive, out = (Path(p).resolve() for p in sys.argv[1:4])
exe = Path(sys.argv[4]).resolve() if len(sys.argv)==5 else root/'coreclr-build/ilasm/ilasm.exe'
assert not out.exists(), out
out.mkdir(parents=True)
here = Path(__file__).resolve().parent
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(unsafe_archive)=='6e6f764834ebf0d9135d0c0dff9d78209df629eee496192c022a531e7f915a7e'
native=lambda p: subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
         DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
def run(command, log, cwd=None):
    with log.open('w') as stream:
        result=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,cwd=cwd)
    assert result.returncode==0,(command,log)
config=out/'NuGet.config';config.write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
def project(folder, name, source=None, exe=False):
    folder.mkdir()
    tree=E.Element('Project',Sdk='Microsoft.NET.Sdk');pg=E.SubElement(tree,'PropertyGroup')
    values=dict(TargetFramework='net8.0',AssemblyName=name,OutputType='Exe' if exe else 'Library',UseAppHost='false',EnableDefaultItems='false',EnableNETAnalyzers='false',NuGetAudit='false',UseSharedCompilation='false',Version='6.1.1',AssemblyVersion='6.1.1.0',FileVersion='6.1.1.0',InformationalVersion='6.1.1+ab95a1f103b49919ba02577a99f3173405bb50ca')
    for k,v in values.items():E.SubElement(pg,k).text=v
    if source:E.SubElement(E.SubElement(tree,'ItemGroup'),'Compile',Include=native(source))
    E.indent(tree);path=folder/'Build.csproj';E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)
    run([dotnet,'build',native(path),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'],folder/'build.log')
    return folder/'bin/Release/net8.0'/(name+'.dll')

fixture=out/'fixture';fixture.mkdir()
name='System.Runtime.CompilerServices.Unsafe';folder=fixture/name;folder.mkdir()
commit='ab95a1f103b49919ba02577a99f3173405bb50ca'
source_root=fixture/('maintenance-packages-'+commit)
source_name='src/'+name+'/src/'+name+'.il'
wanted={source_name, 'src/'+name+'/Versioning.props'};original={}
with tarfile.open(unsafe_archive) as t:
    assert t.pax_headers['comment']==commit
    for m in t:
        path=m.name.partition('/')[2]
        if m.isfile() and path in wanted:
            data=t.extractfile(m).read();p=source_root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            original[path]=hashlib.sha256(data).hexdigest()
assert set(original)==wanted
binary=project(out/'versioning','OwnedVersionResource')
blob=version_payload(binary);(folder/'native-version.bin').write_bytes(blob)
(folder/'native-version.rc').write_text('1 16 "native-version.bin"\n')
run(['/clang64/bin/llvm-rc.exe','-fo','native-version.res','native-version.rc'],folder/'rc.log',folder)
run(['/clang64/bin/llvm-cvtres.exe','-machine:x86','-out:native-version.obj','native-version.res'],folder/'cvtres.log',folder)
include=folder/'include';include.mkdir()
(include/'version.h').write_text('''#define CORE_ASSEMBLY "netstandard"
#define ASSEMBLY_VERSION "6:0:0:0"
#define CORE_ASSEMBLY_VERSION "2:0:0:0"
#define FILE_VERSION "{string('6.1.1.0')}"
#define INFORMATIONAL_VERSION "{string('6.1.1+ab95a1f103b49919ba02577a99f3173405bb50ca')}"
.assembly extern CORE_ASSEMBLY { .publickeytoken = (CC 7B 13 FF CD 2D DD 51) .ver CORE_ASSEMBLY_VERSION }
''')
key=bytes.fromhex((here/'inputs/Microsoft.pubkey.hex').read_text());assert hashlib.sha1(key).digest()[-8:][::-1].hex()=='b03f5f7f11d50a3a'
(fixture/'Microsoft.pubkey').write_bytes(key)
(fixture/'source-inputs.json').write_text(json.dumps(dict(projects={name:dict(commit=commit,original_sources={source_name:original[source_name]})}),indent=2)+'\n')
run(['/usr/bin/python3',str(here/'check-resources.py'),str(root),str(fixture),str(out/'resource-cases'),str(exe)],out/'resources.log')
emitted=out/'resource-cases/llvm-two-sections'/(name+'.dll')
checker=project(out/'metadata','CheckEmitted',here/'inputs/CheckEmitted.cs',True)
run([dotnet,native(checker),native(emitted)],out/'metadata.log')
source=out/'owned π space.il';source.write_bytes((here/'inputs/OwnedProbe.il').read_bytes())
program=out/'OwnedILAsmProbe.dll'
run([native(exe),'-EXE','-DET','-DEBUG=OPT','-OUTPUT='+native(program),native(source)],out/'owned-il-build.log')
(out/'OwnedILAsmProbe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net8.0',framework=dict(name='Microsoft.NETCore.App',version='8.0.31'))))+'\n')
run([dotnet,native(program)],out/'owned-il-run.log')
results=dict(assembler_sha256=sha(exe),original_unsafe_source_inputs_sha256=original,original_unsafe_public_methods=42,portable_pdb_verified=True,
             resource_cases=json.loads((out/'resource-cases/results.json').read_text())['cases'],owned_il_loop_execution_exit_code=0,unicode_space_source_path=True,
             installed_assembler=len(sys.argv)==5,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('PASS original Unsafe IL/42 methods/portable PDB, five COFF resource cases, Unicode input path and emitted IL execution')
