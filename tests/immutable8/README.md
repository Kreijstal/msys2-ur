# Exact System.Collections.Immutable8.0.0 source package

TemplateEngine's NuGet6.13.2 closure requires Immutable>=8.0.0. This package
provides the original8.0.0 release from runtime commit
5535e31a712343a63f5d7d796cd874e563e5ac14, identified by the published nuspec.
The source archive and selected/shared input hashes are pinned. Production
sources are unchanged.

The original NET8 profile, Microsoft public key, assembly8.0.0.0 and release
file8.0.23.53103 are retained. Version/resource generation executes the original
Arcade8 task sources at39042b4048580366d35a7c1c4f4ce8fc0dbea4b4 with original
release build ID20231031.3. The compiler is the installed source Csc5.3 NET10
bootstrap host; production references use source NET8.0.31. Original NET7/NET6,
NS2/NETFramework profiles and full upstream/analyzer integration remain open.

Runtime checks execute the produced DLL in an isolated load context and assert
its path/file version, excluding the serviced inbox copy. They cover immutable
persistence, builder snapshots, Unicode/comparers, sorted sets, stacks/queues,
spans/marshal, frozen dictionaries/sets, atomic updates and errors. The neutral
resource set has16 values; its portable PDB association is checked.

Reference compilation retains the original NET8 conditions, including exclusion
of the pre-NET8 CollectionBuilder polyfill. API comparison includes visible
interfaces and excludes internal implementation interfaces omitted from reference
assemblies. Focused fixtures verify internal-interface additions are accepted
and loss of a public interface is rejected. Full custom-attribute and generic-
constraint metadata comparison is not claimed.

Actual source NuGet7.3 restore verifies that the NET10 consumer selects these
original NET8 assets. Existing Immutable9 and the shared NET8 runtime must
coexist unchanged. TemplateEngine's other strict restore/API gates and the full
PowerShell dependency goal remain open.
