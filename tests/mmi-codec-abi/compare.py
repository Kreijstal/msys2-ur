"""Verify the codec declarations MMI actually consumes against Microsoft headers."""
import hashlib
import json
from pathlib import Path
import sys

out = Path(sys.argv[1])
native = json.loads((out / 'native-schema.json').read_text())
layout = json.loads((out / 'native-layout.json').read_text())
managed = json.loads((out / 'managed-schema.json').read_text())
prefix = 'Microsoft.Management.Infrastructure.Native.'
assert managed['platform'] == 'X64'
mapping = {
    '_MI_ClientFT_V1': 'MI_SerializationFTHelpers+MI_ClientFT_V1',
    '_MI_ExtendedArray': 'MI_ExtendedArray+MI_ExtendedArrayMembers',
    '_MI_DeserializerCallbacks': 'MI_DeserializerCallbacks+MI_DeserializerCallbacksNative',
    '_MI_DeserializerFT_INTL': 'MI_Deserializer+MI_MOFDeserializerFT',
    '_MI_ExtendedArrayFT': 'MI_ExtendedArray+MI_ExtendedArrayFT',
}
client_fields = ['g_applicationFT', '_sessionFT', '_operationFT', '_hostedProviderFT',
                 '_serializerFT', '_deserializerFT', 'g_subscriptionDeliveryOptionsFT',
                 'g_destinationOptionsFT', 'g_operationOptionsFT', '_utilitiesFT']
rename = {'arr': 'array', 'ft': 'deserializerFT', 'DeserializeClassArray': 'DeserializeClassArray_MOF',
          'DeserializeInstanceArray': 'DeserializeInstanceArray_MOF'}
structure_results = []
for name, target in mapping.items():
    item = next(m for m in managed['layouts'] if m['name'] == target)
    assert item['size'] == layout[name]['size'], name
    assert len(item['fields']) == len(native['records'][name]), name
    for index, (c, m) in enumerate(zip(native['records'][name], item['fields'])):
        expected = client_fields[index] if name == '_MI_ClientFT_V1' else rename.get(c['name'], c['name'])
        assert m['name'].removeprefix('reserved_').lower() == expected.lower(), (name, c, m)
        assert m['offset'] == layout[name]['offsets'][c['name']], (name, c, m)
        if name == '_MI_ClientFT_V1':
            assert m['type'] == 'System.IntPtr', m
    structure_results.append({'native': name, 'managed': target, 'size': item['size'],
                              'fields_compared': len(item['fields'])})


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


def parameter(c, m, charset):
    c = c.removeprefix('const ')
    t = m['type'].removeprefix(prefix)
    if c == 'void *':
        assert t == 'System.IntPtr', (c, m)
    elif c == 'MI_Uint8 *':
        assert t == 'System.IntPtr', (c, m)
    elif c == 'MI_Uint8 **':
        assert t == 'System.IntPtr&', (c, m)
    elif c == 'MI_Uint32 *':
        assert t == 'System.UInt32&', (c, m)
    elif c == 'MI_Uint32':
        assert t == 'System.UInt32' or (t == 'MI_SerializerFlags' and m['enum_size'] == 4), (c, m)
    elif c == 'MI_Char *':
        assert t == 'System.String' and (m['marshal_as'] == 'LPWStr' or charset == 'Unicode'), (c, m)
    elif c == 'MI_DeserializerCallbacks *':
        assert t == 'MI_DeserializerCallbacks+MI_DeserializerCallbacksNative', (c, m)
    elif c in ['MI_ClassA **', 'MI_InstanceA **', 'MI_Instance **']:
        assert t == 'MI_NativeObject+IndirectPtr', (c, m)
    elif c in ['MI_Deserializer *', 'MI_Application *', 'MI_Serializer *',
               'MI_OperationOptions *', 'MI_ClassA *', 'MI_ExtendedArray *']:
        assert t == 'MI_NativeObject+DirectPtr', (c, m)
    else:
        raise AssertionError((c, m))


results = []


def signature(name, c, m, args=None, convention='StdCall'):
    assert c.endswith('__attribute__((' + convention.lower() + '))'), (name, c)
    assert m['calling_convention'] == convention, (name, m)
    expected_return = 'System.Void' if c.startswith('void ') else prefix + 'MI_Result'
    assert m['return_type'] == expected_return, (name, m)
    args = arguments(c) if args is None else args
    assert len(args) == len(m['parameters']), (name, args, m)
    for ca, mp in zip(args, m['parameters']):
        parameter(ca, mp, m.get('charset'))
    results.append({'native': name, 'managed': m['name'], 'parameters': len(args), 'signature': c})


delegates = {s['name'].split('+')[-1]: s for s in managed['signatures']}
for field in native['records']['_MI_DeserializerFT_INTL'][1:]:
    signature(field['name'], field['type']['qualType'],
              delegates['MI_Deserializer_' + field['name'] + '_MOF'])
for c, m in [('MI_ExtendedArray_Delete', 'MI_ExtendedArray_Delete'),
             ('MI_Deserializer_GetIncludedFileBuffer', 'GetIncludedFileBuffer'),
             ('MI_Deserializer_FreeIncludedFileBuffer', 'FreeIncludedFileBuffer')]:
    signature(c, native['typedefs'][c]['qualType'], delegates[m])
methods = {m['name']: m for m in managed['methods']}
assert len(methods) == 2
for name, function in native['functions'].items():
    signature(name, function['type']['qualType'], methods[name],
              [p['qualType'] for p in function['parameters']], 'Cdecl')
assert len(results) == 7
assert managed['xml_serializer_entries_matched'] == 3
assert managed['xml_deserializer_entries_matched'] == 6
assert not managed['provider_connection_attempted']
record = {'layouts_compared': structure_results, 'signature_comparisons': results,
          'parameters_compared': sum(s['parameters'] for s in results),
          'xml_serializer_entries_matched': 3, 'xml_deserializer_entries_matched': 6,
          'declaration_divergences': [], 'full_provider_behavior_verified': False,
          'full_dependency_goal_complete': False,
          'scope_notes': ['Windows x64 ABI; reserved1 UInt64 and IntPtr are both eight bytes',
                          'MI_ClassA/MI_InstanceA pointer parameters use the MI_Array prefix of MI_ExtendedArray',
                          'Unused optional codec callbacks remain null pointers; their unused prototypes are not audited'],
          'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(out / 'comparison.json').write_text(json.dumps(record, indent=2) + '\n')
print(f"PASS five codec layouts, seven signatures/{record['parameters_compared']} parameters and nine XML table entries")
