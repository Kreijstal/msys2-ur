"""Stage the validated source compiler and an independently checkable manifest."""
from pathlib import Path
import hashlib,json,shutil,sys
root,prefix=(Path(p).resolve() for p in sys.argv[1:3]);here=Path(__file__).resolve().parent
assert not prefix.exists();tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';tool.mkdir(parents=True)
doc=prefix/'share/doc/dotnet-csharp-compiler53-bootstrap';doc.mkdir(parents=True)
for p in (root/'localized/bin').rglob('*'):
 if p.is_file() and not p.name.startswith('Check.'):
  target=tool/p.relative_to(root/'localized/bin');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
shutil.copyfile(here/'csc53.cmd',tool/'csc53.cmd')
command=prefix/'bin/csc53-bootstrap';command.parent.mkdir();shutil.copyfile(here/'csc53-bootstrap',command);command.chmod(0o755)
checks=doc/'checks';checks.mkdir()
shutil.copyfile(here/'check-installed.py',checks/'check-installed.py')
for n in ['Check.dll','Check.pdb','Check.runtimeconfig.json']:shutil.copyfile(root/'localized/bin'/n,checks/n)
for n in ['api-common.txt','api-csharp.txt','localization-common.json','localization-csharp.json','original-localization-coverage.json']:shutil.copyfile(root/'localized'/n,checks/n)
for src,dest in [('source-audit.json','source-audit.json'),('net10-build/build-status.json','build-status.json'),('localized/results.json','localization-results.json'),('cli-check/results.json','cli-results.json'),('net10-evaluation/results.json','evaluation-results.json')]:shutil.copyfile(root/src,doc/dest)
shutil.copyfile(here/'README.md',doc/'README.md')
for n in ['License.txt','THIRD-PARTY-NOTICES.txt']:
 p=prefix/'share/licenses/dotnet-csharp-compiler53-bootstrap'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'prepared/roslyn-source'/n,p)
limits=dict(provided_original_net10_projects=['Microsoft.CodeAnalysis','Microsoft.CodeAnalysis.CSharp','csc'],source_satellites=26,visualbasic_and_compiler_server_built=False,original_net472_profiles_built=False,source_sdk10_msbuild_tasks_built=False,full_sdk10_built=False,powershell76_built=False,full_dependency_goal_complete=False)
(doc/'package-limits.json').write_text(json.dumps(limits,indent=2)+'\n')
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(prefix.rglob('*')) if p.is_file()}
(doc/'payload-files.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Staged source NET10 compiler:',len(manifest),'manifested files')
