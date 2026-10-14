Builds the Windows implementation of System.Threading.AccessControl 8.0.0
from pinned .NET runtime C# sources, using the installed source-built .NET SDK.
The original native LibraryImport declarations use the SDK's source-built
interop generator. There are no downloaded managed binary inputs.

`makepkg --cleanbuild --force --noconfirm` builds the offline NuGet package and
checks real Windows named mutex, event and semaphore ACLs. The mutex check
also reopens the named object and checks contention from another thread.

Install the resulting pacman package to add System.Threading.AccessControl
8.0.0 to `/clang64/lib/dotnet/library-packs`.
