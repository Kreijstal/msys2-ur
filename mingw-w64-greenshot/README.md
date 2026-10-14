Builds the Full edition of Greenshot's 1.4 development snapshot at
6b1ba7c4e4539c44503c5bb580438b31853068a8 with the source-built MSYS2 .NET 8
Windows desktop SDK and offline NuGet feed. The original source targets .NET
Framework 4.8; prepare.py retargets the four application/build projects and
removes build-only package dependencies in favor of installed SDK assemblies.

The compatibility patch updates native WinRT projection/activation, named
pipe and mutex ACL construction (including reopening an existing mutex with
only synchronize/modify rights), security exception types, and the default
configuration encryption provider. Existing editor serialization formats and
the deserialization whitelist are retained. The application explicitly enables
.NET 8's legacy BinaryFormatter compatibility switch for those formats.

The source archive is audited and upstream managed/native binary build inputs
are removed. All restored libraries come from the installed source-built feed.
Optional external plugin projects and the separate MCP helper are outside the
four-project application build graph.

Run `makepkg --cleanbuild --force --noconfirm` in a CLANG64 shell. Its check()
validates editor serialization, rejection of unknown serialized types,
configuration cipher compatibility, complete assembly type loading, and
native Direct3D/Share manager interop, then runs the application's --no-run
startup path using an isolated configuration directory.

After installation, launch `greenshot`. The native GUI launcher locates the
shared MSYS2 .NET runtime relative to itself and supplies the native DLL path.

Validation on win11 reached normal application startup with an isolated INI
configuration and passed editor, WinRT interop and CLI smoke checks. The SSH
session does not provide the Windows notification platform, and the machine
has no Windows Graphics Capture service. Interactive capture and toast delivery
therefore still need testing in a desktop session with those services available.

The upstream pipe ACL explicitly denies the Windows Network SID. OpenSSH logon
tokens carry that SID on this host, so cross-process IPC is intentionally denied
in the SSH session. An attempted desktop scheduled-task smoke test produced no
result; its temporary task was removed and no test process remained.
