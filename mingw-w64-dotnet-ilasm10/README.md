# Source native ILAsm10

Builds the original native .NET10.0.5 IL assembler from runtime commit
`081d220c0a773ffb7c6bea6b48727833576a65ef`, with the pinned existing MinGW
host/CoreCLR port and two ILAsm resource/CET changes. The target builds with
CLANG64/UASM and the declared source SDK8. It uses no private compiler, runtime
or cDAC build outputs. Only the `ilasm` target is built; no CoreCLR runtime or
cDAC stub is packaged.

Source preparation extracts native inputs, removes prebuilt binaries and applies
all patches at zero fuzz. An independent audit compares source files with the
pinned archive and replays the patches on pristine inputs. Actual assembler
compilation units and generated version headers are checked. The original
Arcade version task and three upstream vectors supply the reproducible source
file version `10.0.526.11800`; this is not a vendor build number.

The resource port uses the actual `.rsrc$02` section index, retaining bounds and
type validation, and compares complete eight-byte COFF section names. Tests
assemble unchanged original Unsafe6.1.1 IL from its pinned source commit, verify
all 42 public methods and the Microsoft public key, and read the emitted portable
PDB. Three valid resource layouts preserve VERSIONINFO bytes exactly; invalid
symbol-section and truncated inputs are rejected. An emitted IL loop executes
on the source .NET8 runtime, using a source filename containing Unicode and spaces.
The executable's AMD64 identity, CET marker and source version are verified.

Run `python make-source.py`, then in Windows CLANG64 run
`MINGW_ARCH=clang64 makepkg-mingw -C -f --noconfirm`.
After installation, the explicit entry point is `ilasm10.exe`. Repeat
`check.py PREPARED UNSAFE_ARCHIVE NEW_OUTPUT /clang64/bin/ilasm10.exe` and run
`check-image.py PREPARED /clang64/bin/ilasm10.exe` with native Python to validate
the installed image. Existing assembler selections are unchanged.

This supplies an assembler prerequisite for the original maintenance libraries.
Formal maintenance/runtime9/Roslyn generator packages, complete runtime/SDK10,
PowerShell7.6 and the full dependency objective remain open.
