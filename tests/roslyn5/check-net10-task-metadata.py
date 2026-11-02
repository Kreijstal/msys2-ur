"""Check source Roslyn task identity, original MSBuild references and resources."""
from pathlib import Path
import json,os,subprocess,sys,xml.etree.ElementTree as E

task,resx,stage,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
check=out/'Check.cs';check.write_text('''using System;using System.IO;using System.Linq;using System.Reflection;using System.Resources;using System.Runtime.Loader;using System.Runtime.Versioning;using System.Xml;using System.Xml.Linq;
class Check { static void Main(string[] args) {
 AssemblyLoadContext.Default.Resolving += (c,n) => {string p=Path.Combine(args[2],n.Name+".dll");return File.Exists(p)?c.LoadFromAssemblyPath(p):null;};
 var a=AssemblyLoadContext.Default.LoadFromAssemblyPath(args[0]);
 var name=a.GetName();
 if(name.Version.ToString()!="5.3.0.0"||Convert.ToHexString(name.GetPublicKeyToken()).ToLowerInvariant()!="31bf3856ad364e35")throw new Exception("identity");
 if(a.GetCustomAttribute<TargetFrameworkAttribute>().FrameworkName!=".NETCoreApp,Version=v10.0")throw new Exception("original NET10 target");
 var build=a.GetReferencedAssemblies().Where(n=>n.Name.StartsWith("Microsoft.Build")).ToArray();
 if(build.Length<2 || build.Any(n=>n.Version.ToString()!="15.1.0.0" || Convert.ToHexString(n.GetPublicKeyToken()).ToLowerInvariant()!="b03f5f7f11d50a3a"))throw new Exception("MSBuild references");
 foreach(string type in new[]{"Csc","Vbc","CopyRefAssembly","GenerateMSBuildEditorConfig","MapSourceRoots"})
  if(a.GetType("Microsoft.CodeAnalysis.BuildTasks."+type)==null)throw new Exception("missing task "+type);
 using var reader=new XmlTextReader(args[1]);reader.WhitespaceHandling=WhitespaceHandling.All;
 var doc=XDocument.Load(reader,LoadOptions.PreserveWhitespace);
 using var stream=a.GetManifestResourceStream("Microsoft.CodeAnalysis.BuildTasks.ErrorString.resources");
 using var set=new ResourceSet(stream);int count=0;
 foreach(var n in doc.Root.Elements("data")) {
  string key=n.Attribute("name").Value, expected=n.Element("value").Value;
  if(set.GetString(key)!=expected)throw new Exception("resource "+key);
  count++;
 }
 Console.WriteLine("PASS task identity,original NET10 target,MSBuild references,five task types and "+count+" exact original resource strings");
}}''')
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
rsp=out/'compile.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/out:"'+native(out/'Check.dll')+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(check)+'"'])+'\n')
(out/'Check.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent));commands=[]
for label,command in [('compile',[host,prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll','-noconfig','@'+native(rsp)]),('execute',[host,out/'Check.dll',task,resx,stage])]:
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
(out/'results.json').write_text(json.dumps(dict(commands=commands,all_original_neutral_resource_strings_verified=len(list(E.parse(resx).iter('data'))),identity_original_target_and_msbuild_references_verified=True,full_dependency_goal_complete=False),indent=2)+'\n')
print((out/'execute.log').read_text(encoding='utf-8').strip())
