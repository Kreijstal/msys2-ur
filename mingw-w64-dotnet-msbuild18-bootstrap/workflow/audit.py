"""Verify cold source inputs, generated outputs, exact feeds and checked behavior."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

root=Path(sys.argv[1]).resolve();here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
evidence=root/'source-evidence';evidence.mkdir()
for original,target in [('build','build4'),('version','version-build'),('localized','localized')]:
    (evidence/target).mkdir();shutil.copyfile(root/original/'results.json',evidence/target/'results.json')
subprocess.run([sys.executable,'-X','utf8',here/'audit-original-inputs.py',evidence,root/'msbuild-sdk10-228caa11.tar.gz',root/'arcade-msbuild18-987d1a73.tar.gz',root/'msbuild-source-packages',root/'source-audit.json'],check=True)
build=json.loads((root/'build/results.json').read_text());localization=json.loads((root/'localized/results.json').read_text());cli=json.loads((root/'cli/results.json').read_text());parallel=json.loads((root/'parallel/results.json').read_text())
assert build['all6_project_compilations_passed'] and build['original_arcade_version_policy_verified']
assert localization['coverage']==dict(satellites=53,resource_sets=118,resource_values=23597)
assert localization['all_original_localized_values_verified'] and localization['german_cli_help_verified']
assert parallel['two_distinct_worker_processes_verified']
checked={}
def verify(path,digest):
    path=Path(path);assert sha(path)==digest,str(path);checked[str(path)]=digest
for r in build['projects']:
    for path,digest in r['actual_reference_sha256'].items():verify(path,digest)
    for base in [root/'build'/r['project'],root/'localized/bin']:verify(base/(r['project']+'.dll'),r['output_sha256'])
    for rel,digest in r['generated_regex_source_sha256'].items():verify(root/'build'/r['project']/rel,digest)
    for rel,digest in r['source_package_cs_sha256'].items():verify(root/'build'/r['project']/'source-packages'/rel,digest)
for rel,digest in localization['satellite_sha256'].items():verify(root/'localized/bin'/rel,digest)
(root/'output-audit.json').write_text(json.dumps(dict(all_current_output_reference_generated_and_source_package_hashes_match=True,verified_files=len(checked),sha256=checked),indent=2)+'\n')
print('PASS cold original source/archive,reference/generated/output and all53 satellite audits')
