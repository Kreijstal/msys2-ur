"""Use original installed Roslyn targets with NuGet-selected source analyzer and policy imports.

This no-SDK fixture validates the actual compile task and package imports. A full
original SDK10 build remains a separate open gate.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

prefix, restore, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
actual = Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host = actual / 'lib/dotnet10/dotnet.exe'
msbuild = actual / 'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/MSBuild.dll'
tool = msbuild.parent / 'Roslyn'
refs = sorted((actual / 'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'))
assert len(refs)==167
cache = restore / 'cache/microsoft.codeanalysis.publicapianalyzers/3.3.4'
archive = prefix / 'lib/dotnet/library-packs/microsoft.codeanalysis.publicapianalyzers.3.3.4.nupkg'
assert (cache/archive.name).read_bytes()==archive.read_bytes()
native=lambda p:Path(p).resolve().as_posix()
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(msbuild),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',MSBuildEnableWorkloadResolver='false')
source=out/'Fixture.cs';source.write_text('#nullable enable\npublic static class Fixture { public static string Echo(string value)=>value; }\n')
shipped=out/'PublicAPI.Shipped.txt';shipped.write_text('#nullable enable\nFixture\nstatic Fixture.Echo(string! value) -> string!\n')
unshipped=out/'PublicAPI.Unshipped.txt';unshipped.write_text('#nullable enable\n')
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',_TargetFrameworkVersionWithoutV='10.0',OutputType='Library',NoCompilerStandardLib='true',Nullable='enable',TreatWarningsAsErrors='true',CodeAnalysisTreatWarningsAsErrors='true',AnalysisMode='All',MicrosoftCodeAnalysisPublicApiAnalyzersRulesVersion='3.3.3',UseSharedCompilation='false',Utf8Output='true',IntermediateOutputPath=native(out)+'/',GeneratedMSBuildEditorConfigFile=native(out/'Generated.editorconfig')).items():E.SubElement(pg,k).text=v
E.SubElement(p,'Import',Project=native(restore/'obj/Dependencies.proj.nuget.g.props'))
items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=native(source));E.SubElement(items,'IntermediateAssembly',Include=native(out/'Fixture.dll'))
for ref in refs:E.SubElement(items,'ReferencePathWithRefAssemblies',Include=native(ref))
for file in [shipped,unshipped]:E.SubElement(items,'AdditionalFiles',Include=native(file))
for name in ['Microsoft.CodeAnalysis.PublicApiAnalyzers.dll','Microsoft.CodeAnalysis.PublicApiAnalyzers.CodeFixes.dll']:E.SubElement(items,'Analyzer',Include=native(cache/'analyzers/dotnet'/name))
E.SubElement(p,'Target',Name='PrepareForBuild')
E.SubElement(p,'Import',Project=native(tool/'Microsoft.CSharp.Core.targets'))
E.SubElement(p,'Import',Project=native(restore/'obj/Dependencies.proj.nuget.g.targets'))
receipt=E.SubElement(p,'Target',Name='Receipt',AfterTargets='CoreCompile');E.SubElement(receipt,'WriteLinesToFile',File=native(out/'receipt.txt'),Lines='@(EditorConfigFiles)',Overwrite='true')
project=out/'Compile.proj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
cmd=[host,msbuild,project,'-t:CoreCompile','-nr:false','-noautoresponse','-nologo','-v:diag']
records=[]
for label,expected in [('exact',0),('nullable-changed',1)]:
    if expected:shipped.write_text('#nullable enable\nFixture\nstatic Fixture.Echo(string? value) -> string!\n')
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=180)
    text=(out/(label+'.log')).read_text()
    assert r.returncode==expected,(label,r.returncode)
    assert not any(code in text for code in ['AD0001','CS8032','CS9057'])
    if expected:assert 'RS0016' in text or 'RS0017' in text
    else:
        assert 'analysislevel_3_3_3_all_warnaserror.globalconfig' in (out/'receipt.txt').read_text(encoding='utf-8-sig').lower()
        assert native(tool/'Microsoft.Build.Tasks.CodeAnalysis.dll').lower() in text.replace('\\','/').lower()
    records.append(dict(case=label,command=[str(p) for p in cmd],exit_code=r.returncode,expected_exit_code=expected))
(out/'results.json').write_text(json.dumps(dict(cases=records,actual_cached_source_archive_SHA256=hashlib.sha256(archive.read_bytes()).hexdigest(),original_installed_Roslyn_targets_and_source_task_used=True,NuGet_selected_build_imports_and_generated_globalconfig_executed=True,analyzer_load_exceptions_rejected=True,full_original_SDK10_build_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original Roslyn CoreCompile task, actual NuGet imports and globalconfig, exact API and changed-nullable rejection')
