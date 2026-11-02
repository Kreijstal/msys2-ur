"""Restore two lower reference contracts without editing raw extracted source."""
import re

def serialization(text, original):
    assert 'class KnownTypeAttribute' not in text
    match = re.search(r'    \[System\.AttributeUsageAttribute[^\n]+\]\n    public sealed partial class KnownTypeAttribute : System.Attribute\n    \{.*?\n    \}', original, re.S)
    assert match
    return text + '\nnamespace System.Runtime.Serialization\n{\n' + match[0] + '\n}\n'

def object_model(text):
    # The original emitter marked both accessors of these abstract events
    # Synchronized. Spell out that method flag for the bootstrap compiler.
    pattern = r'(?m)^(        )(event [^;\n]+;)'
    events = re.findall(pattern, text)
    assert len(events) == 4, events
    return re.sub(pattern, r'\1[method: System.Runtime.CompilerServices.MethodImpl((System.Runtime.CompilerServices.MethodImplOptions)32)]\n\1\2', text)
