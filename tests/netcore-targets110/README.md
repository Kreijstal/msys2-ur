# Original Microsoft.NETCore.Targets 1.1.0 metadata port

Preserves all 22 runtime rows, 97 versioned package mappings and 14 support
profiles in the original graph. The original single empty lib/netstandard1.0
marker and license/notice text are retained. No implementation DLLs or
executables are included; implementations belong to the declared runtime
packages and remain separate work.

CoreFX source4d1af962ca0fede10beb01d197367c2f90e92c97 declares version1.1.0,
the lineup package owners, support profiles and original marker. NuGet's array
serialization of singleton support values is reproduced as a source projection;
the original published graph baseline stays unchanged. Runtime mappings are
retained as pinned declarative data. The original BuildTools lineup generator
has not been replayed.

Checks use source SDK8 NuGet APIs for every runtime dependency/version range and
merge the graph with the installed source Platforms1.1 graph. Windows, Linux and
macOS dependency lookups must select the original package names. Fresh NS1.0,
NS1.3 and NET8 restore-only consumers verify exact version1.1.0 and archive cache
bytes. These checks do not claim that the mapped runtime packages have been
built, or that historical runtimes have executed.

Native Windows Python:

    python.exe -X utf8 check.py SOURCE_FEED NEW_OUTPUT CLANG64_PREFIX

The complete PowerShell dependency goal remains incomplete.
