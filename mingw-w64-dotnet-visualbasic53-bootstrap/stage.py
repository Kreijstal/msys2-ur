"""Stage only the VB/server companion files, preserving CSharp ownership."""
from pathlib import Path
import hashlib,json,shutil,sys
root,prefix=(Path(p).resolve() for p in sys.argv[1:3]);assert not prefix.exists();here=Path(__file__).resolve().parent
tool=prefix/'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap';tool.mkdir(parents=True)
doc=prefix/'share/doc/dotnet-visualbasic53-bootstrap';doc.mkdir(parents=True)
names={'Microsoft.CodeAnalysis.VisualBasic.dll','Microsoft.CodeAnalysis.VisualBasic.pdb','Microsoft.CodeAnalysis.VisualBasic.resources.dll','Microsoft.CodeAnalysis.VisualBasic.resources.pdb','vbc.dll','vbc.pdb','vbc.runtimeconfig.json','VBCSCompiler.dll','VBCSCompiler.pdb','VBCSCompiler.runtimeconfig.json'}
csharp_files=json.loads(Path('/clang64/share/doc/dotnet-csharp-compiler53-bootstrap/payload-files.json').read_text())
for p in (root/'localized/bin').rglob('*'):
 if p.is_file() and p.name in names:
  relative=p.relative_to(root/'localized/bin');target=tool/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  assert target.relative_to(prefix).as_posix() not in csharp_files,relative
shutil.copyfile(here/'vbc53.cmd',tool/'vbc53.cmd')
command=prefix/'bin/vbc53-bootstrap';command.parent.mkdir();shutil.copyfile(here/'vbc53-bootstrap',command);command.chmod(0o755)
checks=doc/'checks';checks.mkdir()
for n in ['check-installed.py','check-net10-vbc.py','check-net10-server.py']:shutil.copyfile(here/n,checks/n)
for n in ['VBChecks.dll','VBChecks.pdb','VBChecks.runtimeconfig.json']:shutil.copyfile(root/'localized/bin'/n,checks/n)
for n in ['localization.json','api-vb.txt','friends.json']:shutil.copyfile(root/'localized'/n,checks/n)
shutil.copytree(root/'prepared/roslyn-source/src/Compilers/VisualBasic/Portable/Symbols/EmbeddedSymbols',checks/'embedded-templates')
for src,name in [('source-audit.json','source-audit.json'),('vb-build/results.json','vb-build-results.json'),('clients/results.json','clients-build-results.json'),('localized/results.json','localization-results.json'),('csharp-source-package-inputs.json','csharp-source-package-inputs.json'),('server-check λ/results.json','server-results.json'),('vbc-check λ/results.json','vbc-results.json')]:shutil.copyfile(root/src,doc/name)
shutil.copyfile(here/'README.md',doc/'README.md')
for n in ['License.txt','THIRD-PARTY-NOTICES.txt']:
 p=prefix/'share/licenses/dotnet-visualbasic53-bootstrap'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'prepared/roslyn-source'/n,p)
(doc/'package-limits.json').write_text(json.dumps(dict(provided_original_net10_projects=['Microsoft.CodeAnalysis.VisualBasic','vbc','VBCSCompiler'],source_satellites=13,requires_source_csharp_companion=True,all_other_framework_profiles_built=False,original_sdk10_msbuild_tasks_built=False,full_sdk10_built=False,powershell76_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
manifest={p.relative_to(prefix).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(prefix.rglob('*')) if p.is_file()}
(doc/'payload-files.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Staged',len(manifest),'VB/server companion files')
