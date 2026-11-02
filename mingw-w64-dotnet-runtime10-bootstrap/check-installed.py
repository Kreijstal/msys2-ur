"""Check every packaged byte and execute all source-hosted framework probes."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

prefix=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
assert not out.exists(),out
doc=prefix/'share/doc/dotnet-runtime10-bootstrap';here=doc/'checks'
manifest=json.loads((doc/'payload-files.json').read_text())
for name,digest in manifest.items():
 file=prefix/name;assert file.is_file() and hashlib.sha256(file.read_bytes()).hexdigest()==digest,name
print('PASS',len(manifest),'installed runtime/package bytes')
env=dict(os.environ,PATH=str(prefix/'bin')+os.pathsep+os.environ['PATH'])
command=['/usr/bin/python3',str(here/'check-host.py'),str(prefix/'lib/dotnet10'),str(out),
 *[str(here/'probes'/(n+'.dll')) for n in ['native','framework','javascript']]]
subprocess.run(command,env=env,check=True)
launcher=subprocess.run(['bash',str(prefix/'bin/dotnet10-bootstrap'),'--list-runtimes'],env=env,
 stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(out/'launcher-list-runtimes.log').write_text(launcher.stdout)
assert launcher.returncode==0 and 'Microsoft.NETCore.App 10.0.5 [' in launcher.stdout,launcher.stdout
print('PASS installed launcher, host discovery and complete-framework probes')
