# Original Humanizer netstandard2.0 prerequisite

The [formal Humanizer recipe](../../mingw-w64-dotnet-humanizer/README.md) now
builds and installs the original Standard2.0 target alongside the retained NET8
port. Both targets pass full original API/resource/runtime, package/cache and
installed-file checks using installed source tools. See
[formal package results](package-results-20261028.txt). The records below describe
the earlier private bootstrap; original Standard1.0/NET6 variants and the full
PowerShell dependency objective remain incomplete.

The unchanged Humanizer2.14.1 project now builds for its declared netstandard2.0
target. This supplies the asset needed by the Roslyn4.14 Workspaces variants;
the installed earlier source package contains the net8 asset.

Source commit: `3ebc38de585fc641a04b0e78ed69468453b0f8a1`.
Archive SHA256: `a98e80e9ca23c4ec17699481bd4b145e5477ba6f2ea8082956724428048c38db`.
The project and all199 selected production C# files remain unchanged. The build
disables the parent directory's versioning/source-link tool imports and supplies
the pinned version information explicitly. The original signing key is retained;
its complete public key is derived independently and checked against the output.
The three original licenses are packaged under distinct names and compared byte
for byte against the archive inputs.

A fresh netstandard2.0 consumer checks casing, irregular inflection, English and
German number words, resources and ordinals. An isolated runtime context loads
the exact source implementation and every original resource set, including
satellites the SDK may omit from a consumer's copy list. All50 sets/3,698 strings
and1,113 original public/protected declarations pass. The API gate compares the
original target's compiled source declarations and checked shapes with metadata.
All255 original source/project/resource/key/license inputs and9 actual compiler/
consumer package references pass the archive/cache checks.

Copy this workflow to `humanizer-ns20-workflow` and place the pinned archive beside
it as `humanizer-3ebc38de.tar.gz`. The source SDK8 and .NET Standard feed are needed;
the audit helper also uses the preceding source net8 Roslyn4.14/runtime9 feeds.
Preparation and consumer directories must be new:

```sh
ROOT=/c/codex-dotnet10/c1.1BZ8KU
/usr/bin/python3 "$ROOT/humanizer-ns20-workflow/prepare.py" "$ROOT" "$ROOT/humanizer-ns20-1"
bash "$ROOT/humanizer-ns20-workflow/build.sh" "$ROOT/humanizer-ns20-1"
/usr/bin/python3 "$ROOT/humanizer-ns20-workflow/check.py" "$ROOT" "$ROOT/humanizer-ns20-1" "$ROOT/humanizer-ns20-1/consumer1"
```

All final commands returned zero. Exact results and hashes are in
[the JSON record](source-results-20261028.json) and
[the logs](source-results-20261028.txt). This private package supports the needed
target; formal complete package/metadata/attribute/install validation and the
full PowerShell dependency objective remain open.
