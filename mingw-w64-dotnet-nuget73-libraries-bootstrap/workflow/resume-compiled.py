"""Resume only if the original producers are identical and completed output hashes verify."""
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
with tarfile.open(root/'nuget73-libraries-source-1.tar.gz') as t:
    files={Path(m.name).name:t.extractfile(m).read() for m in t if m.isfile()}
for n in ['prepare.py','prepare-all.py','EvaluateProjects.cs','build-closure.py','localize-closure.py']:
    assert (here/n).read_bytes()==files[n],('producer changed',n)
subprocess.run([sys.executable,'-X','utf8',here/'audit-closure.py',root,root/'build',root/'resume-audit.json'],check=True)
assets={p.relative_to(root/'build/bin').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'build/bin').rglob('*') if p.is_file()}
assert len([n for n in assets if n.endswith('.resources.dll')])==104
(root/'resume-compiled.json').write_text(json.dumps(dict(original_producers_unchanged=True,completed_binary_asset_sha256=assets,original_input_output_and_reference_hashes_verified=True),indent=2)+'\n')
print('PASS verified completed original library/XML/satellite outputs; original producers unchanged')
