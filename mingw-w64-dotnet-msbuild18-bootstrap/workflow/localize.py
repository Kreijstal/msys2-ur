"""Build original MSBuild NET10 XLF satellites and verify every resource value."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as E

plan,build,stage,out=(Path(p).resolve() for p in sys.argv[1:5]);resume=sys.argv[5:]==['--resume-completed-satellites']
if resume:
    assert out.is_dir()
    assert len(list((out/'bin').glob('*/*.resources.dll')))==53
else:out.mkdir()
source=Path(json.loads((plan/'source-inputs.json').read_text())['source_root']).resolve()
model=json.loads((plan/'evaluated.json').read_text())
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host=prefix/'lib/dotnet10/dotnet.exe';host8=prefix/'lib/dotnet/dotnet.exe'
native=lambda p:Path(p).resolve().as_posix()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
refs=sorted((prefix/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
compiler=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host))
binary=out/'bin'
if not resume:shutil.copytree(stage,binary)
else:
    for p in stage.glob('*.dll'):assert sha(p)==sha(binary/p.name),p.name
commands=[]
def run(label,command,environment=env):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(x) for x in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
def compile(label,output,files,extras=()):
    args=['/nostdlib+','/target:library','/deterministic+','/out:"'+native(output)+'"',*extras]
    args+=['/reference:"'+native(p)+'"' for p in refs]+['"'+native(p)+'"' for p in files]
    rsp=out/(label+'.rsp');rsp.write_text('\n'.join(args)+'\n')
    run(label,[host,compiler,'-noconfig','@'+native(rsp)])
ns={'x':'urn:oasis:names:tc:xliff:document:1.2'}
originals={};resources=[];groups={}
project=E.Element('Project');E.SubElement(project,'UsingTask',TaskName='GenerateResource',AssemblyFile=native(host8.parent/'sdk/8.0.131/Microsoft.Build.Tasks.Core.dll'));target=E.SubElement(project,'Target',Name='Generate')
for name,entry in model.items():
    for item in entry['items']['EmbeddedResource']:
        resx=Path(item['full_path']).resolve()
        if resx.suffix!='.resx':continue
        logical=item['metadata']['LogicalName'].removesuffix('.resources')
        originals[resx.relative_to(source).as_posix()]=sha(resx)
        for xlf in sorted((resx.parent/'xlf').glob(resx.stem+'.*.xlf')):
            originals[xlf.relative_to(source).as_posix()]=sha(xlf)
            tree=E.parse(xlf);culture=tree.find('x:file',ns).get('target-language');assert culture
            translations={u.get('id'):''.join(u.find('x:target',ns).itertext()) for u in tree.findall('.//x:trans-unit',ns) if u.find('x:target',ns) is not None}
            localized=E.parse(resx);values={}
            for node in localized.iter('data'):
                key=node.get('name');value=node.find('value');assert value is not None
                if key in translations:value.text=translations[key]
                # ElementTree's filename writer uses Windows text newlines.
                # MSBuildResXReader uses XmlTextReader with normalization off,
                # so those CRLFs are part of the compiled resource strings.
                values[key]=(value.text or '').replace('\n',os.linesep)
            folder=out/'resources'/name/culture;folder.mkdir(parents=True,exist_ok=True)
            generated=folder/(logical+'.'+culture+'.resx');localized.write(generated,encoding='utf-8',xml_declaration=True)
            resource=generated.with_suffix('.resources')
            E.SubElement(target,'GenerateResource',Sources=native(generated),OutputResources=native(resource),ExecuteAsTool='false')
            groups.setdefault((name,culture),[]).append((resource,logical+'.'+culture+'.resources'))
            resources.append(dict(assembly=name,resource=logical,culture=culture,strings=values))
E.ElementTree(project).write(out/'Resources.proj',encoding='utf-8',xml_declaration=True)
env8=dict(os.environ,DOTNET_ROOT=native(host8.parent),DOTNET_ROOT_X64=native(host8.parent))
if not resume:run('resources',[host8,'msbuild',out/'Resources.proj','-nologo','-t:Generate'],env8)
satellites={}
for (name,culture),items in groups.items():
    folder=out/'resources'/name/culture;info=folder/'AssemblyInfo.cs'
    info.write_text('[assembly:System.Reflection.AssemblyVersion("15.1.0.0")]\n[assembly:System.Reflection.AssemblyFileVersion("18.3.0.11413")]\n[assembly:System.Reflection.AssemblyCulture('+json.dumps(culture)+')]\n')
    destination=binary/culture/(name+'.resources.dll');destination.parent.mkdir(exist_ok=True)
    if not resume:compile('satellite-'+name+'-'+culture,destination,[info],['/publicsign+','/keyfile:"'+native(build/'Microsoft.public.snk')+'"']+['/resource:"'+native(p)+'",'+logical for p,logical in items])
    satellites[destination.relative_to(binary).as_posix()]=sha(destination)
assert len(satellites)==53,(len(satellites),list(groups))
(out/'expected.json').write_text(json.dumps(resources,ensure_ascii=False))
check=out/'Check.cs'
check.write_text('''using System;using System.IO;using System.Reflection;using System.Resources;using System.Globalization;using System.Text.Json;
class Check {static void Main(string[] args) {
 int count=0;using var doc=JsonDocument.Parse(File.ReadAllText(args[0]));
 foreach(var r in doc.RootElement.EnumerateArray()) {
  string name=r.GetProperty("assembly").GetString(), culture=r.GetProperty("culture").GetString();
  var a=Assembly.LoadFrom(Path.Combine(AppContext.BaseDirectory,name+".dll"));
  var s=a.GetSatelliteAssembly(CultureInfo.GetCultureInfo(culture));
  if(s.GetName().Version.ToString()!="15.1.0.0" || Convert.ToHexString(s.GetName().GetPublicKeyToken()).ToLowerInvariant()!="b03f5f7f11d50a3a")throw new Exception("satellite identity");
  var rm=new ResourceManager(r.GetProperty("resource").GetString(),a);
  using var stream=s.GetManifestResourceStream(r.GetProperty("resource").GetString()+"."+culture+".resources");
  if(stream==null)throw new Exception("missing exact satellite resource stream");
  using var set=new ResourceSet(stream);
  // NeutralResourcesLanguage("en") routes English requests to the main
  // assembly. Inspect the original English XLF satellite directly instead.
  var resolved=culture=="en" ? null : rm.GetResourceSet(CultureInfo.GetCultureInfo(culture),true,false);
  if(culture!="en" && resolved==null)throw new Exception("missing resolved resource set");
  foreach(var v in r.GetProperty("strings").EnumerateObject()) {
   if(set.GetString(v.Name)!=v.Value.GetString())throw new Exception(name+"/"+culture+"/"+v.Name+" expected="+JsonSerializer.Serialize(v.Value.GetString())+" actual="+JsonSerializer.Serialize(set.GetString(v.Name)));
   if(resolved!=null && resolved.GetString(v.Name)!=v.Value.GetString())throw new Exception("ResourceManager mismatch "+name+"/"+culture+"/"+v.Name);
   count++;
  }
 }
 Console.WriteLine("PASS all original XLF resource values: "+count);
}}''')
checker=binary/'Check.dll';compile('check-compile',checker,[check],['/target:exe'])
(binary/'Check.runtimeconfig.json').write_text((binary/'MSBuild.runtimeconfig.json').read_text())
run('check-resources',[host,checker,out/'expected.json'])
run('check-german-help',[host,binary/'MSBuild.dll','-help','-nologo','-noautoresponse'],dict(env,DOTNET_CLI_UI_LANGUAGE='de',VSLANG='1031'))
help_text=(out/'check-german-help.log').read_text(encoding='utf-8')
assert 'Syntax' in help_text and ('Projekt' in help_text or 'Optionen' in help_text),help_text[:1000]
coverage=dict(satellites=len(satellites),resource_sets=len(resources),resource_values=sum(len(r['strings']) for r in resources))
(out/'results.json').write_text(json.dumps(dict(commands=commands,completed_satellites_reused_after_count_assertion_correction=resume,resource_newline_policy='Windows text serialization followed by original MSBuildResXReader XmlTextReader with normalization disabled; exact CRLF values checked',coverage=coverage,original_resource_inputs_sha256=originals,satellite_sha256=satellites,all_original_localized_values_verified=True,german_cli_help_verified=True,formal_package_built=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original MSBuild18 localization',coverage,flush=True)
