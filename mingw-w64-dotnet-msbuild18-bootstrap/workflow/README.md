# Source MSBuild18 NET10 bootstrap

This package builds the SDK10.0.201-pinned MSBuild18.3.0-release-26113-113
source commit228caa11ad0046ccb599530abd9aba4e1979b5e9. All six primary NET10
projects are compiled from1326 original Compile items plus104 exact source-only
Roslyn package inputs. The original pinned Arcade version task and MSBuild
override produce file version18.3.0.11413. All53 XLF satellites,118 resource
sets and23597 values are compiled and checked. The original English XLF is
preserved; ResourceManager uses main-assembly English because English is neutral.

Runtime dependencies are exact source-built SolutionPersistence1.0.52 and NET9
OOB9.0.11 packages. Windows runtime assets are selected for Windows execution.
The installed payload retains original task registration and props/targets.
Fresh checks cover version,German help,original default task registration,Unicode
file tasks,parallel builds in two distinct processes and every localized value.
The shell and CMD launchers select the source NET10 host for this process only.
The tool folder is under `lib/dotnet10/build-packs`: original MSBuild worker
startup searches two parent directories for its host, so this placement also
selects NET10 for child nodes when SDK8 is installed alongside it.

Use `msbuild18-bootstrap` from CLANG64 or `msbuild18-bootstrap.cmd` in the
installed tool directory. This is a bootstrap prerequisite for the source SDK10
compiler tasks. Full native RC/icon/content layout,NETFramework/NETStandard
profiles,SDK-style restore/build and the complete SDK10/WindowsDesktop10/
PowerShell7.6 graph remain open. Installed package success does not establish
completion of those requirements. Source and output audits are under this doc
directory; `checks/check-installed.py PREFIX NEW_OUTPUT` repeats the focused
installed check using native CLANG64 Python.
