"""Validate the original NS2 identity, JSON behaviors and two unchanged upstream regressions."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tarfile
build,out,archive=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir();here=Path(__file__).resolve().parent
native=lambda p:Path(p).resolve().as_posix();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=json.loads((build/'results.json').read_text());assert sha(build/'Newtonsoft.Json.dll')==result['output_sha256']
source_count=0
if archive.suffix=='.cs':upstream=archive.read_bytes()
else:
    for rel,h in result['original_source_sha256'].items():assert sha(build/'source'/rel)==h;source_count+=1
    with tarfile.open(archive) as t:
        m=next(m for m in t if m.name.endswith('/Src/Newtonsoft.Json.Tests/JsonConvertTest.cs'));upstream=t.extractfile(m).read()
text=upstream.decode('utf-8-sig')
methods=[]
for name in ['ToStringEnsureEscapedArrayLength','PopulateObjectWithHeaderComment']:
    match=re.search(r'        public void '+name+r'\(\).*?\n        }',text,re.S);assert match;methods.append(match.group())
fixture='using System;using Newtonsoft.Json; namespace Newtonsoft.Json.Tests { static class Assert {public static void AreEqual(object a,object b){if(!object.Equals(a,b))throw new Exception("upstream regression");}} public class JsonConvertTest { public class PopulateTestObject {public decimal Prop {get;set;}}\n'+'\n'.join(methods)+'\n}}'
(out/'Upstream.cs').write_text(fixture)
source=(here/'Check.cs').read_text().replace('static void Main(){','static void Main(){var fixture=new Newtonsoft.Json.Tests.JsonConvertTest();fixture.ToStringEnsureEscapedArrayLength();fixture.PopulateObjectWithHeaderComment();')
source=source.replace('Console.WriteLine("PASS', 'if(typeof(JsonConvert).Assembly.GetCustomAttributes(typeof(System.Runtime.Versioning.TargetFrameworkAttribute),false) is not System.Runtime.Versioning.TargetFrameworkAttribute[] tfm || tfm[0].FrameworkName!=".NETStandard,Version=v2.0")throw new Exception("original NETStandard2 profile");Console.WriteLine("PASS original NS2 profile, two unchanged upstream regressions;')
(out/'Check.cs').write_text(source);shutil.copyfile(build/'Newtonsoft.Json.dll',out/'Newtonsoft.Json.dll')
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
args=['/nostdlib+','/target:exe','/out:"'+native(out/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs+[out/'Newtonsoft.Json.dll']]+['"'+native(out/n)+'"' for n in ['Check.cs','Upstream.cs']]
(out/'compile.rsp').write_text('\n'.join(args)+'\n');(out/'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[]
for label,cmd in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(out/'compile.rsp')]),('execute',[host,out/'Check.dll'])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=90)
    commands.append(dict(command=[str(p) for p in cmd],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_sources_verified=source_count,upstream_test_source_sha256=hashlib.sha256(upstream).hexdigest(),unchanged_original_regression_methods=methods,original_framework='netstandard2.0',full_upstream_test_suite_run=False,other_original_framework_profiles_built=False),indent=2)+'\n')
print((out/'execute.log').read_text(encoding='utf-8'))
