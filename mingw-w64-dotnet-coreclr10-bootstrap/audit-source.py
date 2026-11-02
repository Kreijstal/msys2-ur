"""Revalidate native archive/patch bytes, actual Ninja inputs and source cDAC inputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile,re
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
native=lambda p:subprocess.check_output(['cygpath','-am',str(p)],text=True).strip()
# Native Python avoids tens of thousands of MSYS filesystem round trips.
subprocess.run(['/clang64/bin/python.exe',native(here/'audit-runtime-native.py'),native(root),native(here)],check=True)
audit=json.loads((root/'native-source-audit.json').read_text());record=json.loads((root/'cdac-bootstrap/source-inputs.json').read_text());vmr=json.loads((here/'inputs/command-line-vmr-audit.json').read_text());base=native(root)
def posix(p):
 p=p.replace('\\','/');assert p.lower().startswith(base.lower()+'/'),p
 return root/p[len(base)+1:]
for p,h in record['source_files_sha256'].items():assert hashlib.sha256(posix(p).read_bytes()).hexdigest()==h,p
for name,directory in [('command-line',root/'cdac-bootstrap/command-line-source'),('tool',root/'r/src/coreclr/tools/cdac-build-tool')]:
 actual={posix(p) for p in (root/'cdac-bootstrap'/name/'obj/Release/net8.0/Compile.txt').read_text().splitlines() if p}
 wanted={posix(p) for p in record['source_files_sha256'] if p.endswith('.cs') and posix(p).is_relative_to(directory)}
 assert {p for p in actual if p.is_relative_to(directory)}==wanted,(name,wanted-actual)
for p,item in vmr['verified_original_inputs'].items():
 data=(root/'cdac-bootstrap/command-line-source'/p).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256'] and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==item['git_blob_sha1'],p
audit.update(cdac_original_source_files=record['cdac_original_cs'],command_line_original_source_files=record['command_line_original_cs'],command_line_exact_vmr_inputs=len(vmr['verified_original_inputs']),actual_cdac_compiler_inputs_verified=True,full_dependency_goal_complete=False)
(root/'source-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('PASS original native/archive/patch/Ninja inputs and unchanged source cDAC/System.CommandLine inputs')
