"""Fresh NS2 consumer, metadata gate, isolated old implementation and generated programs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

producer, out = (Path(s).resolve() for s in sys.argv[1:3])
feed = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else producer / 'feed'
assert not out.exists()
out.mkdir()
here = Path(__file__).parent
native = lambda p: subprocess.check_output(['cygpath', '-am', str(p)], text=True).strip()
feeds = list(dict.fromkeys([native(feed), native(Path('/clang64/lib/dotnet/library-packs'))]))
config = out / 'NuGet.config'
config.write_text('<configuration><packageSources><clear/>' + ''.join('<add key="feed' + str(i) + '" value="' + url + '"/>' for i, url in enumerate(feeds)) + '</packageSources></configuration>\n')
env = dict(os.environ, DOTNET_ROOT=native(Path('/clang64/lib/dotnet')), DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet')), DOTNET_CLI_HOME=native(out / 'cli-home'), NUGET_PACKAGES=native(out / 'cache'), MSBuildEnableWorkloadResolver='false', DOTNET_CLI_TELEMETRY_OPTOUT='1')
bridge = out / 'bridge'
bridge.mkdir()
shutil.copy2(here / 'inputs/Bridge.cs', bridge / 'Bridge.cs')
(bridge / 'Bridge.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>netstandard2.0</TargetFramework><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="System.CodeDom" Version="[4.4.0]"/></ItemGroup></Project>\n')
host = out / 'host'
host.mkdir()
for name in ['Api.cs', 'Check.cs']:
    shutil.copy2(here / 'inputs' / name, host / name)
(host / 'Check.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><Nullable>enable</Nullable><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup><ItemGroup><PackageReference Include="Mono.Cecil" Version="[0.11.0]"/></ItemGroup></Project>\n')
commands = []
def run(label, args):
    command = ['/clang64/lib/dotnet/dotnet.exe', *args]
    with (out / (label + '.log')).open('w') as log:
        result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    commands.append(dict(command=command, exit_code=result.returncode))
    assert result.returncode == 0, (label, (out / (label + '.log')).read_text()[-6000:])
for label, project in [('bridge', bridge / 'Bridge.csproj'), ('host', host / 'Check.csproj')]:
    run(label, ['build', native(project), '-c', 'Release', '--configfile', native(config), '-p:UseSharedCompilation=false', '-v:minimal'])
owned = out / 'owned'
owned.mkdir()
shutil.copy2(bridge / 'bin/Release/netstandard2.0/Bridge.dll', owned / 'Bridge.dll')
package = next(p for p in feed.glob('*.nupkg') if p.name.lower() == 'system.codedom.4.4.0.nupkg')
assert (out / 'cache/system.codedom/4.4.0/system.codedom.4.4.0.nupkg').read_bytes() == package.read_bytes()
with zipfile.ZipFile(package) as z:
    data = z.read('lib/netstandard2.0/System.CodeDom.dll')
    (owned / 'reference').mkdir()
    ref_data = z.read('ref/netstandard2.0/System.CodeDom.dll')
    (owned / 'reference/System.CodeDom.dll').write_bytes(ref_data)
    assert (out / 'cache/system.codedom/4.4.0/ref/netstandard2.0/System.CodeDom.dll').read_bytes() == ref_data
bridge_assets = json.loads((bridge / 'obj/project.assets.json').read_text())
assert set(bridge_assets['targets']['.NETStandard,Version=v2.0']['System.CodeDom/4.4.0']['compile']) == {'ref/netstandard2.0/System.CodeDom.dll'}
(owned / 'System.CodeDom.dll').write_bytes(data)
run('run', [native(host / 'bin/Release/net8.0/Check.dll'), native(owned), native(here / 'inputs/published-ns2-metadata.json'), native(producer / 'source-inputs.json'), native(here / 'inputs/published-ns2-reference-metadata.json')])
for extension, language in [('cs', 'CSharp'), ('vb', 'VisualBasic')]:
    folder = out / language
    folder.mkdir()
    shutil.copy2(owned / ('Generated.' + extension), folder / ('Generated.' + extension))
    project = folder / ('Generated.' + ('csproj' if extension == 'cs' else 'vbproj'))
    project.write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><RootNamespace></RootNamespace><TreatWarningsAsErrors>true</TreatWarningsAsErrors><NuGetAudit>false</NuGetAudit></PropertyGroup></Project>\n')
    run('build-' + language, ['build', native(project), '-c', 'Release', '--configfile', native(config), '-p:UseSharedCompilation=false', '-v:minimal'])
    run('run-' + language, [native(folder / 'bin/Release/net8.0/Generated.dll')])
    assert (out / ('run-' + language + '.log')).read_text().splitlines() == ['42', 'héllo Ω "quoted"', 'second']
for project in [bridge, host, out / 'CSharp', out / 'VisualBasic']:
    assert not json.loads((project / 'obj/project.assets.json').read_text()).get('logs')
(out / 'results.json').write_text(json.dumps(dict(commands=commands, original_public_API_entries=1354, original_reference_public_API_entries=1354, original_runtime_reference_table_equal=True, original_compiler_reference_selected_and_verified=True, all_source_resource_values_verified=True, isolated_original_implementation_executed=True, original_NS2_PackageReference_consumer=True, exact_cached_package_sha256=hashlib.sha256(package.read_bytes()).hexdigest(), candidate_DLL_sha256=hashlib.sha256(data).hexdigest(), compiler_reference_DLL_sha256=hashlib.sha256(ref_data).hexdigest(), CSharp_and_VB_generated_source_compiled_and_executed=True, source_SDK8_NET8_test_host=True, other_original_profiles_built=False, full_dependency_goal_complete=False), indent=2) + '\n')
print((out / 'run.log').read_text())
print('PASS CSharp and VisualBasic generated programs compile and execute: 42 and exact Unicode/string escaping')
