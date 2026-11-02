"""Stage original task targets and source compiler assets in MSBuild's Roslyn folder."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

root,prefix=(Path(p).resolve() for p in sys.argv[1:]);prefix.mkdir();here=Path(__file__).resolve().parent
tool=prefix/'lib/dotnet10/build-packs/msbuild-18.3.0-net10-bootstrap/Roslyn';tool.mkdir(parents=True)
actual=Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip());compiler=actual/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';compiler_hashes={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in compiler.rglob('*'):
    if not p.is_file() or p.suffix not in {'.dll','.json','.pdb'}:continue
    target=tool/'bincore'/p.relative_to(compiler);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);compiler_hashes[p.relative_to(compiler).as_posix()]=sha(p)
assert sum(1 for p in compiler_hashes if p.endswith('.resources.dll'))==39
for ext in ['dll','pdb']:shutil.copyfile(root/'task'/('Microsoft.Build.Tasks.CodeAnalysis.'+ext),tool/('Microsoft.Build.Tasks.CodeAnalysis.'+ext))
for p in (root/'localized').glob('*/Microsoft.Build.Tasks.CodeAnalysis.resources.dll'):
    target=tool/p.parent.name/p.name;target.parent.mkdir();shutil.copyfile(p,target)
source=root/'roslyn-source';tasks=source/'src/Compilers/Core/MSBuildTask'
targets={}
for p in tasks.glob('Microsoft.*.targets'):shutil.copyfile(p,tool/p.name);targets[p.name]=sha(p)
shutil.copyfile(root/'generated-targets/Microsoft.Managed.Core.CurrentVersions.targets',tool/'Microsoft.Managed.Core.CurrentVersions.targets')
doc=prefix/'share/doc/dotnet-roslyn53-msbuild-tasks-bootstrap';checks=doc/'checks';checks.mkdir(parents=True)
for n in ['check-installed.py','check-server.py','ResourceCheck.cs']:shutil.copyfile(here/n,checks/n)
shutil.copyfile(tasks/'ErrorString.resx',checks/'ErrorString.resx');shutil.copyfile(root/'localized/expected.json',checks/'expected-localization.json')
for original,name in [('prepare-results.json','prepare-results.json'),('build-results.json','build-results.json'),('source-audit.json','source-audit.json'),('task/results.json','task-build-results.json'),('msbuild17/results.json','msbuild17-build-results.json'),('localized/results.json','localization-build-results.json')]:shutil.copyfile(root/original,doc/name)
shutil.copyfile(here/'README.md',doc/'README.md')
license_dir=prefix/'share/licenses/dotnet-roslyn53-msbuild-tasks-bootstrap';license_dir.mkdir(parents=True)
shutil.copyfile(source/'License.txt',license_dir/'License.txt')
(doc/'compiler-source-asset-sha256.json').write_text(json.dumps(compiler_hashes,indent=2)+'\n');(doc/'original-target-sha256.json').write_text(json.dumps(targets,indent=2)+'\n')
manifest={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc/'payload-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS staged original NET10 Roslyn tasks,13 task satellites,39 compiler satellites and original targets;',len(manifest),'files')
