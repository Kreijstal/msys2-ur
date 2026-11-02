# Source NET10 NuGet7.3 foundation bootstrap

SDK10.0.201 pins NuGet7.3.0-preview.1.11413 and source commit
bf048eb714eb6b1912ba868edca4c7cfec454841. This package builds the original VMR
NET10 Versioning,Frameworks,Common and LibraryModel projects:187 unchanged C#
inputs,original assembly/file/version/signing properties,and52 original XLF
satellites. Four source NuGet library archives retain upstream's individual
library satellite exclusion;the loose NET10 bootstrap layout retains all52.

Fresh checks compare1497 upstream public API declarations,392 exact neutral/
localized resource values,19 original version-range vectors,and actual SemVer,
NET10/platform/nearest-framework resolution,library model and24 concurrent
owned-file lock operations. Payload and NuGet archive asset bytes are checked.

This is the original NET10 source bootstrap profile. The remaining NuGet7.3
libraries,restore/build tasks,resolvers,additional original frameworks,and full
SDK10/WindowsDesktop10/PowerShell7.6 remain open. Runtime validation sources under
this doc directory contain original API/RESX/test inputs;they are explicitly a
consumer validation subset. `checks/check-installed.py PREFIX NEW_OUTPUT` runs
the focused check with native CLANG64 Python and installed source compiler tools.
