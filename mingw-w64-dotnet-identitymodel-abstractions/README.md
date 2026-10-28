Microsoft.IdentityModel.Abstractions6.35.0 from source
===================================================

Pinned source is commitc94c7fc235501d478221e979062bd8837a55575b, as recorded in
the published package. The complete original project/common imports and all nine
C# files are retained for the source.NET8 target. Eight implementation files are
unchanged. Properties/AssemblyInfo.cs has only the three release version values
updated, matching the original updateAssemblyInfo.ps1 CI operation and frozen
published assembly/file/informational identities. Original signing key/token
31bf3856ad364e35 is preserved with public signing, without policy changes.

Only build metadata changes: source.NET8 target, offline source feed, original
public signing, package-validation/SDK trimming downloads disabled, original
IsTrimmable assembly metadata retained, and two build-only vendor SourceLink/
FxCop references omitted. No production algorithm changes. Actual compiler
inputs, original/prepared metadata, source implementation/reference/XML bytes,
original license and source/test inventories are gated.

The NuGet ships lib/net8.0 and ref/net8.0, compiler documentation, original MIT
license, this README and provenance. All published net6 API declarations and
signing/file/informational identities are compared as metadata only. Vendor DLLs
never compile or execute as implementations.

Checks adapt only Moq fixture construction to a concrete subclass in the six
original TelemetryEventDetails test cases; assertion bodies/derived helpers are
retained. Additional checks cover interface dispatch, all six property overloads,
null keys/values, live dictionary views, overwrite/Unicode/extensibility,
constants and original disabled logger/telemetry singleton contracts. Nothing
sends telemetry or authentication traffic. Fresh consumers use the installed
source feed and verify loaded DLL location/bytes plus ref/runtime asset selection.

The supported target is net8.0. Broader upstream/framework/trimming matrices and
MSAL/Azure/PSResourceGet integration remain separate work. Actual source CLR8.0.0
servicing is unchanged.
