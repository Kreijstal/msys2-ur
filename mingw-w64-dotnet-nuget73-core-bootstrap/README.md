# NuGet7.3 NET10 foundation source recipe

Run `python make-source.py --update-checksum` after editing the standalone
workflow,then `makepkg --cleanbuild --force --noconfirm` in CLANG64. The recipe
builds the original VMR NET10 Versioning,Frameworks,Common and LibraryModel
profiles from the SDK10-pinned NuGet commit,including XML documentation and52
original satellites. It installs four source NuGet archives plus the loose
localized foundation layout.

Source/archive/output/reference,payload/API/resource and runtime checks are
included. This is a foundation prerequisite;remaining NuGet7.3 libraries,
restore/build tasks,additional original frameworks and full SDK10/PowerShell7.6
integration remain open. See [scope and consumer checks](workflow/README.md).
