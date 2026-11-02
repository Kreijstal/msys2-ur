#!/usr/bin/env python3
"""Stage the upstream CoreCLR plugin for the mingw-w64 headers and compiler."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]) / "src/powershell-native/nativemsh"
for relative in ("pwrshcommon/pwrshcommon.cpp", "pwrshplugin/pwrshclrhost.h"):
    path = root / relative
    text = path.read_text()
    old = "#include <atlbase.h>"
    assert text.count(old) == 1, path
    path.write_text(text.replace(old, "#if !CORECLR\n" + old + "\n#endif"))

# GNU windmc treats facility names as case sensitive.
path = root / "pwrshplugin/pwrshpluginerrorcodes.mc"
text = path.read_text()
assert "Facility=POWERSHELL" in text
path.write_text(text.replace("Facility=POWERSHELL", "Facility=PowerShell")
               .replace("84:FACILITY_POWERSHELL", "84:PS_NATIVE_FACILITY"))

# Modern SAL avoids the __in/__out names reserved internally by libc++.
annotations = {"__in": "_In_", "__out": "_Out_", "__in_opt": "_In_opt_",
               "__out_opt": "_Out_opt_", "__inout": "_Inout_"}
for path in root.rglob("*"):
    if path.suffix in (".cpp", ".h"):
        text = path.read_text()
        text = re.sub(r"\b(" + "|".join(annotations) + r")\b",
                      lambda m: annotations[m[0]], text)
        # Both callers advance past a literal '.' in a version number.
        text = text.replace("_wcsinc(pwchDot)", "(pwchDot + 1)")
        text = text.replace("WCHAR** wszRemainingVersionString", "const WCHAR** wszRemainingVersionString")
        text = text.replace("WCHAR* wszRemainingVersionStringAfter", "const WCHAR* wszRemainingVersionStringAfter")
        text = text.replace("LVER_PRODUCTVERSION_STR", 'L"700.0.0.0"')
        if path.name == "pwrshclrhost.cpp":
            text = text.replace("#pragma once\n", "")
        if path.name == "pwrshplugin.h":
            # An absent Param token must stay null; null + 7 became address 7
            # and made the next wcsstr access invalid memory during startup.
            assert text.count("param += 7;") == 2
            text = text.replace("param += 7;", "if (param != NULL) param += 7;")
            # Retain static lifetime without a writable-string-literal conversion.
            text = text.replace('version = L"3.0";',
                                'static wchar_t defaultVersion[] = L"3.0";\n                version = defaultVersion;')
        path.write_text(text)

# The mingw-w64 ntverp.h describes Windows 5.2, not this package.
version_template = '''#include <windows.h>
1 VERSIONINFO
FILEVERSION 700,0,0,0
PRODUCTVERSION 700,0,0,0
FILETYPE VFT_DLL
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904b0"
  BEGIN
   VALUE "FileDescription", "PowerShell WinRM plugin"
   VALUE "FileVersion", "700.0.0.0"
   VALUE "ProductVersion", "700.0.0.0"
   VALUE "OriginalFilename", "pwrshplugin.dll"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x0409, 1200
 END
END
'''
(root / "pwrshplugin/version.rc").write_text(version_template)
(Path(sys.argv[1]) / "src/PowerShell.Core.Instrumentation/version.rc").write_text(
    version_template.replace("pwrshplugin.dll", "PowerShell.Core.Instrumentation.dll")
                    .replace("PowerShell WinRM plugin", "PowerShell ETW resources"))
