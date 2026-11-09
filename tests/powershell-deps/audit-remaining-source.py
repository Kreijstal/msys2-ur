"""Inventory current source gaps; does not prove runtime compatibility.

Usage: python3 audit-remaining-source.py MMI_PRISTINE SQL_PRISTINE GO_MSSQLDB NEW_JSON
Replays the current MMI recipe in a temporary directory and the compiled SqlClient
SNIProxy overlay. Requires local pinned source checkouts; never changes them.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[2]
mmi_original, sql_original, go, output = map(Path, sys.argv[1:])
assert not output.exists(), output
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
mmi_inputs = json.loads((repo/'tests/mmi-execution-context/package-results-20261109.json').read_text())
for relative, digest in mmi_inputs['input_sha256'].items():
    assert sha(repo/relative) == digest, relative
sql_record = repo/'tests/sqlclient-lpc/package-results-20261109.json'
if not sql_record.exists():
    sql_record = repo/'tests/sqlclient-browser/package-results-20261109.json'
sql_inputs = json.loads(sql_record.read_text())
assert all(v['build_exit_code'] == v['installed_exit_code'] == 0 for v in sql_inputs['environments'].values())
for relative, digest in sql_inputs['input_sha256'].items():
    assert sha(repo/relative) == digest, relative
mmi_audit = json.loads((repo/'tests/mmi-execution-context/source-audit-20261109.json').read_text())
assert len(mmi_audit['patches']) == 21
for entry in mmi_audit['patches']:
    assert entry['zero_fuzz_exit_code'] == 0
    assert sha(repo/'mingw-w64-dotnet-mmi3'/entry['name']) == entry['sha256']
with tempfile.TemporaryDirectory(prefix='powershell-remaining-source-') as scratch:
    stage = Path(scratch)/'mmi'
    subprocess.run([sys.executable, str(repo/'mingw-w64-dotnet-mmi3/prepare.py'),
                    str(mmi_original.resolve()), str(stage), '--patched', '--public-sign'],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sources = sorted(stage.rglob('*.cs'))
    markers = []
    for p in sources:
        for number, line in enumerate(p.read_text(encoding='utf-8-sig').splitlines(), 1):
            if 'throw new NotImplementedException' in line:
                relative = p.relative_to(stage).as_posix()
                if relative == 'CimProperty.cs':
                    category = 'base_property_setter_overridden_by_both_concrete_implementations'
                elif relative.endswith('MI_ExtendedArray.cs'):
                    category = 'internal_debug_validation_helper'
                elif relative.endswith('MI_Application.cs') and number == 52:
                    category = 'non_null_internal_session_creation_callbacks'
                elif relative.endswith('MI_Deserializer.cs') and number == 440:
                    category = 'non_zero_internal_callback_context'
                else:
                    category = 'unsupported_serialization_format_guard'
                markers.append(dict(path=relative, line=number, category=category, source_sha256=sha(p)))
    assert len(markers) == 12, markers
    subclasses = []
    for p in sources:
        text = p.read_text(encoding='utf-8-sig')
        if re.search(r'class\s+\w+\s*:\s*CimProperty\b', text):
            assert 'public override bool IsValueModified' in text
            subclasses.append(p.relative_to(stage).as_posix())
    assert len(subclasses) == 2
    assert 'internal CimProperty()' in (stage/'CimProperty.cs').read_text()
    session = (stage/'CimSession.cs').read_text()
    assert re.search(r'DestinationOptionsHandle,\s*null,\s*out extendedErrorHandle', session)
    deserializer = (stage/'Serialization/CimDeserializer.cs').read_text()
    assert 'classes, null, IntPtr.Zero, out used' in deserializer
    mof = (stage/'Serialization/CimMofDeserializer.cs').read_text()
    assert 'NewDeserializer(MI_SerializerFlags.None, MI_SerializationFormat.MOF' in mof
    mmi = dict(compiled_CSharp_files=len(sources), not_implemented_markers=markers,
               concrete_CimProperty_implementations=subclasses,
               source_sha256={p.relative_to(stage).as_posix(): sha(p) for p in sources},
               public_non_null_session_callback_not_exposed=True,
               scope='Textual guarded-path inventory; does not prove full reachability, ownership, exceptions or remote compatibility')
    sql_audit_path = sql_inputs.get('source_audit_files', {}).get('clang64', 'tests/sqlclient-browser/evidence-20261109/clang64-source-sni-audit.json')
    sql_audit = json.loads((repo/sql_audit_path).read_text())
    entry = next(e for e in sql_audit['production_overlays'] if e['original_path'].endswith('/SNI/SNIProxy.cs'))
    original = sql_original/entry['original_path']
    assert sha(original) == entry['original_sha256']
    overlay = Path(scratch)/'SNIProxy.cs'
    overlay.write_text(original.read_text(encoding='utf-8-sig'))
    for patch in [entry] + entry.get('additional_patches', []):
        p = repo/'mingw-w64-dotnet-sqlclient'/patch['patch_name']
        assert sha(p) == patch['patch_sha256']
        subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(p)], cwd=scratch,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert sha(overlay) == entry['overlay_sha256']
    text = overlay.read_text()
    protocol = re.search(r'internal enum Protocol\s*\{([^}]+)\}', text).group(1)
    protocols = [s.strip() for s in protocol.split(',')]
    if sql_inputs.get('LPC_endpoint_routing_implemented', False):
        assert protocols == ['TCP', 'NP', 'None', 'Admin', 'LPC']
        assert 'case "lpc"' in text and 'InferLocalConnectionDetails()' in text
        assert 'PipeHostName = ".";' in text and 'SQLLocal' in text
    else:
        assert protocols == ['TCP', 'NP', 'None', 'Admin']
        assert 'case "lpc"' not in text and 'case TdsEnums.LPC' not in text
    factory = next(e for e in sql_audit['production_overlays'] if e['original_path'].endswith('/TdsParserStateObjectFactory.Windows.cs'))
    factory_original = sql_original/factory['original_path']
    assert sha(factory_original) == factory['original_sha256']
    factory_stage = Path(scratch)/'TdsParserStateObjectFactory.Windows.cs'
    factory_stage.write_text(factory_original.read_text(encoding='utf-8-sig'))
    factory_patch = repo/'mingw-w64-dotnet-sqlclient'/factory['patch_name']
    assert sha(factory_patch) == factory['patch_sha256']
    subprocess.run(['patch', '--fuzz=0', '-p1', '-i', str(factory_patch)], cwd=scratch,
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert sha(factory_stage) == factory['overlay_sha256']
    assert 'public static bool UseManagedSNI { get; } = true;' in factory_stage.read_text()
    sql = dict(compiled_SNIProxy_sha256=sha(overlay), protocols=protocols,
               lpc_backend_implemented='LPC' in protocols, proprietary_SNI_binary_fallback_enabled=False,
               source_evidence=sql_audit_path)
commit = subprocess.check_output(['git', '-C', str(go), 'rev-parse', 'HEAD'], text=True).strip()
assert commit == '6c346b78c201e490ca2585f0987ddd8f6b4f06a3'
files = ['sharedmemory/sharedmemory_windows.go', 'internal/np/namedpipe_windows.go',
         'sharedmemory_test.go', 'LICENSE.txt']
assert 'SQLLocal' in (go/files[0]).read_text()
assert 'protocol != "Shared memory"' in (go/'sharedmemory_test.go').read_text()
reference = dict(repository='https://github.com/microsoft/go-mssqldb', commit=commit,
                 files={f: sha(go/f) for f in files},
                 target='Local-only SQLLocal instance endpoint; no SQL Browser lookup; existing named-pipe stream machinery',
                 upstream_live_test='SELECT net_transport FROM sys.dm_exec_connections WHERE session_id = @@SPID must return Shared memory',
                 upstream_test_executed_here=False, port_implemented_here=sql['lpc_backend_implemented'],
                 license='BSD-3-Clause; retain notices if adapting the source')
record = dict(scope='PowerShell7.4.20/.NET8.0.31 current source and remaining gates',
              audit_tool_sha256=sha(Path(__file__)),
              audit_command='python3 tests/powershell-deps/audit-remaining-source.py MMI_PRISTINE SQL_PRISTINE GO_MSSQLDB NEW_JSON',
              mmi_package_version='3.0.0-15', sqlclient_package_version=sql_inputs['package_version'],
              mmi=mmi, sqlclient=sql, lpc_source_reference=reference,
              full_dependency_goal_complete=False)
output.write_text(json.dumps(record, indent=2)+'\n')
print('PASS current source inventory: 152 MMI inputs, 12 categorized guards; SqlClient LPC '+('present' if sql['lpc_backend_implemented'] else 'absent')+'; pinned Microsoft LPC reference')
