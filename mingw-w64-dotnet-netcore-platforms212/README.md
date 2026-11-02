# Original source Platforms 2.1.2 graph

This preserves all515 RID definitions and ordered fallback edges from CoreFX6851cc781ad2ff33d4a0f429a6fc1ab85abaff86. The original project declares2.1.2. Its runtime.json is semantically identical to the pinned original published graph; source line endings are retained. No executable payload is present. This is the original data package required by CodePages4.5.1, with the original empty Standard1.0 marker and no invented runtime implementation.

The source SDK8 only packages the graph. Checks verify source bytes, graph closure/cycles and NuGet expansion for every RID, representative Windows/Linux/macOS chains, and a fresh exact-version PackageReference restore with byte-equal cache/archive data. The full historical CoreFX package toolchain is not replayed. The PowerShell dependency goal remains open.

    makepkg --cleanbuild --force --noconfirm
    bash /clang64/share/doc/dotnet-netcore-platforms212/check.sh NEW_OUTPUT
