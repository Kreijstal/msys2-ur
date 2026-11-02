"""Verify package assembly identities against original runtime9 version policy."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as E

prepared,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
policy=E.parse(prepared/'r/src/libraries/NetCoreAppLibrary.props')
inbox=''.join(policy.findtext('.//'+name) or '' for name in ['NetCoreAppLibrary','WindowsDesktopCoreAppLibrary'])
assert 'System.Diagnostics.EventLog;' in inbox
assert 'System.Diagnostics.EventLog.Messages;' not in inbox
versions=E.parse(prepared/'r/eng/Versions.props')
assert [versions.findtext('.//'+name) for name in ['MajorVersion','MinorVersion','PatchVersion']]==['9','0','11']
assert '<AssemblyVersion Condition="\'$(_AssemblyInTargetingPack)\' != \'true\'">$(MajorVersion).$(MinorVersion).0.$(PatchVersion)</AssemblyVersion>' in (prepared/'r/src/libraries/Directory.Build.targets').read_text(encoding='utf-8-sig')
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
native=lambda p:Path(p).resolve().as_posix()
host=prefix/'lib/dotnet10/dotnet.exe'
program=out/'Probe.cs';program.write_text('''using System;using System.IO;using System.Linq;using System.Reflection;
class Probe {
 static void Need(bool value,string label){if(!value)throw new Exception(label);}
 static int Main(string[] args){try {for(int i=0;i<3;i++){
 var a=Assembly.LoadFile(Path.GetFullPath(args[i]));var n=a.GetName();
 Need(n.Version==new Version(i==2?"9.0.0.11":"9.0.0.0"),"Original assembly-version policy");
 Need(Convert.ToHexString(n.GetPublicKeyToken()!).ToLowerInvariant()=="b03f5f7f11d50a3a","Microsoft signing identity");
 var attributes=a.GetCustomAttributesData();
 Need((string)attributes.Single(x=>x.AttributeType.FullName=="System.Runtime.Versioning.TargetFrameworkAttribute").ConstructorArguments[0].Value! == (i==2?".NETStandard,Version=v2.0":".NETCoreApp,Version=v9.0"),"Original framework identity");
 Need((bool)attributes.Single(x=>x.AttributeType.FullName=="System.CLSCompliantAttribute").ConstructorArguments[0].Value!,"CLS policy");
 if(i==2)Need(!attributes.Any(x=>x.AttributeType.FullName=="System.Runtime.Versioning.SupportedOSPlatformAttribute"),"Message DLL clears platform annotation");
 else Need(attributes.Any(x=>x.AttributeType.FullName=="System.Runtime.Versioning.SupportedOSPlatformAttribute"&&(string)x.ConstructorArguments[0].Value! == "windows"),"Original Windows annotation");
 Console.WriteLine("PASS "+n.FullName);
 }return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}''')
refs=prefix/'lib/dotnet/reference-packs/runtime-9.0.11/ref/net9.0'
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/nullable:enable','/out:"'+native(out/'Probe.dll')+'"',*['/reference:"'+native(p)+'"' for p in refs.glob('*.dll')],'"'+native(program)+'"'])+'\n')
commands=[]
for label,command in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,out/'Probe.dll',prepared/'unsupported-build/System.Diagnostics.EventLog.dll',prepared/'build/System.Diagnostics.EventLog.dll',prepared/'messages/System.Diagnostics.EventLog.Messages.dll'])]:
    if label=='execute':(out/'Probe.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net9.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=result.returncode))
    assert result.returncode==0,(label,result.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,original_version_policy_verified=True,all3_assembly_identities_frameworks_cls_and_platforms_passed=True,original_message_version='9.0.0.11',full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original version/signing/framework/CLS/platform identities for all3 source EventLog assets')
