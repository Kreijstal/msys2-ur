This additional integration check consumes a completed source analyzer package
and its fresh installed-check restore. It invokes the original installed Roslyn
CSharp core targets and source MSBuild18 task, imports NuGet's generated props and
targets, and verifies selection of the package's generated warnings-as-errors
globalconfig. The exact API must compile; a nullable API mismatch must fail.
This does not establish a complete SDK10 build.

Run on CLANG64 with Windows Python:

```
python.exe -X utf8 check.py E:/msys64/clang64 INSTALLED_CHECK/restore NEW_OUTPUT
```
