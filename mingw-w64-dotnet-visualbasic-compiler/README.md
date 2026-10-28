# Source-built Roslyn Visual Basic command-line compiler 4.9.2

This companion tool uses all eleven original vbc/shared driver sources and the
two-file private RazorCompiler helper from Roslyn commit
9934fb9e3527e1c0c51314e57d4aab30f97e8f9e. It depends on separately source-built
Common/VisualBasic 4.9.2 libraries and retains their thirteen satellite cultures.
Assembly identity 4.9.0.0/31bf3856ad364e35 is public-signed with the upstream key.

The relative vbc49.cmd wrapper lives in compiler-packs/roslyn-vb-4.9.2. Use
VbcToolPath for that directory, VbcToolExe=vbc49.cmd, and UseSharedCompilation=false.
This leaves the installed SDK compiler unchanged. VBCSCompiler server, full
Toolset/IDE coverage and full PowerShell integration are separate work.

Checks cover CLI version, Unicode/space response-file paths, compiler errors,
relocation under compiler-packs, a real source-built 4.9 analyzer and incremental
VB source generator through MSBuild, executed generated output, and an expected
analyzer error followed by correction. The installed runtime reports8.0.0; SDK
package labels do not establish later servicing fixes.
