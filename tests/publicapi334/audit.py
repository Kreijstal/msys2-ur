"""Audit every original snapshot byte, explicit source port and compiler input policy."""
from pathlib import Path
import hashlib
import json
import sys
import tarfile
from port import port_source

archive, build, config_comparison, output = (Path(p).resolve() for p in sys.argv[1:])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(archive) == '49a992347546aef48cb31673b294bd1b10c30e68bbb53be61d411bb0d7219e1e'
source = build / 'snapshot/source'
manifest = json.loads((build / 'snapshot/source-inputs.json').read_text())
records = json.loads((build / 'results.json').read_text())
assert records['compiler_warnings_as_errors']
originals = {}
with tarfile.open(archive) as original:
    prefix = 'roslyn-analyzers-22ea6422f85b05ca0793cc3b76375487be407f5d/'
    for member in original:
        rel = member.name[len(prefix):]
        if member.isfile() and rel in manifest['files']:
            originals[rel] = hashlib.sha256(original.extractfile(member).read()).hexdigest()
assert originals == manifest['files']
for rel, expected in originals.items():assert sha(source / rel) == expected, rel
ports, inputs, outputs = {}, 0, {}
for label, record in records['projects'].items():
    response = (build / label / 'compile.rsp').read_text()
    assert '/warnaserror+' in response and '/nullable:enable' in response
    assert not any(flag in response for flag in ['CODEANALYSIS_V3_OR_BETTER','CODEANALYSIS_V3_7_OR_BETTER','HAS_IOPERATION'])
    assert record['original_source_Roslyn_capability_guards_preserved']
    assert record['original_framework'] == 'netstandard2.0'
    assert record['original_MicrosoftCodeAnalysisVersion'] == '1.2.1'
    for rel, expected in record['sources'].items():
        original = source / rel
        assert sha(original) == expected == originals[rel]
        before = original.read_text(encoding='utf-8-sig')
        after, reasons = port_source(original.name, before)
        actual = build / label / 'ports' / rel if before != after else original
        assert actual.read_text(encoding='utf-8-sig') == after
        assert '"' + actual.resolve().as_posix() + '"' in response
        if before != after:
            assert record['source_ports'][rel]['compiled_sha256'] == sha(actual)
            ports[rel] = dict(original_sha256=expected, compiled_sha256=sha(actual), reasons=reasons)
        inputs += 1
    for extension, expected in record['output_sha256'].items():
        p = build / 'bin' / (record['assembly'] + '.' + extension)
        assert sha(p) == expected
        outputs[p.relative_to(build / 'bin').as_posix()] = expected
for asset in records['dependency_assets']:
    assert sha(build / 'dependencies' / Path(asset['member']).name) == asset['sha256']
comparison = json.loads(config_comparison.read_text())
assert comparison['all_text_metadata_equal'] and len(comparison['files']) == 102
output.write_text(json.dumps(dict(original_archive_sha256=sha(archive), original_snapshot_files_verified=len(originals), original_source_inputs_verified=inputs, explicit_production_ports=ports, output_sha256=outputs, original_NS2_and_feature_guards_preserved=True, production_compiler_warnings_as_errors=True, original_published_public_CLR_and_nullable_metadata_required=True, original_package_policy_text_assets_verified=len(comparison['files']), original_Roslyn12_host_compatibility_verified=False, full_upstream_suite_run=False, full_dependency_goal_complete=False), indent=2)+'\n')
print('PASS all',len(originals),'original files,',inputs,'source inputs,',len(ports),'explicit source ports, WAE and 102 generated policy assets')
