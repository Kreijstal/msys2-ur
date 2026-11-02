# Runtime10 native library bootstrap

Builds the complete original Windows shared compression and globalization
CMake targets from runtime10.0.5. Compression retains the pinned vendored
zlib-ng and Brotli sources. All library exports and source-calculated version
resources are checked. Installation stays in an isolated bootstrap directory.

The build replays the verified common MinGW port, applies two PDB-install
conditions and one guarded Windows SDK constant definition, and adapts private
resource-compiler inputs for llvm-windres. It records every change; the allocator
and its fail-fast behavior are retained. Generated version resources use the
original Arcade-calculated source version. No installed compiler or runtime
files are overwritten.

Checks use the original runtime10 stream header for deflate/inflate levels1/6/9,
a known CRC32 vector, Brotli round trip and direct ICU load/version calls.
Matching managed NET10 integration is a separate framework-build gate. Complete
shared-framework packaging, SDK10, PowerShell7.6, static/NativeAOT variants and
broader native/runtime compatibility remain open.
