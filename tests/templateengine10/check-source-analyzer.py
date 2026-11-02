"""Opt-in PublicApiAnalyzer probe for the six projects that declare it.

The original NET10 source-only profile disables custom analyzers. This additional
probe executes their public-API analyzer scope without changing that profile or
its original sources/baselines; full StyleCop/SDK integration remains separate.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as E
import zipfile

plan, build, out = (Path(p).resolve() for p in sys.argv[1:])
out.mkdir()
source = Path(json.loads((plan / 'source-inputs.json').read_text())['source_root'])
prefix = Path(subprocess.check_output(['cygpath','-am','/clang64'],text=True).strip())
host = prefix / 'lib/dotnet10/dotnet.exe'
compiler = prefix / 'lib/dotnet/compiler-packs/roslyn-5.3.0-net10-bootstrap/csc.dll'
archive = prefix / 'lib/dotnet/library-packs/microsoft.codeanalysis.publicapianalyzers.3.3.4.nupkg'
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected = json.loads((prefix / 'share/doc/dotnet-publicapi334-bootstrap/archives.json').read_text())
assert sha(archive)==expected['sha256']
with zipfile.ZipFile(archive) as z:
    analyzer = out / 'Microsoft.CodeAnalysis.PublicApiAnalyzers.dll'
    analyzer.write_bytes(z.read('analyzers/dotnet/' + analyzer.name))
native = lambda p:Path(p).resolve().as_posix()
records = []
for record in json.loads((build / 'results.json').read_text())['projects']:
    name = record['assembly']
    original = source / 'src' / name / (name + '.csproj')
    if E.parse(original).findtext('.//EnablePublicApiAnalyzer') != 'true':
        continue
    folder = out / name
    folder.mkdir()
    args = (build / name / 'compile.rsp').read_text().splitlines()
    args = [('/out:"' + native(folder / (name + '.dll')) + '"') if a.startswith('/out:') else ('/doc:"' + native(folder / (name + '.xml')) + '"') if a.startswith('/doc:') else a for a in args]
    args += ['/analyzer:"' + native(analyzer) + '"']
    baselines = []
    for label in ['Shipped','Unshipped']:
        original_file = original.parent / ('PublicAPI.' + label + '.txt')
        baseline = folder / original_file.name
        baseline.write_bytes(original_file.read_bytes())
        baselines.append(dict(original=native(original_file),sha256=sha(original_file)))
        args.append('/additionalfile:"' + native(baseline) + '"')
    for path in source.rglob('.editorconfig'):
        # Include only configuration files on this project's ancestor path.
        if original.is_relative_to(path.parent):args.append('/analyzerconfig:"' + native(path) + '"')
    rsp = folder / 'compile.rsp'
    rsp.write_text('\n'.join(args) + '\n')
    command = [host, compiler, '-noconfig', '@' + native(rsp)]
    with (folder / 'compile.log').open('w',encoding='utf-8') as log:
        result = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DOTNET_ROOT=native(host.parent),DOTNET_ROOT_X64=native(host.parent)),timeout=240)
    text = (folder / 'compile.log').read_text()
    diagnostics = re.findall(r'(?:warning|error) (\w+\d+):', text)
    assert not any(code in text for code in ['AD0001','CS8032','CS9057']),name
    records.append(dict(assembly=name,command=[str(p) for p in command],exit_code=result.returncode,diagnostic_ids=diagnostics,original_baselines=baselines))
    print(name,result.returncode,sorted(set(diagnostics)),flush=True)
assert len(records)==6
(out / 'results.json').write_text(json.dumps(dict(projects=records,installed_source_analyzer_archive_SHA256=sha(archive),actual_source_analyzer_executed=True,original_NET10_source_only_custom_analyzers_remain_disabled=True,additional_opt_in_probe=True,production_sources_and_original_API_baselines_unchanged=True,all_six_original_API_analyzer_scoped_projects_passed=all(r['exit_code']==0 for r in records),full_original_analyzer_or_SDK_integration_verified=False,full_dependency_goal_complete=False),indent=2)+'\n')
raise SystemExit(0 if all(r['exit_code']==0 for r in records) else 1)
