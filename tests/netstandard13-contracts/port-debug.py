"""Restore the lower Debug contract's six original conditional-call attributes."""
import re

def port(text, original):
    before, body = text.split('    public static partial class Debug\n', 1)
    body, after = body.split('    public static partial class Debugger\n', 1)
    assert 'Conditional' not in body
    signatures = re.findall(r'        public static void ([^\n]+) \{ \}', body)
    assert len(signatures) == 6
    for signature in signatures:
        # Each original member carries this attribute in the unchanged CoreFX ref source.
        needle = '[System.Diagnostics.ConditionalAttribute("DEBUG")]\n        public static void ' + signature + ' { }'
        assert needle in original, signature
    body = body.replace('        public static void ', '        [System.Diagnostics.ConditionalAttribute("DEBUG")]\n        public static void ')
    return before + '    public static partial class Debug\n' + body + '    public static partial class Debugger\n' + after
