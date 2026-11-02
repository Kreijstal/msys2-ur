"""Package original data-only build tools without running legacy release tooling."""
from pathlib import Path
import hashlib
import json
import re
import sys
import tarfile
import xml.etree.ElementTree as E

root, out = map(Path, sys.argv[1:])
out.mkdir()
contracts = json.loads((Path(__file__).parent/'contracts.json').read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
records = {}
for ident, contract in contracts.items():
    archive = root/Path(contract['source_archive']).name
    assert sha(archive.read_bytes()) == contract['source_archive_sha256']
    commit = contract.get('source_commit') or contract['repository']['commit']
    with tarfile.open(archive) as t:
        assert t.pax_headers['comment'] == commit
        source = {m.name.partition('/')[2]:t.extractfile(m).read() for m in t if m.isfile()}
    folder = out/ident
    folder.mkdir()
    data = {}
    for name, expected in contract['original_build_file_contract'].items():
        value = source[expected['source_path']]
        assert sha(value) == expected['source_sha256']
        data[name] = value
    if ident == 'DotNet.ReproducibleBuilds':
        project_path = 'src/DotNet.ReproducibleBuilds/DotNet.ReproducibleBuilds.csproj'
        project = E.fromstring(source[project_path])
        assert project.findtext('.//TargetFramework') == 'netstandard1.0'
        declared = {e.get('PackagePath') + (e.get('Include') if e.get('PackagePath').endswith('/') else ''): 'src/'+ident+'/'+e.get('Include') for e in project.iter('None') if e.get('Pack')=='true'}
        assert declared == {n:v['source_path'] for n,v in contract['original_build_file_contract'].items()}
        license_name = 'LICENSE'
        data['README.md'] = source['README.md']
        # Replay original upstream CI/branch precedence vectors through MSBuild.
        cases = {}
        for filename, label in [('ContinuousIntegrationTests.cs','ci'),('SourceLinkTests.cs','branch')]:
            path = 'tests/DotNet.ReproducibleBuilds.Tests/'+filename
            text = source[path].decode('utf-8-sig')
            rows = re.findall(r'\{ new\(\) \{ (.*?) \}(?:, "(.*?)")? \}', text)
            cases[label] = [dict(properties=dict(re.findall(r'\["(.*?)"\] = "(.*?)"', properties)), expected=expected or 'true') for properties,expected in rows]
            assert all(c['properties'] for c in cases[label])
            (folder/filename).write_bytes(source[path])
        assert len(cases['ci']) == 11 and len(cases['branch']) == 45, {k:len(v) for k,v in cases.items()}
        (out/'upstream-vectors.json').write_text(json.dumps(cases,indent=2)+'\n')
    else:
        project_path = 'src/NoTargets/Microsoft.Build.NoTargets.csproj'
        project = E.fromstring(source[project_path])
        assert project.findtext('.//TargetFramework') == 'net472'
        assert project.findtext('.//PackageType') == 'MSBuildSdk'
        license_name = 'LICENSE.txt'
        data['LICENSE.txt'] = source[license_name]
        data['MSBuild-NuGet-Icon.png'] = source['branding/MSBuild-NuGet-Icon.png']
    (folder/'LICENSE').write_bytes(source[license_name])
    (folder/'original-project.xml').write_bytes(source[project_path])
    package = E.Element('package', xmlns='http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd')
    md = E.SubElement(package,'metadata')
    for name, value in dict(id=ident,version=contract['version'],authors='Microsoft and .NET Foundation contributors',description='Original source MSBuild settings for '+ident).items():
        E.SubElement(md,name).text=value
    E.SubElement(md,'license',type='expression').text='MIT'
    E.SubElement(md,'repository',type='git',url=contract['repository']['url'],commit=commit)
    if ident == 'Microsoft.Build.NoTargets':
        types=E.SubElement(md,'packageTypes');E.SubElement(types,'packageType',name='MSBuildSdk')
        dependencies=E.SubElement(md,'dependencies');E.SubElement(dependencies,'group',targetFramework='.NETFramework4.7.2')
        E.SubElement(md,'icon').text='MSBuild-NuGet-Icon.png'
    else:
        E.SubElement(md,'developmentDependency').text='true'
        E.SubElement(md,'readme').text='README.md'
    files=E.SubElement(package,'files')
    for name,value in data.items():
        path=folder/'content'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
        E.SubElement(files,'file',src='content/'+name,target=name)
    E.indent(package);E.ElementTree(package).write(folder/'Data.nuspec',encoding='utf-8',xml_declaration=True)
    # The stub invokes source SDK8 NuGet pack only; it compiles no implementation
    # and does not retarget either original data project's declared profile.
    (folder/'Data.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><EnableDefaultItems>false</EnableDefaultItems><IncludeBuildOutput>false</IncludeBuildOutput><NuspecFile>Data.nuspec</NuspecFile><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>\n')
    records[ident] = dict(version=contract['version'],source_commit=commit,source_archive_sha256=sha(archive.read_bytes()),original_project=project_path,original_project_sha256=sha(source[project_path]),original_project_framework=project.findtext('.//TargetFramework'),content_sha256={n:sha(v) for n,v in data.items()},source_changes=0)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/></packageSources></configuration>\n')
(out/'source-results.json').write_text(json.dumps(dict(packages=records,original_release_toolchain_replayed=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original data-only sources and project declarations',list(records))
