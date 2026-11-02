"""Verify real source NuGet restore and Windows/Linux NET10 runtime asset selection."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, xml.etree.ElementTree as E

prefix, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
native = lambda p: Path(p).resolve().as_posix()
actual = Path(subprocess.check_output(['cygpath', '-am', '/clang64'], text=True).strip())
host = actual / 'lib/dotnet10/dotnet.exe'
tools = actual / 'lib/dotnet10/build-packs/nuget-7.3.0-preview.1.11413-net10-bootstrap/bin'
feed = prefix / 'lib/dotnet/library-packs'
config = out / 'NuGet.config'
config.write_text('<configuration><packageSources><clear/><add key="candidate-source" value="' + native(feed) + '"/></packageSources></configuration>')
p = E.Element('Project')
pg = E.SubElement(p, 'PropertyGroup')
for k, v in dict(TargetFramework='net10.0', TargetFrameworkIdentifier='.NETCoreApp', TargetFrameworkVersion='v10.0',
    TargetFrameworkMoniker='.NETCoreApp,Version=v10.0', RuntimeIdentifiers='win-x64;linux-x64',
    RuntimeIdentifierGraphPath=native(actual / 'lib/dotnet/sdk/8.0.131/PortableRuntimeIdentifierGraph.json'),
    RestoreProjectStyle='PackageReference', MSBuildProjectExtensionsPath=native(out / 'obj') + '/',
    BaseIntermediateOutputPath=native(out / 'obj') + '/', RestoreConfigFile=native(config),
    RestorePackagesPath=native(out / 'cache'), RestoreTaskAssemblyFile=native(tools / 'NuGet.Build.Tasks.dll'),
    TreatWarningsAsErrors='true', NuGetAudit='false').items():
    E.SubElement(pg, k).text = v
name = 'System.Security.Cryptography.Pkcs'
E.SubElement(E.SubElement(p, 'ItemGroup'), 'PackageReference', Include=name, Version='[6.0.4]')
E.SubElement(p.find('ItemGroup'), 'PackageReference', Include='System.Formats.Asn1', Version='[10.0.2]')
E.SubElement(p, 'Import', Project=native(tools / 'NuGet.targets'))
E.ElementTree(p).write(out / 'Consumer.proj', encoding='utf-8', xml_declaration=True)
cmd = [host, tools / 'MSBuild.dll', out / 'Consumer.proj', '-t:Restore', '-nologo', '-v:minimal']
with (out / 'restore.log').open('w', encoding='utf-8') as log:
    r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=dict(os.environ,
        DOTNET_ROOT=native(host.parent), DOTNET_ROOT_X64=native(host.parent), DOTNET_HOST_PATH=native(host),
        DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'cache')), timeout=180)
assert r.returncode == 0, r.returncode
assets = json.loads((out / 'obj/project.assets.json').read_text())
assert set(assets['libraries']) == {name + '/6.0.4', 'System.Formats.Asn1/10.0.2'}
assert not assets.get('logs'), assets.get('logs')
selected = {}
for target, body in assets['targets'].items():
    entry = body[name + '/6.0.4']
    assert set(entry['compile']) == {'ref/net6.0/' + name + '.dll'}, (target, entry)
    expected = ('runtimes/win/lib/net6.0/' if target.endswith('/win-x64') else 'lib/net6.0/') + name + '.dll'
    assert set(entry['runtime']) == {expected}, (target, entry)
    assert entry['dependencies'] == {'System.Formats.Asn1': '6.0.0'}, entry
    asn1 = body['System.Formats.Asn1/10.0.2']
    assert set(asn1['compile']) == {'lib/net10.0/System.Formats.Asn1.dll'}
    assert set(asn1['runtime']) == {'lib/net10.0/System.Formats.Asn1.dll'}
    selected[target] = dict(compile=list(entry['compile']), runtime=list(entry['runtime']), asn1_compile=list(asn1['compile']), asn1_runtime=list(asn1['runtime']))
assert {'net10.0', 'net10.0/win-x64', 'net10.0/linux-x64'} == set(selected), selected
archive = feed / (name.lower() + '.6.0.4.nupkg')
cached = out / 'cache' / name.lower() / '6.0.4' / archive.name
assert archive.read_bytes() == cached.read_bytes()
asn1_archive = feed / 'system.formats.asn1.10.0.2.nupkg'
assert asn1_archive.read_bytes() == (out / 'cache/system.formats.asn1/10.0.2' / asn1_archive.name).read_bytes()
(out / 'results.json').write_text(json.dumps(dict(command=[str(p) for p in cmd], exit_code=0,
    source_archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), selected_assets=selected,
    source_NuGet73_strict_NET10_restore_and_RID_selection_verified=True,
    full_SDK10_pruning_integration_verified=False, full_dependency_goal_complete=False), indent=2) + '\n')
print('PASS strict source NuGet7.3 NET10 restore: reference, Windows implementation and portable Linux fallback assets')
