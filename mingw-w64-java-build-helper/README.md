# Source-bootstrapped Java libraries and Apache Maven

These packages build Apache Maven 3.9.16, the default build plugins and every
library they need from source, without Maven, Gradle or any prebuilt jar,
on the JDK of `mingw-w64-openjdk` (itself bootstrapped without a binary JDK).
The approach follows GNU Guix (`gnu/packages/maven.scm`): each module is
compiled with `javac` and packed with `jar`, Modello is run directly for the
generated model classes, and the metadata a Maven build would add is produced
by other means.

## javabuild.sh

`java-build-helper` installs `share/java-build-helper/javabuild.sh`, sourced
by the PKGBUILDs (`jb_module`, `jb_plugin`, `jb_modello`, `jb_relocate`,
`jb_install`, `jb_loadcheck`, `jb_test`, ...), and a jar of tools:

| Tool | Replaces |
| --- | --- |
| `jb.MojoDescriptorProcessor` (annotation processor) | maven-plugin-plugin: writes `META-INF/maven/plugin.xml` from `@Mojo`/`@Parameter`/`@Component`, also for superclasses in other jars |
| `jb.PlexusComponentsProcessor` (annotation processor) | plexus-component-metadata: `META-INF/plexus/components.xml` from `@Component`/`@Requirement` and `@plexus.component` javadoc tags, merged with the static descriptors |
| Sisu's own `SisuIndexAPT6` | sisu-maven-plugin: `META-INF/sisu/javax.inject.Named` |
| `jb.ModelloRunner` | modello-maven-plugin (ModelloCli with the plugin's defaults) |
| `jb.Relocate` (ASM) | maven-shade-plugin relocations (surefire-shared-utils) |
| `jb.LoadCheck` | smoke test: loads every class of a jar and resolves its member signatures |
| `JUnit4Runner.java` | surefire for upstream JUnit 4 tests, with exclusions |
| `jb.Osgi` | PDE build / Tycho's reading of `MANIFEST.MF` and `build.properties`: OSGi compile class paths, bundle build order, qualifier replacement, `bundles.info` |
| `jb.DsProcessor` (annotation processor) | bnd's Declarative Services support (`.settings/org.eclipse.pde.ds.annotations.prefs`): `OSGI-INF/<component>.xml` from `@Component`/`@Reference`/`@Activate`, component property types |
| `jb.Bnd` | bnd's manifest analysis for third-party bundles: `Export-Package` (with `uses:`), `Import-Package` version ranges from the class path, osgi.ee, from bnd-style instructions |
| `ResolveCheck.java` | resolves the built bundles in Equinox together with the installed plug-ins and prints the framework's explanation for every unresolved one |

Generated descriptors were compared with those in the upstream jars: the
plugin descriptors of all six plugins (clean 3.2.0: plus a requiredMavenVersion upstream lacks), the Sisu indexes and Plexus
`components.xml` files are identical (upstream's generated `help` goal is not
produced).

## Layout

* `${MINGW_PREFIX}/share/maven-repo/<group path>/<artifactId>/<version>/` is
  a Maven repository of every packaged artifact: the jar and a *flattened*
  POM (no parent, no dependencyManagement; the compile/runtime/provided/optional
  dependencies with their exclusions, each pinned to the version that is
  packaged).  The upstream `pom.xml` is kept inside the jar under
  `META-INF/maven/<g>/<a>/` as Maven does.  Pinned versions mean that a
  dependent package is rebuilt when a dependency changes version.
* `${MINGW_PREFIX}/share/java/<artifactId>.jar` is a hard link to the jar in
  the repository (no second copy).
* Package names: `java-<artifact>` for libraries, `maven-<module>` for Apache
  Maven projects (`maven-wagon-*`, `maven-resolver-*`, `maven-surefire-*`,
  plugins), one split package per artifact, one PKGBUILD per upstream
  repository.  Only UCRT64 is built (the only JDK).
* `maven` installs `share/maven` (MAVEN_HOME: `bin/`, `conf/`, `lib/ext/`)
  and `bin/mvn{,.cmd}`, `bin/mvnDebug{,.cmd}`.  Its `bin/m2.conf` loads the
  jars from `share/maven-repo` and sets `maven.repo.local.tail` to it, so the
  packaged repository is a read-only tail of every local repository:
  `mvn -o` finds the packaged plugins with an empty `~/.m2`.
  `-Dmaven.repo.local.tail=` turns this off.

## OSGi bundles (Eclipse plug-ins)

`jb_bundle <dir>` builds an Eclipse plug-in project the way PDE build and
Tycho do, from its own `META-INF/MANIFEST.MF` and `build.properties`:

* every `source.<library>` is compiled with javac (`jars.compile.order`;
  `--release` from `Bundle-RequiredExecutionEnvironment`); the non-Java files
  of the source folders are copied next to the classes, except
  `exclude.<library>` patterns and `$JB_RESOURCE_EXCLUDES` (default
  `package.html`, as eclipse-platform-parent configures Tycho);
* the compile class path is the closure of `Require-Bundle`,
  `Import-Package` (optional ones included) and `Fragment-Host` over the
  bundles staged by the build (`$srcdir/jb-plugins`) and the installed
  plug-ins, plus the fragments of those hosts (the SWT win32 fragment), the
  OSGi annotations (versioning, bundle, DS), `additional.bundles`,
  `jars.extra.classpath` and, for API tools projects, the PDE API
  annotations, as PDE/Tycho add them;
* `.qualifier` in `Bundle-Version` becomes `$JB_QUALIFIER`, one fixed
  qualifier per pkgbase (the release's build id);
* with PDE's DS annotation support enabled, `jb.DsProcessor` writes the
  component descriptions into `OSGI-INF/` (and `Service-Component` if the
  manifest lacks it); its output is byte-identical to bnd's for the
  components of the Eclipse 2026-09 platform;
* `bin.includes`/`bin.excludes` decide the content of the jar, which is
  staged as `<bsn>_<version>.jar`.

`jb_bundles -- DIR...` sorts the bundles of a repository by their
dependencies and builds them (per-bundle options in
`JB_BUNDLE_OPTS_<bsn>` arrays), `jb_bundle_loadcheck` loads every class of a
bundle against its OSGi class path, `jb_osgi_resolvecheck` resolves the
staged bundles in Equinox with the installed ones, and `jb_plugins_install`
installs them.  Third-party libraries that are OSGi bundles upstream are
built with `jb_module ... -b <bnd instructions>` (jb.Bnd writes the
manifest) and installed with `jb_install --plugin`; jars of packages that
are not bundles are turned into bundles with `jb_wrap` (as Eclipse Orbit
does).

### Plug-in layout

* `${MINGW_PREFIX}/lib/eclipse/plugins/<bsn>_<version>.jar` is the single
  plug-in directory of all packaged bundles (Eclipse's own and third-party
  ones; the latter are hard links to the jar in `share/maven-repo`).
  Bundles with `Eclipse-BundleShape: dir` (the launcher library fragment) are
  installed unpacked.  An RCP application builds its configuration from
  it: `configuration/config.ini` (`osgi.framework`, `osgi.bundles` with
  `org.eclipse.equinox.simpleconfigurator`) and
  `configuration/org.eclipse.equinox.simpleconfigurator/bundles.info`, which
  `java jb.Osgi bundlesinfo --dirs ${MINGW_PREFIX}/lib/eclipse/plugins
  [--start BSN@LEVEL:true]... OUT ROOT-BSN...` writes for a set of root
  bundles and everything they need (or `--all`).
* `${MINGW_PREFIX}/lib/eclipse/eclipse.exe` and `eclipsec.exe` are the native
  launcher; next to a copy of them, `eclipse.ini` names the launcher jar
  (`-startup`) and library (`--launcher.library`) in the plug-in directory.
* Package names: `eclipse-<bsn without org.eclipse., dots as dashes>`, one
  split package per bundle, one PKGBUILD per upstream repository (the
  Equinox and eclipse.platform runtime bundles depend on each other and are
  one pkgbase, `eclipse-platform-core`; the UI bundles of eclipse.platform
  are built with eclipse.platform.ui in `eclipse-platform-ui`).

## Build order

java-build-helper, hamcrest, junit4, javax-inject, aopalliance,
javax-annotation-api, plexus-utils, plexus-xml, plexus-classworlds,
plexus-interpolation, plexus-containers, commons-cli, commons-io,
commons-lang3, commons-codec, slf4j, jspecify, error-prone-annotations,
j2objc-annotations, jsr305, asm, guava, guice, sisu, plexus-cipher,
sonatype-plexus-build-api, plexus-build-api, httpcomponents-core,
httpcomponents-client, jansi, modello, plexus-sec-dispatcher,
maven-shared-utils, gson, maven-wagon, maven-resolver, maven,
maven-plugin-tools, maven-filtering, maven-resources-plugin, qdox,
plexus-languages, plexus-compiler, maven-shared-incremental,
maven-compiler-plugin, xz, zstd-jni, aircompressor, commons-compress,
plexus-io, plexus-archiver, maven-file-management, maven-archiver,
maven-jar-plugin, maven-install-plugin, maven-clean-plugin,
maven-common-artifact-filters, maven-surefire, ant.

Eclipse RCP (2026-09): java-osgi, java-felix, java-jakarta-inject-api,
java-jakarta-annotation-api, java-jna, java-bouncycastle, eclipse-orbit,
java-jetbrains-annotations, java-bnd, java-aries-spifly, java-jsvg,
eclipse-pde, eclipse-jdt, eclipse-swt, eclipse-platform-core, eclipse-p2,
eclipse-emf, eclipse-platform-ui, eclipse-gef-classic, eclipse-lsp4j.
