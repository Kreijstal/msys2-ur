# SDK10 logging abstractions source bootstrap

Builds original NET10 Microsoft.Extensions.DependencyInjection.Abstractions and
Microsoft.Extensions.Logging.Abstractions 10.0.2 from SDK-pinned VMR44525024,
and the logging package's original netstandard2.0 Roslyn4.4 generator. The source
snapshot verifies5719 VMR files; the three profiles compile74 unchanged C# inputs.
All original resource/version helper bytes match the SDK's Arcade helper inputs.
Versioning uses original servicing BuildID20251212.105: assembly10.0.0.0,
file10.0.225.61305 and MicrosoftAspNetCore key. No production C# is changed.

The generator retains its original Microsoft.CodeAnalysis.CSharp.Workspaces4.4
reference. The installed source Roslyn4.4 package's recorded transitive support
closure uses Immutable/Metadata9.0.0,Memory4.6.2,Buffers4.6.1 and Unsafe6.1.1;
those actual versions are recorded rather than relabeled as older minimums.
The original non-CoreApp nullable-warning policy is retained. The generator's
existing resource-language attribute is preserved without duplicating it.

Runtime validation compiles with the original generator and executes structured
Unicode logging, event IDs, enabled guards, scopes and DI descriptors/keyed
services/constructor activation. Invalid source must report SYSLIB1017.
All16 neutral/localized resource sets,576 values,13 original NS2 satellites,
three identities and portable PDB associations are checked.

The CLR contract comparison matches all404 reference declarations with zero
missing/extra/changed signatures. Logging also matches nullable metadata. The
strict DI nullable comparison FAILS with25 differences: its pinned reference
source uses nonnullable factory keys while the pinned implementation accepts
nullable keys, among related keyed-service annotation differences. The original
bytes are preserved. The separate baseline check ensures the complete known
report is unchanged; it does not turn the strict nullable gate green. The
full original metadata-compatibility requirement remains open.

This isolated bootstrap package supplies two NET10 NuGet archives and the
original shipped generator/analyzer layout. Additional original frameworks,
full upstream/analyzer integration and complete logging/configuration/console
closure remain required. These prerequisites support the exact SDK10 template
engine and driver graph; they do not complete PowerShell7.6/SDK10 or earlier
runtime/native compatibility gates.
