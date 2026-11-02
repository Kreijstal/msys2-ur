"""Restore and compile a source package through original NuGet and Roslyn CoreCompile targets."""
from pathlib import Path
import hashlib
import copy
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E

candidate,version,out=Path(sys.argv[1]).resolve(),sys.argv[2],Path(sys.argv[3]).resolve();out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';nuget=host.parent/'build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin';msbuild=host.parent/'build-packs/msbuild-18.3.0-net10-bootstrap/MSBuild.dll';tool=msbuild.parent/'Roslyn';native=lambda p:Path(p).resolve().as_posix()
feed=candidate/'lib/dotnet/library-packs';archive=feed/('wcwidth.sources.'+version+'.nupkg')
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="exact-source" value="'+native(feed)+'"/></packageSources></configuration>')
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(TargetFramework='net10.0',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',TargetFrameworkMoniker='.NETCoreApp,Version=v10.0',RestoreProjectStyle='PackageReference',MSBuildProjectExtensionsPath=native(out/'obj')+'/',BaseIntermediateOutputPath=native(out/'obj')+'/',RestoreConfigFile=native(out/'NuGet.config'),RestorePackagesPath=native(out/'cache'),RestoreTaskAssemblyFile=native(nuget/'NuGet.Build.Tasks.dll'),TreatWarningsAsErrors='true',NuGetAudit='false').items():E.SubElement(pg,k).text=v
E.SubElement(E.SubElement(p,'ItemGroup'),'PackageReference',Include='Wcwidth.Sources',Version='['+version+']',GeneratePathProperty='true',ExcludeAssets='all' if version=='2.0.0' else '')
E.SubElement(p,'Import',Project=native(nuget/'NuGet.targets'));E.ElementTree(p).write(out/'Restore.proj',encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(msbuild),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',MSBuildEnableWorkloadResolver='false');commands=[]
def run(label,cmd):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=240)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
    return (out/(label+'.log')).read_text()
run('restore',[host,nuget/'MSBuild.dll',out/'Restore.proj','-t:Restore','-nologo','-v:minimal'])
assets=json.loads((out/'obj/project.assets.json').read_text());assert not assets.get('logs')
cache=out/'cache/wcwidth.sources'/version;assert (cache/archive.name).read_bytes()==archive.read_bytes()
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
source=out/'Program.cs';source.write_text('using System; using Wcwidth; class Program { static void Main() { if(UnicodeCalculator.GetWidth(0x4e16)!=2 || UnicodeCalculator.GetWidth(0x0301)!=0 || UnicodeCalculator.GetWidth(new System.Text.Rune(0x1f680))!=2)throw new Exception("Widths");Console.WriteLine("PASS actual source NuGet compile and Unicode widths"); } }\n')
usings=out/'GlobalUsings.cs';usings.write_text('global using System;global using System.Collections.Generic;global using System.IO;global using System.Linq;global using System.Net.Http;global using System.Threading;global using System.Threading.Tasks;')
p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
for k,v in dict(Language='C#',BaseIntermediateOutputPath=native(out/'obj')+'/',NuGetPackageRoot=native(out/'cache')+'/',TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',_TargetFrameworkVersionWithoutV='10.0',OutputType='Exe',NoCompilerStandardLib='true',Nullable='enable' if version=='4.0.1' else 'disable',TreatWarningsAsErrors='true',UseSharedCompilation='false',IntermediateOutputPath=native(out)+'/',GeneratedMSBuildEditorConfigFile=native(out/'Generated.editorconfig'),DefineConstants='TRACE;NET;NETCOREAPP;NET10_0;NET6_0_OR_GREATER;NET7_0_OR_GREATER;NET8_0_OR_GREATER;NET9_0_OR_GREATER;NET10_0_OR_GREATER').items():E.SubElement(pg,k).text=v
E.SubElement(p,'Import',Project=native(out/'obj/Restore.proj.nuget.g.props'));items=E.SubElement(p,'ItemGroup');E.SubElement(items,'Compile',Include=native(source));E.SubElement(items,'Compile',Include=native(usings));E.SubElement(items,'IntermediateAssembly',Include=native(out/'App.dll'))
for ref in refs:E.SubElement(items,'ReferencePathWithRefAssemblies',Include=native(ref))
if version=='2.0.0':
    policy=Path(__file__).resolve().parent/'SDK.Microsoft.TemplateEngine.Cli.csproj'
    assert hashlib.sha256(policy.read_bytes()).hexdigest()=='b31a15f17e4a36cd56846d1e6f2c9bb36e0590c47c76920d1be209d363f5074e'
    original_target=E.parse(policy).find("Target[@Name='CopyExternalSourceFilesIntoProject']")
    assert original_target is not None
    p.append(copy.deepcopy(original_target))
E.SubElement(p,'Target',Name='PrepareForBuild');E.SubElement(p,'Import',Project=native(tool/'Microsoft.CSharp.Core.targets'));E.SubElement(p,'Import',Project=native(out/'obj/Restore.proj.nuget.g.targets'))
E.ElementTree(p).write(out/'Compile.proj',encoding='utf-8',xml_declaration=True)
run('compile',[host,msbuild,out/'Compile.proj','-t:'+('CopyExternalSourceFilesIntoProject;CoreCompile' if version=='2.0.0' else 'CoreCompile'),'-nr:false','-noautoresponse','-nologo','-v:diag'])
(out/'App.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
assert 'PASS actual source NuGet compile and Unicode widths' in run('execute',[host,out/'App.dll'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,version=version,exact_fresh_source_archive_bytes_verified=True,original_Roslyn_CoreCompile_task_used=True,SDK_net6_source_copy_and_ExcludeAssets_all_preserved=version=='2.0.0',original_SDK_copy_target_executed_unchanged=version=='2.0.0',NuGet_automatic_content_compile_items_used=version=='4.0.1',Unicode_width_execution_passed=True,original_full_SDK10_build_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS fresh NuGet source restore and original Roslyn task consumer',version)
