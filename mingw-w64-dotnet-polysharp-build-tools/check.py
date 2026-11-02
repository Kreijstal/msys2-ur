"""Exercise original packaged MSBuild behavior using isolated source-only caches."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

out, candidate, producer = (Path(p).resolve() for p in sys.argv[1:])
assert not out.exists()
out.mkdir()
native = lambda p: subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
feed = out/'feed';feed.mkdir()
available = {}
for base in [candidate,Path('/clang64/lib/dotnet/library-packs')]:
    for path in base.glob('*.nupkg'):
        available.setdefault(path.name.lower(),path)
for name,path in available.items():
    try: os.link(path,feed/name)
    except OSError: shutil.copyfile(path,feed/name)
config=out/'NuGet.config'
config.write_text('<configuration><packageSources><clear/><add key="source" value="'+native(feed)+'"/></packageSources></configuration>\n')
env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')),
    DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),
    DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
commands=[]
def run(label,args,expected=0):
    with (out/(label+'.log')).open('w') as log:
        result=subprocess.run([dotnet,*args],env=env,cwd=out,stdout=log,stderr=subprocess.STDOUT)
    text=(out/(label+'.log')).read_text()
    commands.append(dict(label=label,command=[dotnet,*args],exit_code=result.returncode,expected_exit_code=expected))
    assert result.returncode==expected,(label,result.returncode,text[-5000:])
    return text
def project(folder,body):
    folder.mkdir()
    if folder.name != 'direct':
        body=body.replace('<PropertyGroup>','<PropertyGroup><AssemblyName>'+folder.name+'</AssemblyName>',1)
    path=folder/'Check.csproj';path.write_text(body)
    return path
capture='''<Target Name="Capture" AfterTargets="Build"><WriteLinesToFile File="$(MSBuildProjectDirectory)/properties.$(TargetFramework).txt" Lines="$(UsingMicrosoftNoTargetsSdk)|$(EnableDefaultCompileItems)|$(EnableDefaultEmbeddedResourceItems)|$(IncludeBuildOutput)|$(ProduceReferenceAssembly)|$(DebugType)|$(PublishRepositoryUrl)" Overwrite="true"/></Target>'''
defaults='<TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit><UseAppHost>false</UseAppHost>'
client=project(out/'direct','<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType>'+defaults+'</PropertyGroup><ItemGroup><PackageReference Include="DotNet.ReproducibleBuilds" Version="[1.2.25]"/></ItemGroup>'+capture+'</Project>')
(client.parent/'Program.cs').write_text('''using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.PortableExecutable;
using var reader = new PEReader(File.OpenRead(Assembly.GetExecutingAssembly().Location));
if (!reader.ReadDebugDirectory().Any(e => e.Type == DebugDirectoryEntryType.EmbeddedPortablePdb)) throw new Exception("Missing embedded PDB");
Console.WriteLine("PASS actual embedded portable PDB from original reproducible-build props");
''')
run('direct-build',['build',native(client),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
assert (client.parent/'properties.net8.0.txt').read_text().strip().endswith('|embedded|true')
run('embedded-pdb',['exec',native(client.parent/'bin/Release/net8.0/Check.dll')])
source=json.loads((producer/'source-results.json').read_text())
for ident,record in source['packages'].items():
    name=ident.lower()+'.'+record['version']+'.nupkg'
    cached=out/'cache'/ident.lower()/record['version']/name
    # NoTargets resolves in the following test; reproducible-builds is now cached.
    if ident=='DotNet.ReproducibleBuilds': assert cached.read_bytes()==(feed/name).read_bytes()

# A real SDK-resolution/build/pack path with broken C# and resx default inputs.
# The same inputs would fail in a compiling project.
for extension in ['csproj','msbuildproj']:
    folder=out/('notargets-'+extension);folder.mkdir()
    path=folder/('Data.'+extension)
    path.write_text('<Project Sdk="Microsoft.Build.NoTargets/2.0.1"><PropertyGroup><TargetFramework>net8.0</TargetFramework><GenerateDependencyFile>false</GenerateDependencyFile><SuppressDependenciesWhenPacking>true</SuppressDependenciesWhenPacking><PackageId>NoTargets.Source.Probe</PackageId><Version>1.0.0</Version>'+defaults+'</PropertyGroup><ItemGroup><None Include="payload.txt" Pack="true" PackagePath="data/"/></ItemGroup>'+capture+'</Project>')
    (folder/'Broken.cs').write_text('this is deliberately invalid C#')
    (folder/'Broken.resx').write_text('this is deliberately invalid XML')
    (folder/'payload.txt').write_text('owned data-only probe\n')
    run('notargets-'+extension,['build',native(path),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
    props=(folder/'properties.net8.0.txt').read_text().strip().split('|')
    assert props[:5]==['true','false','false','false','false'],props
    assert not list((folder/'bin').rglob('*.dll')) and not list((folder/'obj').rglob('*.dll'))
    run('notargets-pack-'+extension,['pack',native(path),'-c','Release','--no-restore','-o',native(folder/'packed'),'-v:minimal'])
    with zipfile.ZipFile(folder/'packed/NoTargets.Source.Probe.1.0.0.nupkg') as z:
        assert z.read('data/payload.txt')==b'owned data-only probe\n'
        assert not any(n.endswith(('.dll','.exe')) for n in z.namelist())
    run('notargets-clean-'+extension,['msbuild',native(path),'-t:Clean','-p:Configuration=Release','-v:minimal'])

# Restore original transitive/multi-targeting package imports through NuGet.
for label,frameworks in [('multi','<TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>'),('child','<TargetFramework>net8.0</TargetFramework>')]:
    path=project(out/label,'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup>'+frameworks+defaults+'</PropertyGroup><ItemGroup><PackageReference Include="DotNet.ReproducibleBuilds" Version="[1.2.25]"/></ItemGroup>'+capture+'</Project>')
    (path.parent/'Marker.cs').write_text('public class Marker {}\n')
    run(label+'-build',['build',native(path),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
    for tfm in (['net8.0','netstandard2.0'] if label=='multi' else ['net8.0']):
        assert (path.parent/('properties.'+tfm+'.txt')).read_text().strip().endswith('|embedded|true')
parent=project(out/'parent','<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework>'+defaults+'</PropertyGroup><ItemGroup><ProjectReference Include="../child/Check.csproj"/></ItemGroup>'+capture+'</Project>')
run('transitive-build',['build',native(parent),'-c','Release','--configfile',native(config),'-p:UseSharedCompilation=false','-v:minimal'])
assert (parent.parent/'properties.net8.0.txt').read_text().strip().endswith('|embedded|true')

cached=out/'cache/dotnet.reproduciblebuilds/1.2.25'
probe=out/'Policy.proj'
probe.write_text('<Project><Import Project="'+native(cached/'build/DotNet.ReproducibleBuilds.props')+'"/><Import Project="'+native(cached/'build/DotNet.ReproducibleBuilds.targets')+'"/><Target Name="Probe"><WriteLinesToFile File="'+native(out/'policy.txt')+'" Lines="$(ContinuousIntegrationBuild)|$(RepositoryBranch)|$(DebugType)|$(PublishRepositoryUrl)" Overwrite="true"/></Target></Project>')
vectors=json.loads((producer/'upstream-vectors.json').read_text())
ci_count=branch_count=0
for kind in ['ci','branch']:
    for index,case in enumerate(vectors[kind]):
        for override in [False,True]:
            properties=dict(case['properties'])
            if override: properties['ContinuousIntegrationBuild' if kind=='ci' else 'RepositoryBranch']='false' if kind=='ci' else 'explicitly-set'
            args=['msbuild',native(probe),'-t:Probe','-nologo','-v:quiet',*[('-p:'+k+'='+v) for k,v in properties.items()]]
            run(kind+'-'+str(index)+'-'+str(int(override)),args)
            values=(out/'policy.txt').read_text().strip().split('|')
            expected=('false' if kind=='ci' else 'explicitly-set') if override else case['expected']
            assert values[0 if kind=='ci' else 1]==expected,(case,values)
            if kind=='ci':ci_count+=1
            else:branch_count+=1
for key,values in [('DebugType',['embedded','portable']),('PublishRepositoryUrl',['true','false'])]:
    for value in values:
        run('override-'+key+'-'+value,['msbuild',native(probe),'-t:Probe','-nologo','-v:quiet','-p:'+key+'='+value])
        actual=(out/'policy.txt').read_text().strip().split('|')
        assert actual[2 if key=='DebugType' else 3]==value
for version,expected in [('17.7.0',1),('17.8.0',0),('17.9.0',0)]:
    log=run('version-'+version,['msbuild',native(probe),'-t:_ReproducibleBuildsMSBuildVersionCheck','-nologo','-v:minimal','-warnAsError','-p:_ReproducibleBuildsMSBuildVersion='+version],expected)
    assert ('Reproducible builds requires MSBuild' in log)==(expected==1)

for ident,record in source['packages'].items():
    name=ident.lower()+'.'+record['version']+'.nupkg'
    cached=out/'cache'/ident.lower()/record['version']/name
    assert cached.read_bytes()==(feed/name).read_bytes()
    with zipfile.ZipFile(cached) as z:
        for member,digest in record['content_sha256'].items(): assert hashlib.sha256(z.read(member)).hexdigest()==digest
        assert not any(n.lower().endswith(('.dll','.exe','.pdb')) for n in z.namelist())
(out/'results.json').write_text(json.dumps(dict(commands=commands,upstream_CI_vectors_executed=ci_count,upstream_branch_vectors_executed=branch_count,original_MSBuild_version_guard_cases=3,default_and_explicit_policy_overrides=True,actual_embedded_PDB=True,NoTargets_project_extensions=['csproj','msbuildproj'],NoTargets_data_pack_and_clean=True,original_build_MultiTargeting_and_Transitive_imports=True,exact_cached_archive_and_original_content_bytes=True,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original build tools:',ci_count,'CI vectors,',branch_count,'branch vectors, embedded PDB, transitive/multi-targeting imports, NoTargets build/pack/clean and version guards')
