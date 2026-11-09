"""Capture pinned codec declarations and independently measure native layouts."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

prefix, out = map(Path, sys.argv[1:])
here = Path(__file__).resolve().parent
pin = json.loads((here / 'vendor/source.json').read_text())
assert hashlib.sha256((here / 'vendor/micodec.h').read_bytes()).hexdigest() == pin['header_sha256']
source = out / 'header.c'
source.write_text('#include "codec-contract.h"\n')
compiler = str(prefix / 'bin/clang')
includes = ['-I' + str(here), '-I' + str(here / 'vendor')]
ast = subprocess.run([compiler, *includes, '-Xclang', '-ast-dump=json',
                      '-fsyntax-only', str(source)], check=True, capture_output=True, text=True)
names = ['_MI_ClientFT_V1', '_MI_ExtendedArray', '_MI_DeserializerCallbacks',
         '_MI_DeserializerFT_INTL', '_MI_ExtendedArrayFT']
records, typedefs, functions = {}, {}, {}


def visit(node):
    kind, name = node.get('kind'), node.get('name', '')
    if kind == 'RecordDecl' and node.get('completeDefinition') and name in names:
        records[name] = [{'name': f['name'], 'type': f['type']} for f in node.get('inner', [])
                         if f.get('kind') == 'FieldDecl']
    if kind == 'TypedefDecl' and name in ['MI_ExtendedArray_Delete',
                                        'MI_Deserializer_GetIncludedFileBuffer',
                                        'MI_Deserializer_FreeIncludedFileBuffer']:
        typedefs[name] = node['type']
    if kind == 'FunctionDecl' and name in ['MI_Application_NewSerializer_Mof',
                                         'MI_Application_NewDeserializer_Mof']:
        functions[name] = {'type': node['type'], 'parameters': [p['type'] for p in node.get('inner', [])
                                                              if p.get('kind') == 'ParmVarDecl']}
    for child in node.get('inner', []):
        visit(child)


visit(json.loads(ast.stdout))
assert set(records) == set(names) and len(typedefs) == 3 and len(functions) == 2
code = ['#include "codec-contract.h"', '#include <stddef.h>', '#include <stdio.h>',
        'int main(void) {', 'puts("{");']
for index, name in enumerate(names):
    code.append(f'printf("\\"{name}\\":{{\\"size\\":%zu,\\"offsets\\":{{", sizeof(struct {name}));')
    for number, field in enumerate(records[name]):
        comma = ',' if number + 1 < len(records[name]) else ''
        code.append(f'printf("\\"{field["name"]}\\":%zu{comma}", offsetof(struct {name}, {field["name"]}));')
    comma = ',' if index + 1 < len(names) else ''
    code.append(f'puts("}}}}{comma}");')
code.extend(['puts("}");', 'return 0;', '}'])
layout = out / 'layout.c'
layout.write_text('\n'.join(code) + '\n')
subprocess.run([compiler, *includes, '-std=c11', '-Wall', '-Wextra', '-Werror',
                str(layout), '-o', str(out / 'layout.exe')], check=True)
native_layout = subprocess.check_output([str(out / 'layout.exe')], text=True)
(out / 'native-layout.json').write_text(json.dumps(json.loads(native_layout), indent=2) + '\n')
schema = {'records': records, 'typedefs': typedefs, 'functions': functions, 'source': pin,
          'windows_header_sha256': hashlib.sha256((prefix / 'include/mi.h').read_bytes()).hexdigest(),
          'header_owner': subprocess.check_output(['pacman', '-Qo', str(prefix / 'include/mi.h')], text=True).strip(),
          'compiler': subprocess.check_output([compiler, '--version'], text=True).splitlines()[0]}
(out / 'native-schema.json').write_text(json.dumps(schema, indent=2) + '\n')
