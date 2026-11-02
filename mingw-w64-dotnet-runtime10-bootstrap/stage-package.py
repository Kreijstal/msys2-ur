"""Stage the audited framework and reproducible installed-package checks."""
from pathlib import Path
import hashlib,json,shutil,sys

root=Path(sys.argv[1]).resolve();prefix=Path(sys.argv[2]).resolve()
here=Path(__file__).resolve().parent
assert not prefix.exists(),prefix
layout=root/'runtime-layout';manifest=json.loads((layout/'source-payload.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,item in manifest['source_files'].items():assert sha(layout/name)==item['sha256'],name
shutil.copytree(layout,prefix/'lib/dotnet10')
doc=prefix/'share/doc/dotnet-runtime10-bootstrap';doc.mkdir(parents=True)
for name in ['README.md']:shutil.copy2(here/name,doc/name)
files={
 'build-plan/compiler-source-audit.json':'compiler-source-audit.json',
 'build-plan/build-status.json':'build-status.json',
 'managed-source-inputs.json':'managed-source-inputs.json',
 'version-build-inputs.json':'version-build-inputs.json',
 'linked-check/results.json':'linked-results.json',
 'runtime-check/results.json':'runtime-results.json',
 'host-check/results.json':'host-results.json',
 'asn-check/results.json':'asn-results.json',
 'contract-check/results.json':'contract-results.json',
 'contract-check/compare.exit':'strict-contract.exit',
}
for source,target in files.items():shutil.copy2(root/source,doc/target)
checks=doc/'checks';checks.mkdir();(checks/'probes').mkdir();(checks/'sources').mkdir()
shutil.copy2(here/'check-installed.py',checks/'check-installed.py')
shutil.copy2(root/'framework-workflow/check-host.py',checks/'check-host.py')
for case,name in [('native','NativeFrameworkProbe.cs'),('framework','CompleteFrameworkProbe.cs'),('javascript','JavaScriptWindowsProbe.cs')]:
 shutil.copy2(root/'runtime-check/complete CLR10 λ'/(case+'.dll'),checks/'probes'/(case+'.dll'))
 shutil.copy2(root/'framework-workflow/inputs'/name,checks/'sources'/name)
binfolder=prefix/'bin';binfolder.mkdir()
shutil.copy2(here/'dotnet10-bootstrap.sh',binfolder/'dotnet10-bootstrap');(binfolder/'dotnet10-bootstrap').chmod(0o755)
licenses=prefix/'share/licenses/dotnet-runtime10-bootstrap';licenses.mkdir(parents=True)
for name in ['LICENSE.TXT','THIRD-PARTY-NOTICES.TXT']:shutil.copy2(root/'r'/name,licenses/name)
shutil.copy2(root/'Arcade-LICENSE.TXT',licenses/'Arcade-LICENSE.TXT')
contract=json.loads((doc/'contract-results.json').read_text())
assert len(contract['assemblies'])==167 and not any(v['missing'] for v in contract['assemblies'].values())
(doc/'package-limits.json').write_text(json.dumps(dict(
 managed_framework_assemblies=172,private_seed_assemblies_shipped=0,
 strict_contract_exit_code=int((doc/'strict-contract.exit').read_text()),
 strict_reference_api_shape_parity_verified=contract['total_differences']==0,
 extra_contract_entries=sum(len(v['extra']) for v in contract['assemblies'].values()),
 changed_contract_entries=sum(len(v['changed']) for v in contract['assemblies'].values()),
 full_runtime_compatibility_verified=False,full_sdk10_built=False,powershell76_built=False,
 full_dependency_goal_complete=False),indent=2)+'\n')
proof={p.relative_to(prefix).as_posix():sha(p) for p in prefix.rglob('*') if p.is_file()}
(doc/'payload-files.json').write_text(json.dumps(proof,indent=2)+'\n')
print('PASS source runtime package staged:',len(proof),'audited files, private seeds excluded')
