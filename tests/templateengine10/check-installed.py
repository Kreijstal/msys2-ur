"""Check packaged TemplateEngine payload, fresh restore, runtime and unchanged API failure."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile

prefix,out=(Path(p).resolve() for p in sys.argv[1:]);out.mkdir()
doc=prefix/'share/doc/dotnet-templateengine10-bootstrap';here=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();native=lambda p:Path(p).resolve().as_posix()
manifest=json.loads((doc/'payload-sha256.json').read_text());archives=json.loads((doc/'archives.json').read_text())
for rel,expected in manifest.items():assert sha(prefix/rel)==expected,rel
plan=out/'plan';plan.mkdir();shutil.copytree(doc/'validation-source',plan/'source');(plan/'source-inputs.json').write_text(json.dumps(dict(source_root=native(plan/'source'))))
build=out/'build';binary=build/'bin';binary.mkdir(parents=True);shutil.copyfile(doc/'build-results.json',build/'results.json')
localized=out/'localized';localized.mkdir();shutil.copyfile(doc/'localization-results.json',localized/'results.json')
commands=[]
def run(label,script,args,expected=0):
    command=[sys.executable,'-X','utf8',here/script,*args]
    with (out/(label+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=600)
    commands.append(dict(command=[str(p) for p in command],exit_code=r.returncode,expected_exit_code=expected));assert r.returncode==expected,(label,r.returncode)
run('restore','check-package-restore.py',[prefix,out/'restore'])
for name,archive in archives.items():
    cached=out/'restore/cache'/name.lower()/'10.0.200-preview.26113.113'/(name.lower()+'.10.0.200-preview.26113.113.nupkg')
    assert sha(cached)==archive['sha256']
    with zipfile.ZipFile(cached) as z:
        assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==archive['members']
        for member in z.namelist():
            if member.startswith('lib/net10.0/'):
                target=binary/member[len('lib/net10.0/'):];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(member))
run('resources','check-resources.py',[plan,build,localized,out/'resources'])
run('runtime-and-API','check.py',[plan,out/'restore',build,out/'runtime-API'],1)
run('original-API-failure','check-api-baseline.py',[out/'runtime-API'])
(out/'results.json').write_text(json.dumps(dict(commands=commands,payload_files_verified=len(manifest),seven_exact_source_TemplateEngine_archives_verified=True,original_NET10_framework_and_identities_verified=True,fresh_original_CPM_WAE_and_archive_bytes_verified=True,owned_folder_and_NuGet_template_install_generate_uninstall_passed=True,resources_and_PDBs_verified=True,strict_all_seven_API_baseline_passed=False,strict_all_seven_API_baseline_exit_code=1,original_missing_API_entries=2,original_API_failure_report_preserved=True,full_original_SDK_pruning_integration_verified=False,other_original_framework_profiles_built=False,full_dependency_goal_complete=False),indent=2)+'\n')
print('PASS fresh packaged runtime/restore/resources; stronger original API baseline remains FAILED with exactly two unchanged entries')
