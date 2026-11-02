"""Exercise original NET10 compiler targets and installed task/server resources."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
actual=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=actual/'lib/dotnet10/dotnet.exe';native=lambda p:Path(p).resolve().as_posix()
relative=Path('lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap');msbuild=actual/relative/'MSBuild.dll';tool=prefix/relative/'Roslyn';task=tool/'Microsoft.Build.Tasks.CodeAnalysis.dll';doc=prefix/'share/doc/dotnet-roslyn53-msbuild-tasks-bootstrap';checks=doc/'checks'
manifest=json.loads((doc/'payload-sha256.json').read_text())
for rel,digest in manifest.items():assert hashlib.sha256((prefix/rel).read_bytes()).hexdigest()==digest,rel
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(msbuild),MSBUILDUSESERVER='0',MSBUILDDISABLENODEREUSE='1',MSBuildEnableWorkloadResolver='false')
refs=sorted((actual/'lib/dotnet/reference-packs/runtime-10.0.5/ref/net10.0').glob('*.dll'));assert len(refs)==167
commands=[]
def run(label,command,expected=0):
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==expected,(label,r.returncode)
    return (out/(label+'.log')).read_text(encoding='utf-8')
for language,extension,program in [
 ('CSharp','cs','''using System;
public static class Extensions { extension(string text) { public int TwiceLength => text.Length*2; } }
class Program { static void Main() { if("Grüße".TwiceLength!=10)throw new Exception();Console.WriteLine("PASS original CSharp core targets NET10 Grüße 世界"); } }
'''),
 ('VisualBasic','vb','''Imports System
Imports System.Linq
Module Program
 Sub Main()
  If (From n In {1,2,3} Select n*2).Sum()<>12 Then Throw New Exception("LINQ")
  Console.WriteLine("PASS original VisualBasic core targets NET10 Grüße 世界")
 End Sub
End Module
''')]:
    work=out/(language+' λ');work.mkdir();source=work/('Program 世界.'+extension);source.write_text(program,encoding='utf-8');binary=work/'App.dll'
    p=E.Element('Project');pg=E.SubElement(p,'PropertyGroup')
    values=dict(TargetFrameworkIdentifier='.NETCoreApp',TargetFrameworkVersion='v10.0',_TargetFrameworkVersionWithoutV='10.0',OutputType='Exe',NoCompilerStandardLib='true',DebugSymbols='true',DebugType='portable',Deterministic='true',UseSharedCompilation='false',Utf8Output='true',IntermediateOutputPath=native(work)+'/',GeneratedMSBuildEditorConfigFile=native(work/'Generated.editorconfig'),OwnedProperty='Grüße 世界')
    if language=='VisualBasic':values.update(FinalDefineConstants='_MYTYPE="Empty"',VBRuntime='Embed',OptionStrict='On',OptionInfer='true')
    for k,v in values.items():E.SubElement(pg,k).text=v
    ig=E.SubElement(p,'ItemGroup');E.SubElement(ig,'Compile',Include=native(source));E.SubElement(ig,'IntermediateAssembly',Include=native(binary));E.SubElement(ig,'CompilerVisibleProperty',Include='OwnedProperty')
    for ref in refs:E.SubElement(ig,'ReferencePathWithRefAssemblies',Include=native(ref))
    # Core targets consume the host build's PrepareForBuild hook. This owned
    # no-SDK fixture supplies only that hook; SDK restore/build remains open.
    prepare=E.SubElement(p,'Target',Name='PrepareForBuild');E.SubElement(prepare,'MakeDir',Directories=native(work))
    E.SubElement(p,'Import',Project=native(tool/('Microsoft.'+language+'.Core.targets')))
    receipt=E.SubElement(p,'Target',Name='Receipt',AfterTargets='CoreCompile');E.SubElement(receipt,'WriteLinesToFile',File=native(work/'receipt.txt'),Lines='$(CompilerApiVersion)|$(LangVersion)',Overwrite='true')
    project=work/'Compile.proj';E.ElementTree(p).write(project,encoding='utf-8',xml_declaration=True)
    command=[host,msbuild,project,'-t:CoreCompile','-nr:false','-noautoresponse','-nologo','-v:diag']
    if prefix!=actual:command+=['-p:RoslynTargetsPath='+native(tool)]
    log=run(language+'-compile',command)
    assert native(task).lower() in log.replace('\\','/').lower(),'Default task registration did not load candidate task'
    assert 'CompilerServer: tool - using command line tool by design' in log
    assert 'build_property.OwnedProperty = Grüße 世界' in (work/'Generated.editorconfig').read_text(encoding='utf-8-sig')
    receipt_text=(work/'receipt.txt').read_text(encoding='utf-8-sig').strip();assert receipt_text.startswith('roslyn5.3|')
    if language=='CSharp':assert receipt_text=='roslyn5.3|14.0',receipt_text
    (work/'App.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
    assert 'PASS original '+language+' core targets NET10 Grüße 世界' in run(language+'-execute',[host,binary])
    assert binary.with_suffix('.pdb').is_file()
    source.write_text('class Broken { void M(){ MissingName(); } }' if language=='CSharp' else 'Module Broken\nSub Main()\nMissingName()\nEnd Sub\nEnd Module\n')
    log=run(language+'-invalid',command,1);assert ('CS0103' if language=='CSharp' else 'BC30451') in log
resource_check=out/'ResourceCheck.dll';rsp=out/'resources.rsp';rsp.write_text('\n'.join(['/nostdlib+','/target:exe','/out:"'+native(resource_check)+'"']+['/reference:"'+native(p)+'"' for p in refs]+['"'+native(checks/'ResourceCheck.cs')+'"'])+'\n')
run('resource-check-compile',[host,tool/'bincore/csc.dll','-noconfig','@'+native(rsp)])
(out/'ResourceCheck.runtimeconfig.json').write_text(json.dumps(dict(runtimeOptions=dict(tfm='net10.0',framework=dict(name='Microsoft.NETCore.App',version='10.0.5')))))
assert '434 exact neutral/localized resource values' in run('all-task-resources',[host,resource_check,task,checks/'ErrorString.resx',checks/'expected-localization.json',msbuild.parent])
run('shared-server',[sys.executable,'-X','utf8',checks/'check-server.py',task,msbuild.parent,out/'server','--use-existing-layout'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_byte_verified=len(manifest),original_csharp_and_vb_core_targets_compiled_and_executed=True,original_default_compiler_task_registration_verified=True,generated_original_compiler_api_version='roslyn5.3',original_csharp14_default_langversion_verified=True,unicode_paths_outputs_pdb_error_codes_and_generated_editorconfig_verified=True,task_resource_values_verified=434,task_localized_satellites=13,compiler_localized_satellites=39,actual_packaged_tasks_and_compilers_share_owned_source_server=True,installed_default_roslyn_path_verified=prefix==actual,full_sdk_style_build_verified=False,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS original CSharp/VB core targets,NET10 execution,Unicode/PDB/editorconfig/error codes,434 task values and owned shared server;installed default path:',prefix==actual)
