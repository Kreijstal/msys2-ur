"""Run with Windows Python: inspect the codec without loading managed MMI."""
import ctypes
import json
from pathlib import Path
import sys


class Report(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint32) for name in
                ['status', 'used', 'count', 'scalar_type', 'array_type', 'array_size', 'scalar_flags']]


library = ctypes.CDLL(str(Path(sys.argv[1]).resolve()))
parse = library.oracle_parse
parse.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_wchar_p, ctypes.POINTER(Report)]
parse.restype = ctypes.c_int
document = 'class MSYS2_Empty { uint32 Id; };\n'
results = {}
for encoding in ['utf-16', 'utf-16-le', 'utf-8-sig', 'utf-8']:
    data = document.encode(encoding)
    buffer = ctypes.create_string_buffer(data)
    report = Report()
    assert parse(buffer, len(data), 0, 'Default', ctypes.byref(report)) == 0
    assert report.status == 0 and report.count == 0 and report.used == len(data)
    results[encoding] = {'result': report.status, 'rows': report.count, 'used': report.used,
                         'input_bytes': len(data)}
print(json.dumps({'managed_MMI_loaded': False, 'native_only_empty_result_controls': results}, indent=2))
