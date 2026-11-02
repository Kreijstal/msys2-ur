"""Execute exact packaged source consumers, unchanged upstream cases and NS2 visibility checks."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

prepared,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
here=Path(__file__).resolve().parent;record=json.loads((prepared/'results.json').read_text());source=prepared/'source'
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe';compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));standard=sorted((prefix/'lib/dotnet/packs/NETStandard.Library.Ref/2.0.3/ref/netstandard2.0').glob('*.dll'))
assert len(refs)==167 and len(standard)==113
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();commands=[]
def run(label,cmd,expected=0,root=host.parent):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(root),DOTNET_ROOT_X64=native(root)),timeout=240)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
    return (out/(label+'.log')).read_text()
def compile(label,files,references,defines,library=False):
    target=out/(label+'.dll');rsp=out/(label+'.rsp')
    args=['/nostdlib+','/warnaserror+','/target:'+('library' if library else 'exe'),'/langversion:14.0','/nullable:'+('disable' if record['version']=='2.0.0' else 'enable'),'/debug:portable','/out:"'+native(target)+'"','/define:'+defines]
    args+=['/reference:"'+native(p)+'"' for p in references]+['"'+native(p)+'"' for p in files]
    rsp.write_text('\n'.join(args)+'\n');run(label+'-compile',[host,compiler,'-noconfig','@'+native(rsp)]);return target
archive=Path(record['archive']);assert sha(archive)==record['archive_sha256']
content=out/'package-content';content.mkdir()
with zipfile.ZipFile(archive) as z:
    assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==record['archive_members']
    for name,expected in record['content_file_sha256'].items():
        p=content/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name));assert sha(p)==expected
selected='net6.0' if record['version']=='2.0.0' else 'net10.0'
production=sorted((content/'contentFiles/cs'/selected/'External/Wcwidth').rglob('*.cs'))
assert production
# The SDK explicitly copies net6.0 source for2.0.0 into its NET10 project. The
# consumer framework defines come from that NET10 target, not the content path.
usings=out/'Usings.cs';usings.write_text('global using System;\nglobal using System.Collections.Generic;\nglobal using System.IO;\nglobal using System.Linq;\nglobal using System.Net.Http;\nglobal using System.Threading;\nglobal using System.Threading.Tasks;\nglobal using Xunit;\nglobal using Shouldly;\n')
tests=sorted((source/'src/Wcwidth.Tests').glob('*.cs'));assert tests
expected_cases=sum(p.read_text(encoding='utf-8-sig').count('[Fact]') for p in tests)
files=[*production,*tests,here/'Assertions.cs',here/'RunTests.cs',usings]
# Source packages contain no binaries. This consumes the original source content
# in a NET10 test application; no original NET7 host/runtime claim is made.
upstream=compile('Upstream',files,refs,'TRACE;NET;NETCOREAPP;NET10_0;NET6_0_OR_GREATER;NET7_0_OR_GREATER;NET8_0_OR_GREATER;NET9_0_OR_GREATER;NET10_0_OR_GREATER')
(out/'Upstream.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
text=run('upstream-execute',[host,upstream]);assert 'PASS '+str(expected_cases)+' unchanged upstream Fact methods' in text,text
print(text,flush=True)
identity=out/'StandardInfo.cs';identity.write_text('[assembly:System.Runtime.Versioning.TargetFramework(".NETStandard,Version=v2.0")]\n')
ns_source=sorted((content/'contentFiles/cs/netstandard2.0/External/Wcwidth').rglob('*.cs'))
loader=compile('LoadScalar',[here/'LoadScalar.cs'],refs,'TRACE')
(out/'LoadScalar.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
ns_cases=[]
standard_usings=out/'StandardUsings.cs'
standard_usings.write_text('global using System;\nglobal using System.Collections.Generic;\nglobal using System.IO;\nglobal using System.Linq;\nglobal using System.Net.Http;\nglobal using System.Threading;\nglobal using System.Threading.Tasks;\n')
for visibility,define in [('public','TRACE;NETSTANDARD;NETSTANDARD2_0'),('internal','TRACE;NETSTANDARD;NETSTANDARD2_0;WCWIDTH_VISIBILITY_INTERNAL')]:
    library=compile('Standard-'+visibility,[*ns_source,here/'ScalarCheck.cs',identity,*([standard_usings] if record['version']=='4.0.1' else [])],standard,define,True)
    text=run('standard-'+visibility+'-execute',[host,loader,library,visibility]);ns_cases.append(text.strip());print(text,flush=True)
(out/'results.json').write_text(json.dumps(dict(commands=commands,archive_sha256=sha(archive),version=record['version'],all_original_source_content_frameworks_and_bytes_verified=True,upstream_Fact_methods_executed=expected_cases,upstream_test_source_changes=0,explicit_assertion_shim_used_instead_of_full_test_runner=True,assertion_negative_control_rejected=True,SDK_original_net6_source_copy_consumed_in_NET10=record['version']=='2.0.0',actual_NETStandard2_consumer_profiles=['public','internal'],NETStandard2_execution=ns_cases,source_tables_regenerated=False,original_committed_generated_sources_preserved=True,original_MinVer_NuGetizer_analyzer_toolchain_replayed=False,all_original_runtime_hosts_tested=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS source package bytes,',expected_cases,'unchanged upstream cases and actual NS2 public/internal consumers')
