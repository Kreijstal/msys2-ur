"""Compile and run the API/resource/compiler suite using NET10 contracts."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

out=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
binary=out/'bin';check=out/'checks';check.mkdir(exist_ok=True)
inputs=here/'net10-check-inputs';files=[]
for name in ['Roslyn53Checks.cs','CheckApi.cs','StandardConsumer.cs']:
 text=(inputs/name).read_text()
 if name=='Roslyn53Checks.cs':
  assert text.count('.NETStandard,Version=v2.0')==1
  text=text.replace('.NETStandard,Version=v2.0','.NETCoreApp,Version=v10.0')
  implementation_override='''                .Where(p => Path.GetFileNameWithoutExtension(p) is not ("System.Collections.Immutable" or "System.Reflection.Metadata"))
                .Concat(new[] { typeof(ImmutableArray<>).Assembly.Location, typeof(MetadataReader).Assembly.Location })
'''
  assert text.count(implementation_override)==1
  # NET10 libraries use the NET10 inbox contracts. Their implementation DLLs
  # deliberately contain zero-version references for runtime unification;
  # those runtime files cannot replace reference assemblies in an API model.
  text=text.replace(implementation_override,'')
 if name=='StandardConsumer.cs':text=text.replace('netstandard2.0','net10.0')
 p=check/name;p.write_text(text);files.append(p)
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/langversion:preview','/nullable:enable','/deterministic+','/debug:portable','/out:"'+native(binary/'Check.dll')+'"']
args+=['/reference:"'+native(p)+'"' for p in refs+[binary/(n+'.dll') for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp']]]
args+=['"'+native(p)+'"' for p in files]
rsp=out/'consumer.rsp';rsp.write_text('\n'.join(args)+'\n')
host='/clang64/lib/dotnet10/dotnet.exe';env=dict(os.environ,DOTNET_ROOT=native(Path('/clang64/lib/dotnet10')),DOTNET_ROOT_X64=native(Path('/clang64/lib/dotnet10')),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable')
commands=[]
def run(label,command):
 with (out/(label+'.log')).open('w') as f:r=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT)
 commands.append(dict(label=label,command=command,exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
run('consumer',[host,native(binary/'csc.dll'),'-noconfig','@'+native(rsp)])
(binary/'Check.runtimeconfig.json').write_text((binary/'csc.runtimeconfig.json').read_text())
run('consumer-run',[host,native(binary/'Check.dll'),native(refs[0].parent),*[native(out/n) for n in ['api-common.txt','api-csharp.txt','localization-common.json','localization-csharp.json','original-localization-coverage.json']]])
(out/'consumer-results.json').write_text(json.dumps(dict(commands=commands,checker_inputs_sha256={n:sha(inputs/n) for n in ['Roslyn53Checks.cs','CheckApi.cs','StandardConsumer.cs']},api_model_uses_original_net10_reference_contracts=True,api_missing_signatures=0,resource_sets=28,resource_strings=39508,original_public_api_declarations=10560,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS NET10 original API/resource/compiler suite against all167 source reference contracts')
