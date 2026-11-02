# Original NuGet7.3 NET10 libraries source bootstrap

The SDK10.0.201 pin maps to NuGet.Client bf048eb714eb6b1912ba868edca4c7cfec454841.
Original source-build/VMR conditions select NET10. Configuration, Packaging,
Protocol, DependencyResolver.Core, ProjectModel, Credentials, Resolver and Commands
compile from1081 unchanged production inputs. The four installed source foundation
libraries and exact original Newtonsoft13.0.3, ProtectedData8.0.0, PKCS8.0.1 and
Extensions6.0.0 dependencies are used. No published implementation is downloaded.

Assembly7.3.0.0, file7.3.0.11413, original public key and friend declarations are
retained. The original nuspec schema is embedded and source-built JSON generation
produces package metadata serializers. XML documentation is emitted. All104
original XLF satellites ship in the loose bootstrap layout; individual source
NuGet archives retain upstream's satellite exclusion. Package metadata preserves
the evaluated NET10 dependency graph with exact source-feed versions.

Checks preserve6615 upstream API declarations and verify10164 neutral/localized
values. Raw extra-API comparison is not performed. Owned offline tests cover
configuration/Unicode/DPAPI,pack/schema/archive,local feed lookup,transitive restore,
assets and generated package metadata. An installed consumer also restores the
actual packaged NuGet.Commands dependency graph from source-only local feeds.

This is a source bootstrap. Remaining NuGet build/pack/restore tasks, SDK resolver,
PackageManagement/XDT/MEF, additional original frameworks and tool profiles, full
upstream tests, original analyzer/tool integrations and complete SDK10/desktop10/
PowerShell7.6 integration remain required. Existing broad compatibility gates
also remain open. This bundle does not complete the full dependency goal.
