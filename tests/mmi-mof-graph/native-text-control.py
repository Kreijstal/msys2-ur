"""Run with Windows Python; observe codec text without loading managed MMI."""
import ctypes
import json
from pathlib import Path
import sys

library = ctypes.CDLL(str(Path(sys.argv[1]).resolve()))
read = library.graph_text
read.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int,
                 ctypes.c_wchar_p, ctypes.c_uint]
read.restype = ctypes.c_int
source = Path(sys.argv[2]).read_text(encoding='utf-8')
schema = source.split('const string Schema="""')[1].split('""";')[0]
rows = source.split('const string Rows="""')[1].split('""";')[0]
results = {}
for encoding in ['utf-16', 'utf-16-le', 'utf-8-sig', 'utf-8']:
    for instances, text in [(0, schema), (1, schema + '\n' + rows)]:
        data = text.encode(encoding)
        buffer = ctypes.create_string_buffer(data)
        output = ctypes.create_unicode_buffer(512)
        code = read(buffer, len(data), instances, output, len(output))
        assert code == 0
        expected = 'second λ' if instances else 'derived 雪'
        if encoding.startswith('utf-8'):
            expected = expected.encode('utf-8').decode('latin-1')
        assert output.value == expected
        results[encoding + '/' + str(instances)] = {'setup': code, 'text': output.value}
print(json.dumps({'managed_MMI_loaded': False, 'observations': results}, indent=2))
