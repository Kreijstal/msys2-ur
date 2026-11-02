"""Verify the original NET8 MEF assets are selected and execute real composition."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

prepared,out=(Path(p).resolve() for p in sys.argv[1:3]);feed=Path(sys.argv[3]).resolve() if len(sys.argv)==4 else prepared/'feed'
assert not out.exists();out.mkdir(parents=True)
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
names=[n for n in json.loads((prepared/'source-inputs.json').read_text())['order'] if n.startswith('System.Composition.')]
(out/'Build.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><AssemblyName>Net8CompositionProbe</AssemblyName><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><UseSharedCompilation>false</UseSharedCompilation></PropertyGroup><ItemGroup><Compile Remove="metadata/**/*.cs"/><PackageReference Include="System.Composition" Version="[9.0.0]"/><PackageReference Include="Microsoft.Bcl.AsyncInterfaces" Version="[9.0.0]" Aliases="async9"/></ItemGroup></Project>')
tree=E.parse(out/'Build.csproj')
target=E.SubElement(tree.getroot(),'Target',Name='AliasFrameworkForwardingDestinations',BeforeTargets='CoreCompile')
items=E.SubElement(target,'ItemGroup')
for kind in ['ReferencePath','ReferencePathWithRefAssemblies']:
    item=E.SubElement(items,kind,Update='@('+kind+')',Condition="'%({k}.Filename)' == 'System.Runtime' Or '%({k}.Filename)' == 'netstandard'".format(k=kind))
    E.SubElement(item,'Aliases').text='global,async9'
tree.write(out/'Build.csproj',encoding='utf-8',xml_declaration=True)
(out/'NuGet.config').write_text('<configuration><packageSources><clear/><add key="source" value="'+native(feed)+'"/></packageSources></configuration>')
(out/'Program.cs').write_text('''extern alias async9;
using System;
using System.Collections.Generic;
using System.Composition;
using System.Composition.Hosting;
using System.Composition.Convention;
using System.IO;
using System.Reflection;
using System.Runtime.Versioning;
using System.Threading;
using System.Threading.Tasks;
[Export] public class OwnedExport { public int Value=>42; }
class Program {
 static bool disposed;
 sealed class Resource:IAsyncDisposable {public ValueTask DisposeAsync(){disposed=true;return default;}}
 static async IAsyncEnumerable<int> Values([System.Runtime.CompilerServices.EnumeratorCancellation]CancellationToken token=default) {await Task.Yield();token.ThrowIfCancellationRequested();yield return 42;}
 static async Task<int> Main() {
  if(typeof(async9::System.IAsyncDisposable)!=typeof(IAsyncDisposable) ||
     typeof(async9::System.Collections.Generic.IAsyncEnumerable<int>)!=typeof(IAsyncEnumerable<int>) ||
     typeof(async9::System.Threading.Tasks.Sources.ManualResetValueTaskSourceCore<int>)!=typeof(System.Threading.Tasks.Sources.ManualResetValueTaskSourceCore<int>))throw new Exception("Competing downlevel async type identities");
  foreach(Type t in new[]{typeof(ExportAttribute),typeof(CompositionContext),typeof(CompositionHost),typeof(ConventionBuilder),typeof(ContainerConfiguration)}) {
   if(t.Assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName!=".NETCoreApp,Version=v8.0")throw new Exception("Wrong MEF target: "+t);
   if(Path.GetDirectoryName(Path.GetFullPath(t.Assembly.Location))!=Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar))throw new Exception("Foreign MEF implementation: "+t.Assembly.Location);
  }
  using var container=new ContainerConfiguration().WithPart<OwnedExport>().CreateContainer();
  if(container.GetExport<OwnedExport>().Value!=42)throw new Exception("NET8 composition failed");
  int total=0;
  await using(var resource=new Resource()) {await foreach(var value in Values().ConfigureAwait(false))total+=value;}
  if(total!=42 || !disposed)throw new Exception("Async iteration/disposal failed");
  bool cancelled=false;
  try {await foreach(var value in Values().WithCancellation(new CancellationToken(true)))throw new Exception("Cancellation was ignored");}catch(OperationCanceledException){cancelled=true;}
  if(!cancelled)throw new Exception("Async iterator cancellation failed");
  Console.WriteLine("PASS original NET8 MEF composition and Standard2.1 forwarder: shared alias/runtime types, async iteration/disposal/cancellation");return 0;
 }
}
''')
env=dict(os.environ,DOTNET_CLI_HOME=native(out/'cli-home'),NUGET_PACKAGES=native(out/'cache'),DOTNET_CLI_TELEMETRY_OPTOUT='1',MSBuildEnableWorkloadResolver='false')
dotnet='/clang64/lib/dotnet/dotnet.exe'
with (out/'build.log').open('w') as log:subprocess.run([dotnet,'build',native(out/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-p:UseSharedCompilation=false','-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
assets=json.loads((out/'obj/project.assets.json').read_text());assert set(assets['libraries'])=={n+'/9.0.0' for n in names+['System.Composition','Microsoft.Bcl.AsyncInterfaces']}
target=next(iter(assets['targets'].values()));hashes={}
for name in names:
    selected=target[name+'/9.0.0'];assert set(selected['compile'])=={'lib/net8.0/'+name+'.dll'},(name,selected)
    package=feed/(name.lower()+'.9.0.0.nupkg')
    if not package.exists():package=feed/(name+'.9.0.0.nupkg')
    with zipfile.ZipFile(package) as z:
        data=z.read('lib/net8.0/'+name+'.dll')
        assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==data
        assert (prepared/'baseline-net8'/name/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==data
    assert (out/'cache'/name.lower()/'9.0.0'/(name.lower()+'.9.0.0.nupkg')).read_bytes()==package.read_bytes()
    hashes[name]=hashlib.sha256(data).hexdigest()
name='Microsoft.Bcl.AsyncInterfaces';asset='lib/netstandard2.1/'+name+'.dll'
selected=target[name+'/9.0.0'];assert set(selected['compile'])==set(selected['runtime'])=={asset},selected
assert not selected.get('dependencies'),selected
package=feed/(name.lower()+'.9.0.0.nupkg')
if not package.exists():package=feed/(name+'.9.0.0.nupkg')
with zipfile.ZipFile(package) as z:
    data=z.read(asset)
    assert (out/'bin/Release/net8.0'/(name+'.dll')).read_bytes()==data
    assert (prepared/'forwarder-netstandard21'/name/'bin/Release/netstandard2.1'/(name+'.dll')).read_bytes()==data
assert (out/'cache'/name.lower()/'9.0.0'/(name.lower()+'.9.0.0.nupkg')).read_bytes()==package.read_bytes()
forwarder_sha256=hashlib.sha256(data).hexdigest()
refs=(prepared/'forwarder-netstandard21'/name/'obj/Release/netstandard2.1/ReferencePath.txt').read_text(encoding='utf-8-sig').splitlines()
assert len(refs)==121 and all('/packs/NETStandard.Library.Ref/2.1.0/ref/netstandard2.1/' in p.replace('\\','/') for p in refs)
for ref in refs:
    filename=ref.replace('\\','/').rsplit('/',1)[-1]
    assert (Path('/clang64/lib/dotnet/packs/NETStandard.Library.Ref/2.1.0/ref/netstandard2.1')/filename).is_file()
with (out/'run.log').open('w') as log:subprocess.run([dotnet,native(out/'bin/Release/net8.0/Net8CompositionProbe.dll')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
expected=[]
source=prepared/'runtime-source/src/libraries/Microsoft.Bcl.AsyncInterfaces/src/Microsoft.Bcl.AsyncInterfaces.Forwards.cs'
for value in re.findall(r'TypeForwardedTo\(typeof\((.*?)\)\)',source.read_text()):expected.append(re.sub(r'<(,*)>',lambda m:'`'+str(len(m[1])+1),value))
(out/'expected-forwards.json').write_text(json.dumps(expected)+'\n')
metadata=out/'metadata';metadata.mkdir()
here=Path(__file__).resolve().parent
(metadata/'Build.csproj').write_text('<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0</TargetFramework><OutputType>Exe</OutputType><UseAppHost>false</UseAppHost><EnableDefaultItems>false</EnableDefaultItems><EnableNETAnalyzers>false</EnableNETAnalyzers><NuGetAudit>false</NuGetAudit><UseSharedCompilation>false</UseSharedCompilation></PropertyGroup><ItemGroup><Compile Include="'+native(here/'inputs/CheckForwarder21.cs')+'"/></ItemGroup></Project>')
with (out/'metadata-build.log').open('w') as log:subprocess.run([dotnet,'build',native(metadata/'Build.csproj'),'-c','Release','--configfile',native(out/'NuGet.config'),'-v:minimal'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
with (out/'metadata-results.json').open('w') as log:subprocess.run([dotnet,native(metadata/'bin/Release/net8.0/Build.dll'),native(out/'bin/Release/net8.0/Microsoft.Bcl.AsyncInterfaces.dll'),native(out/'expected-forwards.json')],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
(out/'results.json').write_text(json.dumps(dict(original_net8_mef_assets_verified=5,source_assembly_sha256=hashes,fresh_cache_matches_source_feed=True,real_net8_composition_execution_passed=True,original_standard21_forwarder_sha256=forwarder_sha256,original_standard21_reference_paths=121,forwarder_runtime=json.loads((out/'metadata-results.json').read_text()),async_iteration_disposal_cancellation_passed=True,no_downlevel_tasks_dependency_selected=True,installed_feed=len(sys.argv)==4,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original NET8 MEF and Standard2.1 forwarder NuGet selection, exact source bytes, complete forwards and runtime type unification')
