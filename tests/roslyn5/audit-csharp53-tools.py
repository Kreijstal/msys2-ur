"""Audit installed source-package ownership and bytes of the real build tools."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,subprocess,sys
root=Path(sys.argv[1]).resolve();prefix=Path('/clang64')
@lru_cache(maxsize=None)
def local(value):
 return Path(subprocess.check_output(['cygpath','-u',value],text=True).strip()) if ':/' in value.replace('\\','/') else Path(value)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((root/'src/source-audit.json').read_text())['actual_compiler_generator_and_reference_inputs_sha256']
tools=json.loads((root/'src/prepared/tool-inputs.json').read_text())
for name,record in tools.items():inputs[name]=record['sha256']
for path in [prefix/'lib/dotnet/dotnet.exe',prefix/'lib/dotnet/sdk/8.0.131/MSBuild.dll',prefix/'lib/dotnet/sdk/8.0.131/Microsoft.Build.dll',prefix/'lib/dotnet10/dotnet.exe']:
 inputs[str(path)]=sha(path)
owners={};verified={}
for name,digest in inputs.items():
 path=local(name)
 if not path.is_relative_to(prefix):continue
 assert sha(path)==digest,name
 owner=subprocess.check_output(['pacman','-Qoq',str(path)],text=True).strip()
 assert owner.startswith('mingw-w64-clang-x86_64-dotnet-'),(path,owner)
 owners.setdefault(owner,[]).append(str(path));verified[str(path)]=digest
assert len(verified)>=167,len(verified)
assert any(Path(n).name=='CompilerHost.dll' for n in verified)
assert any(Path(n).name=='System.Text.RegularExpressions.Generator.dll' for n in verified)
for owner in sorted(owners):
 result=subprocess.run(['pacman','-Qkk',owner],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 assert result.returncode==0 and ', 0 altered files' in result.stdout,(owner,result.stdout)
(root/'tool-ownership-audit.json').write_text(json.dumps(dict(installed_source_tool_and_reference_bytes_verified=len(verified),installed_source_package_owners=owners,installed_source_bytes_sha256=verified,all_actual_source_package_bytes_and_owner_integrity_verified=True,inherited_compiler5_bootstrap_profile=True,full_sdk10_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS',len(verified),'installed source tool/ref bytes;',len(owners),'source package owners,0 altered files')
