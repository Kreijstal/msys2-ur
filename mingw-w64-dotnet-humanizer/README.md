# Humanizer.Core2.14.1.NET8 port

The current shipping recipe builds pinned Humanizer sources from commit
3ebc38de585fc641a04b0e78ed69468453b0f8a1 as a.NET8 port for CLANG64 and UCRT64.
It removes bundled binary inputs, restores from the installed source feed and
runs its.NET8 consumer checks.

The separate original-profile Standard2.0/NET8 reconstruction and its validation
remain in tests/humanizer-netstandard and source snapshot4ed960a. Those historical
profile requirements are separate from this PowerShell.NET8 shipping recipe.
