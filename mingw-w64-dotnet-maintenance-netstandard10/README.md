# New maintenance dependencies for PowerShell7.6 and SDK10

Adds source-built System.Memory4.6.3, System.Runtime.CompilerServices.Unsafe6.1.2
and System.Threading.Tasks.Extensions4.6.3 alongside the older packaged versions.
The publisher's nuspec metadata pins all three to maintenance-packages commit
f62ca0009b038cab4725a720f386623a969d73ad. Unsafe retains its original IL source;
the C# implementations retain their original Release inputs and resource text.

The private build also rebuilds the exact Buffer4.6.1/Vector4.6.1 dependencies
from their original pinned source. Those two archives are used for closure tests
and are not shipped by this companion package. The existing maintenance package
continues to supply them and the older Memory/Unsafe/Tasks versions.

The original .NET Standard2.0 implementation, dependency groups, XML docs,
licenses and higher-framework inbox placeholders are retained. Checks exercise
the actual isolated portable implementations and ordinary source framework
asset selection with fresh source-only caches. Legacy Framework implementations
and the full PowerShell/SDK dependency goal remain open.
