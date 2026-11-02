"""Resume an existing prepared tree after restoring its original NS2 policy."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as E
from policy import write_policy

out = Path(sys.argv[1]).resolve()
source = out / 'roslyn-source'
native = lambda p: subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
inputs = json.loads((out / 'source-inputs.json').read_text())
for data in inputs['projects'].values():
    for rel, digest in data['original_cs'].items():
        assert hashlib.sha256((source / rel).read_bytes()).hexdigest() == digest
policy = out / 'OriginalCompilerPolicy.props'
original_policy_hashes = write_policy(source, policy)
wrappers = json.loads((out / 'wrappers.json').read_text())
for name in wrappers:
    path = out / 'evaluation' / name / 'Evaluate.csproj'
    tree = E.parse(path)
    assert not any(e.get('Project') == native(policy) for e in tree.iter('Import'))
    E.SubElement(tree.getroot(), 'Import', Project=native(policy))
    E.indent(tree)
    tree.write(path, encoding='utf-8', xml_declaration=True)
env = dict(os.environ, DOTNET_CLI_HOME=native(out/'cli-home'), NUGET_PACKAGES=native(out/'cache'),
           DOTNET_CLI_TELEMETRY_OPTOUT='1', MSBuildEnableWorkloadResolver='false')
dotnet = '/clang64/lib/dotnet/dotnet.exe'
subprocess.run([dotnet, 'build', native(out/'evaluation-tool/Build.csproj'), '-c', 'Release',
                '--configfile', native(out/'NuGet.config'), '-p:UseSharedCompilation=false', '-v:minimal'], env=env, check=True)
sdk = native(Path('/clang64/lib/dotnet/sdk/8.0.131'))
env.update(MSBuildSDKsPath=sdk+'/Sdks', MSBUILD_EXE_PATH=sdk+'/MSBuild.dll')
subprocess.run([dotnet, native(out/'evaluation-tool/bin/Release/net8.0/EvaluateRoslynProjects.dll'),
                native(out/'wrappers.json'), native(out/'evaluated-policy.json')], env=env, check=True)
evaluated = json.loads((out/'evaluated-policy.json').read_text())
record = {}
for name, values in evaluated.items():
    props = values['properties']
    assert props['DisableNullableWarnings'] == 'true'
    assert props['Nullable'] == 'enable' and props['Features'] == 'strict'
    assert props['NoWarn'].endswith(';1573;1591;1701;Nullable')
    path = out/name/'Build.csproj'
    tree = E.parse(path)
    group = tree.find('PropertyGroup')
    assert group.findtext('TreatWarningsAsErrors') == 'true'
    for key in ['NoWarn', 'Features', 'Nullable', 'WarningLevel']:
        item = group.find(key)
        if item is None:
            item = E.SubElement(group, key)
        item.text = props[key]
    E.indent(tree)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    record[name] = {k: props[k] for k in ['NoWarn','Features','Nullable','WarningLevel','DisableNullableWarnings','TargetFrameworks']}
(out/'restored-original-policy.json').write_text(json.dumps(dict(original_policy_sha256=original_policy_hashes,
    projects=record, production_source_changes=0, TreatWarningsAsErrors=True), indent=2)+'\n')
print('PASS restored pinned original NS2 compiler policy; WAE retained; production source unchanged')
