"""Cold source compile of task prerequisites,NET10 tasks,original targets and XLF."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as E

root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
prefix=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());host=prefix/'lib/dotnet10/dotnet.exe';msbuild=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/MSBuild.dll';native=lambda p:Path(p).resolve().as_posix()
commands=[]
def run(label,command,env=None):
    print('RUN',label,flush=True)
    with (root/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
    commands.append(dict(label=label,command=[str(p) for p in command],exit_code=r.returncode));assert r.returncode==0,(label,r.returncode)
resumed=os.environ.get('ROSLYN_TASKS_RESUME_COMPILED')=='1'
if resumed:
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    model=json.loads((root/'msbuild17/results.json').read_text())['projects']
    task_model=json.loads((root/'task/results.json').read_text())
    for r in model+[task_model]:
        source=Path(json.loads((root/('plan17' if 'project' in r else 'task-plan')/'source-inputs.json').read_text())['source_root'])
        for key in ['original_source_sha256','original_resource_sha256']:
            for rel,digest in r[key].items():assert sha(source/rel)==digest,rel
        for path,digest in r['actual_reference_sha256'].items():assert sha(path)==digest,path
        dll=root/'msbuild17'/r['project']/(r['project']+'.dll') if 'project' in r else root/'task/Microsoft.Build.Tasks.CodeAnalysis.dll'
        assert sha(dll)==r['output_sha256']
    print('REUSE terminal-success unchanged source/reference/output hashes:6 MSBuild17 projects and NET10 task',flush=True)
else:
    run('msbuild17',[sys.executable,'-X','utf8',here/'build-msbuild17.py',root/'plan17',root/'msbuild17'])
    run('task',[sys.executable,'-X','utf8',here/'build-task.py',root/'task-plan',root/'msbuild17',root/'task'])
generated=root/'generated-targets';generated.mkdir()
project=E.Element('Project');pg=E.SubElement(project,'PropertyGroup');E.SubElement(pg,'IntermediateOutputPath').text=native(generated)+'/'
E.SubElement(project,'Import',Project=native(root/'roslyn-source/eng/Versions.props'))
E.SubElement(project,'Import',Project=native(root/'task-plan/Task.targets'))
generation_project=root/'GenerateVersion.proj';E.ElementTree(project).write(generation_project,encoding='utf-8',xml_declaration=True)
env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent),DOTNET_HOST_PATH=native(host),MSBUILD_EXE_PATH=native(msbuild),MSBuildSDKsPath=native(prefix/'lib/dotnet/sdk/8.0.131/Sdks'))
run('original-version-target',[host,msbuild,generation_project,'-t:GenerateCompilerVersionTargetsFile','-nologo','-noautoresponse','-nr:false'],env)
assert E.parse(generated/'Microsoft.Managed.Core.CurrentVersions.targets').findtext('.//CompilerApiVersion')=='roslyn5.3'
run('localization',[sys.executable,'-X','utf8',here/'localize.py',root])
(root/'build-results.json').write_text(json.dumps(dict(commands=commands,cold_source_build=not resumed,verified_completed_source_builds_reused_after_generation_harness_fix=resumed,original_version_target_executed=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS cold original NET10 Roslyn task and source MSBuild17.11 prerequisite build')
