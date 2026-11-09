"""Compare actual MMI delegate metadata with independently compiled mi.h types.

This checks declarations, storage and export availability, not provider behavior.
"""
import hashlib
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
native = json.loads((out / 'native-schema.json').read_text())
managed = json.loads((out / 'managed-schema.json').read_text())
prefix = 'Microsoft.Management.Infrastructure.Native.'
signatures = {s['name'].split('+')[-1]: s for s in
              managed['bridge_signatures'] + managed['other_signatures']}


def arguments(signature):
    start = signature.index('(*)(') + 4
    depth, current, parts = 0, '', []
    for char in signature[start:]:
        if char == ')' and depth == 0:
            if current:
                parts.append(current.strip())
            return parts
        if char == ',' and depth == 0:
            parts.append(current.strip())
            current = ''
            continue
        depth += (char == '(') - (char == ')')
        current += char
    raise AssertionError(signature)


results = []


def compare(name, signature, target):
    delegate = signatures[target]
    convention = 'Cdecl' if signature.endswith('__attribute__((cdecl))') else 'StdCall'
    assert signature.endswith('__attribute__((' + convention.lower() + '))'), signature
    assert delegate['calling_convention'] == convention, name
    returns = signature.split('(*)', 1)[0].strip()
    expected = {'void': 'System.Void', 'MI_Result': prefix + 'MI_Result',
                'MI_Module *': 'System.IntPtr'}[returns]
    assert delegate['return_type'] == expected, name
    args = arguments(signature)
    assert len(args) == len(delegate['parameters']), name
    for c, m in zip(args, delegate['parameters']):
        if '*' in c:
            assert m['type'] == 'System.IntPtr' and m['marshal_as'] is None, (name, c, m)
        elif c == 'MI_Boolean':
            assert m['type'] == 'System.Byte' and m['marshal_as'] is None, (name, c, m)
        elif c == 'MI_Uint32':
            assert m['type'] == 'System.UInt32' or (
                m['type'] == prefix + 'MI_WriteMessageChannel' and m['enum_size'] == 4), (name, c, m)
        else:
            assert c in ['MI_Result', 'MI_Type', 'MI_PromptType', 'MI_OperationCallback_ResponseType'], c
            assert m['type'] == prefix + c and m['enum_size'] == 4, (name, c, m)
    results.append({'native': name, 'managed': target, 'parameters': len(args),
                    'calling_convention': convention, 'signature': signature})


mapping = {'PromptUser': 'PromptCallback', 'WriteError': 'ErrorCallback',
           'WriteMessage': 'MessageCallback', 'WriteProgress': 'ProgressCallback',
           'Instance': 'InstanceCallback', 'Indication': 'IndicationCallback',
           'Class': 'InstanceCallback', 'StreamedParameter': 'StreamedCallback'}
for suffix, target in mapping.items():
    name = 'MI_OperationCallback_' + suffix
    compare(name, native['typedefs'][name]['qualType'], target)
for suffix, target in [('PromptUser', 'ReplyCallback'), ('WriteError', 'ReplyCallback'),
                       ('Instance', 'Acknowledge'), ('Indication', 'Acknowledge'),
                       ('Class', 'Acknowledge'), ('StreamedParameter', 'Acknowledge')]:
    name = 'MI_OperationCallback_' + suffix
    compare(name + '.reply_or_ack', arguments(native['typedefs'][name]['qualType'])[-1], target)
compare('MI_Deserializer_ClassObjectNeeded', native['typedefs']['MI_Deserializer_ClassObjectNeeded']['qualType'],
        'MI_Deserializer_ClassObjectNeededNative')
compare('MI_MainFunction', native['typedefs']['MI_MainFunction']['qualType'], 'MI_MainFunction')
for field in native['records']['_MI_SessionCallbacks'][1:]:
    compare('MI_SessionCallbacks.' + field['name'], field['type']['qualType'],
            'MI_SessionCallbacks_' + field['name'][0].upper() + field['name'][1:] + 'Native')
close = native['records']['_MI_SessionFT'][0]
assert close['name'] == 'Close'
compare('MI_SessionFT.Close.completion', arguments(close['type']['qualType'])[-1],
        'MI_Session_Close_CompletionCallback')
assert len(results) == 19 and len(signatures) == 14
assert managed['storage_size'] == 72 and managed['storage_offsets'] == list(range(0, 72, 8))
assert managed['populated_callbacks'] == 8 and managed['context_is_null']
assert managed['root_count_before'] == managed['root_count_after']
assert not managed['provider_connection_attempted']
exports = {e['module']: e['symbols'] for e in managed['exports']}
assert exports == {'mi.dll': ['MI_Application_InitializeV1', 'mi_clientFT_V1'],
                   'mimofcodec.dll': ['MI_Application_NewSerializer_Mof', 'MI_Application_NewDeserializer_Mof']}

# These are recorded import policies, not independent private codec prototypes.
methods = {m['name']: m for m in managed['pinvoke_methods']}
assert len(methods) == 6
for name in ['MI_Application_InitializeV1', 'MI_Application_NewSerializer_Mof', 'MI_Application_NewDeserializer_Mof']:
    method = methods[name]
    assert method['calling_convention'] == 'Cdecl' and method['return_type'] == prefix + 'MI_Result'
    assert len(method['parameters']) == 4
    strings = [p for p in method['parameters'] if p['type'] == 'System.String']
    assert len(strings) == 1 and strings[0]['marshal_as'] == 'LPWStr'
for name in ['LoadLibrary', 'FreeLibrary', 'GetProcAddress']:
    assert methods[name]['calling_convention'] == 'Winapi'
assert methods['LoadLibrary']['parameters'][0]['marshal_as'] == 'LPWStr'
assert methods['FreeLibrary']['return_type'] == 'System.Boolean'
assert methods['FreeLibrary']['return_marshal_as'] == 'Bool'
assert methods['GetProcAddress']['parameters'][1]['marshal_as'] == 'LPStr'
record = {'callback_signature_comparisons': len(results), 'distinct_managed_delegates': len(signatures),
          'outer_parameters_compared': sum(r['parameters'] for r in results), 'comparisons': results,
          'callback_storage_bytes': 72, 'populated_callback_slots': 8, 'system_exports_found': 4,
          'pinvoke_policies_checked': 6, 'declaration_divergences': [],
          'provider_behavior_verified': False, 'private_codec_prototypes_verified': False,
          'full_dependency_goal_complete': False,
          'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out / 'comparison.json').write_text(json.dumps(record, indent=2) + '\n')
print(f"PASS {len(results)} callback signature comparisons, 14 delegates, 9 storage slots and 4 system exports")
