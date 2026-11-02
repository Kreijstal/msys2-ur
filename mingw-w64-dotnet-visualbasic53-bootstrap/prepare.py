"""Prepare pristine VB sources and bind the installed source CSharp compiler."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
root,out=(Path(p).resolve() for p in sys.argv[1:3]);here=Path(__file__).resolve().parent
subprocess.run(['/usr/bin/python3',str(here/'legacy/prepare.py'),str(root),str(out)],check=True)
subprocess.run(['/usr/bin/python3',str(here/'evaluate-net10-toolset.py'),str(out),str(root/'net10-evaluation'),str(root/'net10-plan')],check=True)
subprocess.run(['/usr/bin/python3',str(here/'vb-bootstrap-inputs/prepare-generators.py'),str(out/'roslyn-source'),str(root/'vb-generators')],check=True)
tool=Path('/clang64/lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap');doc=Path('/clang64/share/doc/dotnet-csharp-compiler53-bootstrap')
manifest=json.loads((doc/'payload-files.json').read_text());prefix=Path('/clang64')
for n,d in manifest.items():assert hashlib.sha256((prefix/n).read_bytes()).hexdigest()==d,n
(root/'csharp-source-package-inputs.json').write_text(json.dumps(dict(installed_package=subprocess.check_output(['pacman','-Q','mingw-w64-clang-x86_64-dotnet-csharp-compiler53-bootstrap'],text=True).strip(),actual_source_tool_files_sha256={p.relative_to(tool).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in tool.rglob('*') if p.is_file()},all_installed_csharp_payload_hashes_verified=True),indent=2)+'\n')
shutil.copytree(tool,root/'csharp/bin')
