"""Explicit source ports required by the source SDK's enabled style analyzers."""
from pathlib import Path
import hashlib
import json
import sys

def apply(out):
    source=out/'source';base=source/'src/PolySharp.SourceGenerators'
    changes={
        'Diagnostics/Analyzers/UnsupportedCSharpLanguageVersionAnalyzer.cs':[
            ('ImmutableArray.Create(UnsupportedCSharpLanguageVersionError)','[UnsupportedCSharpLanguageVersionError]')],
        'PolyfillsGenerator.TypeForwards.cs':[
            ('ImmutableArray.Create(\n        "System.Index",\n        "System.Range",\n        "System.Runtime.CompilerServices.IsExternalInit",\n        "System.Runtime.CompilerServices.RequiresLocationAttribute")',
             '[\n        "System.Index",\n        "System.Range",\n        "System.Runtime.CompilerServices.IsExternalInit",\n        "System.Runtime.CompilerServices.RequiresLocationAttribute"]'),
            ('return ImmutableArray<string>.Empty;','return [];')],
        'Extensions/AnalyzerConfigOptionsProviderExtensions.cs':[
            ('return ImmutableArray<string>.Empty;','return [];')],
        'PolyfillsGenerator.Polyfills.cs':[
            ('return ImmutableArray<AvailableType>.Empty;','return [];')],
        'Helpers/EquatableArray{T}.cs':[
            ('public static implicit operator EquatableArray<T>(ImmutableArray<T> array)\n    {\n        return FromImmutableArray(array);\n    }',
             'public static implicit operator EquatableArray<T>(ImmutableArray<T> array) => FromImmutableArray(array);'),
            ('public static implicit operator ImmutableArray<T>(EquatableArray<T> array)\n    {\n        return array.AsImmutableArray();\n    }',
             'public static implicit operator ImmutableArray<T>(EquatableArray<T> array) => array.AsImmutableArray();'),
            ('public static bool operator ==(EquatableArray<T> left, EquatableArray<T> right)\n    {\n        return left.Equals(right);\n    }',
             'public static bool operator ==(EquatableArray<T> left, EquatableArray<T> right) => left.Equals(right);'),
            ('public static bool operator !=(EquatableArray<T> left, EquatableArray<T> right)\n    {\n        return !left.Equals(right);\n    }',
             'public static bool operator !=(EquatableArray<T> left, EquatableArray<T> right) => !left.Equals(right);')]
    }
    record={}
    for name,replacements in changes.items():
        path=base/name;original=path.read_bytes();text=original.decode('utf-8')
        for before,after in replacements:
            assert text.count(before)==1,(name,before)
            text=text.replace(before,after)
        path.write_bytes(text.encode('utf-8'))
        record[path.relative_to(source).as_posix()]=dict(original_sha256=hashlib.sha256(original).hexdigest(),ported_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),replacements=len(replacements))
    (out/'source-ports.json').write_text(json.dumps(dict(reason='Keep original Lang13/strict/WAE/style enforcement with source SDK analyzers',files=record,warning_suppressions_added=False),indent=2)+'\n')
    p=out/'source-inputs.json';data=json.loads(p.read_text());data['production_source_changes']=len(record);data['source_ports']=record;p.write_text(json.dumps(data,indent=2)+'\n')
    print('PASS applied explicit analyzer-compatible source ports:',len(record),'files; no warning suppressions')

if __name__=='__main__':apply(Path(sys.argv[1]).resolve())
