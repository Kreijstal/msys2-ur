# CodeDom 4.4 original Standard 2.0 source bootstrap

Builds the original System.CodeDom 4.4.0 netstandard2.0 implementation and
separate compiler reference from CoreFX commit
8321c729934c0f8be754953439b88e6e1c120c24. Production C# inputs are unchanged.
The implementation and reference each preserve their original 1,354 public API
entries, assembly 4.0.0.0/cc7b13ffcd2ddd51 and netstandard2.0 dependency identity.
The reference retains its original parameter names and type initialization flags.

The disclosed build host is the source SDK8/NET8 and a private original Roslyn4.4
CLI rebuilt against installed source Roslyn4.4 libraries. Source compiler5
bootstraps that CLI. Language7.3 is the explicit bootstrap parser setting;
warnings remain errors with only SDK default1701/1702 suppressions. Original
CODEDOM/Release source conditions, signing key, file version and 23 resource
values are preserved. Informational version explicitly identifies this source
bootstrap. Generated resource properties and assembly metadata replace legacy
build-tools outputs. Published DLLs are metadata baselines only.

The check builds a fresh exact-version NS2 consumer against the reference asset
and runs the old implementation in an isolated load context. It checks CSharp/VB
generation, keywords, Unicode, code-tree validation, diagnostics, temporary-file
ownership and original unsupported compiler paths. Both generated programs are
compiled with the source SDK and executed on source NET8.

    makepkg --cleanbuild --force --noconfirm
    /usr/bin/python3 /clang64/share/doc/dotnet-codedom44-bootstrap/check.py \
      /clang64/share/doc/dotnet-codedom44-bootstrap NEW_OUTPUT \
      /clang64/lib/dotnet/library-packs

Only the original NS2 profile is packaged. NET461 and other framework assets,
the original 2017 build-tools host, full upstream test matrix and execution on
original historical runtimes remain unverified. Dataflow4.6 and MSBuildTasks16
remain separate work. This does not complete the PowerShell dependency goal.
