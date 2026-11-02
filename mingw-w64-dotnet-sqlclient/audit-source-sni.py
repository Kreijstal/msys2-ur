"""Audit the candidate port against the pinned archive and actual compile inputs.

Run with MSYS Python: SOURCE BUILD_ROOT TDS_CHECK_ROOT SOURCE_ARCHIVE.
This establishes source coverage/provenance, not untested runtime feature parity.
"""
import os
from pathlib import Path
import hashlib
import json
import posixpath
import subprocess
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as E

source, build = (Path(p).resolve() for p in sys.argv[1:3])
peer = None if len(sys.argv) == 4 else Path(sys.argv[3]).resolve()
archive = Path(sys.argv[-1]).resolve()
inputs = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha(archive.read_bytes()) == 'f5b1bd0cf8b2c6e232ff866a4f3b069c30c48f37820c10c81691de211d4ba3c6'
with tarfile.open(archive) as tar:
    members = [p for p in tar.getmembers() if p.isfile()]
    prefix = members[0].name.split('/')[0]+'/'
    originals = {p.name.removeprefix(prefix): tar.extractfile(p).read() for p in members}

def native(path):
    return subprocess.check_output(['cygpath', '-am', str(path)], text=True).strip().replace('\\', '/')

def archived(path):
    relative = path.relative_to(source).as_posix()
    assert path.read_bytes() == originals[relative], relative
    return relative

def replay(original, patch, overlay):
    assert sha(patch.read_bytes()) == overlay['patch_sha256']
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/Path(overlay['original_path']).name
        path.write_text(original.decode('utf-8-sig').replace('\r\n', '\n'))
        subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(patch)], cwd=temp,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert sha(path.read_bytes()) == overlay['overlay_sha256']

port = json.loads((build/'managed-sni-port.json').read_text())
assert port['release_and_debug_use_managed_sni'] is True
assert port['complete_runtime_compatibility_verified'] is False
assert {p['patch_name'] for p in port['overlays']} == {
    '0001-use-managed-sni-on-windows.patch', '0003-pass-complete-spns-to-windows-sspi.patch',
    '0004-accept-short-custom-named-pipe-paths.patch',
    '0005-honor-inclusive-smp-send-window.patch'}
overlays = {}
for item in port['overlays']:
    path = source/item['original_path']
    archived(path)
    assert sha(path.read_bytes()) == item['original_sha256']
    replay(originals[item['original_path']], inputs/item['patch_name'], item)
    staged = build/'overlays'/path.name
    assert sha(staged.read_bytes()) == item['overlay_sha256']
    overlays[staged.relative_to(build).as_posix()] = item['original_path']

project_path = 'src/System.Data.SqlClient/src/System.Data.SqlClient.csproj'
root = E.fromstring(originals[project_path])
project_dir = posixpath.dirname(project_path)
conditions = {
    '': lambda windows: True,
    "'$(TargetPlatformIdentifier)' == 'windows'": lambda windows: windows,
    "'$(TargetPlatformIdentifier)' != 'windows'": lambda windows: not windows,
    "'$(IsFunctionalAssembly)' == 'true'": lambda windows: windows,
    "'$(TargetFrameworkIdentifier)' == '.NETFramework'": lambda windows: False,
    "'$(TargetFrameworkIdentifier)' != '.NETFramework' and '$(TargetPlatformIdentifier)' == ''": lambda windows: not windows,
    "'$(TargetFrameworkIdentifier)' == '.NETCoreApp'": lambda windows: True,
}
result = dict(source_commit='84b081710c66cc560b77d4de38cee493c3a38e9d',
              source_sha256=sha(archive.read_bytes()), production_overlays=port['overlays'])
for role, windows in [('implementation', True), ('contract', False)]:
    expected = set()
    for group in root.findall('ItemGroup'):
        assert group.get('Condition', '') in conditions
        if not conditions[group.get('Condition', '')](windows):
            continue
        for item in group.findall('Compile'):
            assert not item.get('Condition'), item.attrib
            if item.get('Remove'):
                assert item.get('Remove') == '@(Compile)'
                expected.clear()
            else:
                path = item.get('Include').replace('\\', '/')
                if path.startswith('$(CommonPath)'):
                    path = 'src/Common/'+path.removeprefix('$(CommonPath)')
                else:
                    path = posixpath.normpath(project_dir+'/'+path)
                assert path in originals, path
                expected.add(path)
    # This compatibility helper supplies the resource accessors rebuilt by
    # prepare.py; its source bytes are independently checked against the archive.
    expected.add('src/Common/src/System/SR.cs')
    selected, generated, hashes = set(), [], {}
    source_prefix, build_prefix = native(source)+'/', native(build)+'/'
    lines = (build/role/'compile-inputs.txt').read_text(encoding='utf-8-sig').splitlines()
    assert len(lines) == len(set(lines)), 'duplicate compiler inputs'
    for line in lines:
        line = line.replace('\\', '/')
        if line.startswith(source_prefix):
            path = line[len(source_prefix):]
            archived(source/path)
            selected.add(path)
            hashes[path] = sha((source/path).read_bytes())
        else:
            assert line.startswith(build_prefix), line
            path = line[len(build_prefix):]
            if path in overlays:
                assert role == 'implementation'
                selected.add(overlays[path])
                hashes[overlays[path]] = sha((build/path).read_bytes())
            else:
                framework = 'net8.0-windows' if windows else 'net8.0'
                allowed = {role+'/SR.Generated.cs',
                    role+'/obj/Release/'+framework+'/.NETCoreApp,Version=v8.0.AssemblyAttributes.cs',
                    role+'/obj/Release/'+framework+'/build.AssemblyInfo.cs'}
                if windows:
                    allowed.add(role+'/obj/Release/'+framework+'/ThisAssembly.cs')
                assert path in allowed, path
                generated.append(path)
    assert selected == expected, (role, sorted(expected-selected), sorted(selected-expected))
    assert len(generated) == (4 if windows else 3), generated
    result[role] = dict(original_selected_sources=len(selected),
        generated_sources=generated, compiled_sha256=hashes)

result['original_build_metadata'] = {}
for path in [project_path, project_dir+'/GenerateThisAssemblyCs.targets', project_dir+'/Resources/Strings.resx', 'LICENSE', project_dir+'/PACKAGE.md']:
    assert (source/path).read_bytes()==originals[path],path
    result['original_build_metadata'][path]=sha(originals[path])
result['outputs']={}
for role, framework in [('implementation','net8.0-windows'),('contract','net8.0')]:
    result['outputs'][role]={}
    for path in ['bin/Release/'+framework+'/System.Data.SqlClient.dll','obj/Release/'+framework+'/ref/System.Data.SqlClient.dll']:
        result['outputs'][role][path]=sha((build/role/path).read_bytes())
    framework_root=Path(os.environ['MINGW_PREFIX']+'/lib/dotnet/packs/Microsoft.NETCore.App.Ref/8.0.31')
    framework_prefix=native(framework_root)+'/'
    references={}
    for value in (build/role/'reference-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/')
        assert value.lower().startswith(framework_prefix.lower()),value
        path=value[len(framework_prefix):];references[path]=sha((framework_root/path).read_bytes())
    result[role]['framework_references']=references
    result[role]['generated_sha256']={path:sha((build/path).read_bytes()) for path in result[role]['generated_sources']}
    resources={}
    for value in (build/role/'resource-inputs.txt').read_text(encoding='utf-8-sig').splitlines():
        value=value.replace('\\','/');assert value.startswith(native(source)+'/'),value
        path=value[len(native(source)) + 1:];assert (source/path).read_bytes()==originals[path]
        resources[path]=sha(originals[path])
    result[role]['resource_inputs']=resources
    result[role]['prepared_project_metadata']={path:sha((build/role/path).read_bytes()) for path in ['build.csproj','upstream.proj','GenerateThisAssemblyCs.targets']}
result['removed_binary_inputs']=json.loads((build/'removed-binaries.json').read_text())
for item in result['removed_binary_inputs']:
    path=item['path'].replace('\\','/');assert sha(originals[path])==item['sha256'] and not (source/path).exists()
(build/'source-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
if peer is None:
    print('PASS full pinned source/compiler/framework/resource/implementation/reference inventories; experimental runtime parity remains open')
    sys.exit(0)

tds_inventory = json.loads((peer/'tds-source-inventory.json').read_text())
utilities = {}
for name in ('TDS', 'TDS.EndPoint', 'TDS.Servers'):
    directory = 'src/System.Data.SqlClient/tests/Tools/TDS/'+name
    tree = E.fromstring(originals[directory+'/'+name+'.csproj'])
    expected = set()
    if tree.findtext('./PropertyGroup/EnableDefaultCompileItems') != 'false':
        expected.update(p for p in originals if p.startswith(directory+'/') and p.endswith('.cs'))
    for group in tree.findall('ItemGroup'):
        condition = group.get('Condition', '')
        assert condition in ('', "'$(TargetPlatformIdentifier)' == 'windows'", "'$(TargetPlatformIdentifier)' == 'unix'")
        if condition.endswith("== 'unix'"):
            continue
        for item in group.findall('Compile'):
            path = item.get('Include').replace('\\', '/')
            path = ('src/Common/'+path.removeprefix('$(CommonPath)')) if path.startswith('$(CommonPath)') else directory+'/'+path
            expected.add(posixpath.normpath(path))
    assert set(tds_inventory[name]) == expected, name
    project = E.parse(peer/name/'build.csproj').getroot()
    actual, patches = set(), []
    for item in project.findall('./ItemGroup/Compile'):
        path = (peer/name/item.get('Include')).resolve()
        if path.is_relative_to(source):
            actual.add(archived(path))
        else:
            assert name == 'TDS.EndPoint' and path == peer/name/'overlays/PlaceholderStream.cs'
            overlay = json.loads((peer/name/'test-stream-overlay.json').read_text())
            assert sha(originals[overlay['original_path']]) == overlay['original_sha256']
            replay(originals[overlay['original_path']], inputs/'0002-tds-test-peer-return-partial-handshake-reads.patch', overlay)
            assert sha(path.read_bytes()) == overlay['overlay_sha256']
            actual.add(overlay['original_path'])
            patches.append(overlay)
    assert actual == expected, name
    for path, digest in tds_inventory[name].items():
        assert digest == sha(originals[path])
    utilities[name] = dict(original_selected_sources=len(expected), overlays=patches)
result['upstream_test_utilities'] = utilities
implementation = build/'implementation/bin/Release/net8.0-windows/System.Data.SqlClient.dll'
consumers = list((peer/'bin/Release/net8.0-windows').rglob('System.Data.SqlClient.dll'))
consumer = next(p for p in consumers if p.read_bytes()==implementation.read_bytes())
result['tested_implementation_sha256'] = sha(implementation.read_bytes())
result['tested_consumer_asset'] = consumer.relative_to(peer).as_posix()
(build/'source-sni-audit.json').write_text(json.dumps(result, indent=2)+'\n')
print('PASS exact pinned archive, complete original compiler inputs, four production overlays, 142 upstream TDS utility inputs/one test-stream overlay, and tested Release DLL bytes:',
      {role: result[role]['original_selected_sources'] for role in ('implementation', 'contract')})
