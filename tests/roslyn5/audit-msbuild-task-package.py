"""Audit an actual source NET10 Roslyn task pacman archive independently."""
from pathlib import Path
import hashlib,json,sys,tarfile

package,output=(Path(p).resolve() for p in sys.argv[1:]);sha=lambda data:hashlib.sha256(data).hexdigest()
doc='clang64/share/doc/dotnet-roslyn53-msbuild-tasks-bootstrap/'
tool='clang64/lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/Roslyn/'
with tarfile.open(package) as t:
    members={m.name.removeprefix('./'):m for m in t.getmembers() if m.isfile()}
    def read(name):return t.extractfile(members[name]).read()
    def load(name):return json.loads(read(doc+name))
    manifest=load('payload-sha256.json')
    for path,digest in manifest.items():assert sha(read('clang64/'+path))==digest,path
    actual={n for n in members if n.startswith('clang64/')};expected={'clang64/'+n for n in manifest}|{doc+'payload-sha256.json'}
    assert actual==expected,actual^expected
    build=load('task-build-results.json');source=load('source-audit.json');localization=load('localization-build-results.json')
    assert sha(read(tool+'Microsoft.Build.Tasks.CodeAnalysis.dll'))==build['output_sha256']
    assert build['original_target_framework']=='net10.0' and build['original_compile_time_msbuild_source_version']=='17.11.48'
    assert build['original_production_source_changes']==0
    assert source['roslyn_task']['original_compile_items']==60 and source['msbuild17']['original_compile_items']==1195 and source['collections_source_items']==37
    assert len(localization['satellite_sha256'])==13
    for path,digest in localization['satellite_sha256'].items():assert sha(read(tool+path))==digest,path
    targets=load('original-target-sha256.json')
    for name,digest in targets.items():assert sha(read(tool+name))==digest,name
    compiler=load('compiler-source-asset-sha256.json')
    for path,digest in compiler.items():assert sha(read(tool+'bincore/'+path))==digest,path
    assert sum(n.endswith('.resources.dll') for n in compiler)==39
    assert all(tool+'bincore/'+n+'.dll' in members for n in ['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','Microsoft.CodeAnalysis.VisualBasic','csc','vbc','VBCSCompiler'])
    assert 'clang64/lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/MSBuild.dll' not in members
    info=read('.PKGINFO').decode();assert 'pkgname = mingw-w64-clang-x86_64-dotnet-roslyn53-msbuild-tasks-bootstrap\n' in info
    assert 'pkgver = 5.3.0.2.26113.113-1\n' in info
    record=dict(package=package.name,package_sha256=sha(package.read_bytes()),regular_payload_files=len(actual),all_payload_bytes_and_exact_file_inventory_verified=True,original_net10_task_output_matches=True,original_task_cs_inputs=60,private_msbuild17_compile_items=1195,collections_source_items=37,task_satellites=13,compiler_satellites=39,source_compiler_asset_files=len(compiler),all_original_target_and_compiler_asset_hashes_verified=True,msbuild_host_dll_not_replaced=True,full_sdk10_built=False,full_dependency_goal_complete=False)
output.write_text(json.dumps(record,indent=2)+'\n')
print('PASS actual NET10 Roslyn task package:',record['regular_payload_files'],'payload files,13 task satellites,39 compiler satellites,original targets and source compiler asset hashes')
