# Roslyn compile-time MSBuild17.11 prerequisites

These source API prerequisites are now rebuilt privately by the installed
NET10 Roslyn task bootstrap recipe. The task package passes original compiler
targets and default registration on MSBuild18;this does not complete formal
MSBuild17 dependency packaging. See
[`task package evidence`](../roslyn5/net10-msbuild-tasks-package-results-20261029.txt).

SDK10 Roslyn5.3 declares MSBuild17.11.48 compile-time package dependencies with
runtime assets excluded. Its source pin is
`02bf66295b64ab368d12933041f7281aad186a2d`; original NuGet repository metadata,
archive hash and the source-only Collections package pin are recorded in
[`source-pins-20261029.json`](source-pins-20261029.json).

All six primary original NET8 projects compile:1195 original Compile items plus
37 unchanged Collections source-package files. These outputs supply the original
compile-time MSBuild API version to the NET10 Roslyn task build; execution of
those tasks uses the SDK10-pinned source MSBuild18. Both Csc/Vbc command-line
paths and automatic shared compiler-server operation pass. Original source,
resource/project archive comparisons and350 current output/reference hashes pass.
See [`commands and evidence`](../roslyn5/net10-msbuild-tasks-results-20261029.txt).

These remain private bootstrap prerequisites. OOB references currently use
explicit source SDK8 DLLs; formal exact NuGet dependency resolution, original
Arcade file version, complete localization, original additional frameworks and
formal MSBuild17 packages remain open. The file version17.11.48.0 is explicitly
a bootstrap value. The complete17.11 CLI has only been compiled, while its
Framework/Utilities/Tasks APIs have been consumed by the NET10 task compilation.

The focused native Windows Python commands are:

```sh
python ../msbuild18/prepare-plan.py PINNED_ARCHIVE PLAN --msbuild-17.11-net8
bash ../msbuild18/evaluate.sh PLAN SOURCE_EVALUATOR_DLL
python build.py PLAN NEW_BUILD_OUTPUT
```

The matching source-only Collections archive must be under
`PLAN/../msbuild1711-source-packages`. An optional third build argument reuses
only successful project outputs after validating their source, reference,
output hashes, file version and compatibility macros. Fresh outputs are required.
