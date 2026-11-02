"""Exercise the freshly built original NET10 csc on the source NET10 host."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

build=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
assert not out.exists();out.mkdir(parents=True)
status=json.loads((build/'build-status.json').read_text())
assert set(status)=={'Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
host=Path('/clang64/lib/dotnet10/dotnet.exe')
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_ROLL_FORWARD='Disable')
for name,record in status.items():assert sha(build/'bin'/(name+'.dll'))==record['output_sha256'],name
commands=[]
def run(label,args,expected=0):
 result=subprocess.run([str(host),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (out/(label+'.log')).write_text(result.stdout)
 commands.append(dict(label=label,command=[str(host),*args],exit_code=result.returncode))
 assert result.returncode==expected,(label,result.returncode,result.stdout)
 return result.stdout
version=run('version',[native(build/'bin/csc.dll'),'-noconfig','-version'])
assert version.startswith('5.3.'),version
source=out/'CSharp14 λ.cs'
source.write_text('''using System;
using System.Reflection;
using System.Runtime.Versioning;
using System.Text.RegularExpressions;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
public static class Extensions { extension(string text) { public int TwiceLength => text.Length * 2; } }
public partial class Program {
 [GeneratedRegex("a+")] private static partial Regex MatchA();
 public static int Main() {
  if ("source".TwiceLength != 12 || !MatchA().IsMatch("caaa")) return 1;
  if (Environment.Version.Major != 10) return 2;
  foreach (var assembly in new[] { typeof(Compilation).Assembly, typeof(CSharpCompilation).Assembly }) {
   if (assembly.GetCustomAttribute<TargetFrameworkAttribute>()?.FrameworkName != ".NETCoreApp,Version=v10.0") return 3;
   if (assembly.GetName().Version?.Major != 5 || assembly.GetName().Version?.Minor != 3) return 4;
   Console.WriteLine(assembly.FullName + "; " + assembly.Location);
  }
  Console.WriteLine("PASS original NET10 compiler, CSharp14 extension property, generated regex and NET10 library identities");
  return 0;
 }
}
''',encoding='utf-8')
refs=sorted(Path('/clang64/lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
refs += [build/'bin'/name for name in ['Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll']]
generator=Path('/clang64/lib/dotnet/generator-packs/runtime-10.0.5/analyzers/dotnet/cs/System.Text.RegularExpressions.Generator.dll')
(out/'generated').mkdir()
args=['/nostdlib+','/target:exe','/langversion:14','/deterministic+','/debug:portable','/out:"'+native(out/'probe.dll')+'"','/analyzer:"'+native(generator)+'"','/generatedfilesout:"'+native(out/'generated')+'"']
args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(source)+'"']
rsp=out/'compiler λ.rsp';rsp.write_text('\n'.join(args)+'\n',encoding='utf-8')
run('compile',[native(build/'bin/csc.dll'),'-noconfig','@'+native(rsp)])
import shutil
for name in ['Microsoft.CodeAnalysis.dll','Microsoft.CodeAnalysis.CSharp.dll']:shutil.copyfile(build/'bin'/name,out/name)
(out/'probe.runtimeconfig.json').write_text((build/'bin/csc.runtimeconfig.json').read_text())
execution=run('execute',[native(out/'probe.dll')]);assert 'PASS original NET10 compiler' in execution
bad=out/'bad.cs';bad.write_text('class Bad { static void Main() { MissingSymbol(); } }\n')
negative_args=[a for a in args if not a.startswith(('/out:','/analyzer:','/generatedfilesout:'))][:-1]+['/out:"'+native(out/'bad.dll')+'"','"'+native(bad)+'"']
negative=out/'negative.rsp';negative.write_text('\n'.join(negative_args)+'\n')
diagnostic=run('negative',[native(build/'bin/csc.dll'),'-noconfig','@'+native(negative)],1)
assert 'CS0103' in diagnostic and not (out/'bad.dll').exists()
assert list((out/'generated').rglob('RegexGenerator.g.cs'))
record=dict(commands=commands,actual_compiler_outputs_sha256={n:r['output_sha256'] for n,r in status.items()},regex_generator_sha256=sha(generator),probe_sha256=sha(out/'probe.dll'),real_net10_cli_execution_passed=True,csharp14_and_source_regex_generation_passed=True,invalid_source_exit_code=1,original_cli_profile_complete=False,full_sdk10_built=False,full_dependency_goal_complete=False)
(out/'results.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS source NET10 csc: version, Unicode response file, CSharp14, regex generation, NET10 identities and invalid-source exit1')
