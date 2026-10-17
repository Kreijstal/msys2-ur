# DBeaver CE dependency bootstrap (UCRT64)

Source-built runtime libraries for the DBeaver CE 26.2.2 source tree. The
`dbeaver-dependencies` package installs Eclipse 4.41, DBeaver common APIs,
third-party OSGi bundles and DBeaver's nine composite library bundles.
The DBeaver application itself is a separate packaging step.

Install from the msys2-ur rolling repository in a UCRT64 shell:

```
pacman -S mingw-w64-ucrt-x86_64-dbeaver-dependencies
```

The existing repository is
`https://github.com/Kreijstal/msys2-ur/releases/tag/x11-shared-20260731`.

Build with the source-bootstrapped OpenJDK package and `java-build-helper`.
Build the `java-*` recipes before `dbeaver-orbit` and `dbeaver-bundles`;
build `eclipse-orbit-ant`, `eclipse-platform-extra`, `eclipse-ecf` and
`eclipse-p2-extra` before this aggregate recipe. Each PKGBUILD records its
exact package prerequisites and SHA-256-pinned source inputs.

No downloaded library bytecode is used. Maven Central `*-sources.jar`
archives supply Java sources; all `.class` files are compiled locally.
XMLBeans and OOXML `.xsb` schema metadata are retained as runtime data.
ICU's upstream data-only archives supply Unicode and time-zone resources;
the build checks that these contain no Java classes. WKG's parsers are
generated from its grammars with the source-built ANTLR tool.

Source pins:

- DBeaver: tag `26.2.2`.
- dbeaver-common: `5658d5409f14f6d99aa76d42692960666029ede9`.
- dbeaver-deps-ce: `047e8447ffddb0a8818216a91e5aad28e78c59bf`.
- WKG fork: `46b107715434ea3260659319e7261cd2f5e51f53`.
- ECF: `a512085c8abe32ceb930178a4c85284c0691d46f`.
- Eclipse Platform, Equinox and p2: tag `R4_41`.

Build profiles:

- Java 21 is the library baseline; the packaged Eclipse workbench uses
  the source-built OpenJDK 28 runtime.
- JSch uses its upstream JDK 9–19 implementations on the Java 21 baseline,
  with the JDK 23/24 multi-release implementations preserved. The optional
  junixsocket native backend is omitted; the JDK Unix-domain socket backend
  handles supported Java versions.
- Apache HTTP client uses OpenJDK JSSE. The optional native Conscrypt
  strategies are omitted.
- Batik retains SVG rendering and the Rhino JavaScript backend. Its optional
  Tcl/Jacl and Python/Jython adapters are omitted. The Rhino package supplies
  the engine and XML support; its separate shell/debugger applications are omitted.
- MSV retains its validator library. Its legacy command-line UI relies on
  a removed private JDK catalog resolver and is omitted.
- XML Resolver uses the JDK SAX/JAXP parser and catalog resolution. Optional
  Jing catalog validation and the external Xerces XNI adapter are omitted.
- JavaParser and legacy collection libraries compile against their upstream
  Java 8 API surface to avoid collisions with Java 21 collection methods.
- XMLBeans retains its library and schema compiler. Its two Maven plugin
  entry points and Maven plugin descriptor are omitted.
- Saxon retains its native and W3C DOM trees. Optional Axiom, DOM4J, JDOM2,
  XOM adapters and the interactive Gizmo shell are omitted.
- EJML's Lombok-generated value/accessor methods are expanded in a pinned
  source patch. EJML and its optional MFL adapter are jointly compiled for
  bootstrap, then rebuilt and packaged as separate artifacts.
- Eclipse p2's optional Ant-task side JARs are omitted. The Ant core and
  launcher are packaged as an OSGi bundle using their actual 1.10.15 version.
  DBeaver's feature pin to the historical `org.apache.ant` version 1.99.1
  needs adjustment when the application feature is packaged.
- The SLF4J and Logback bundles use Equinox registered buddy loading to
  discover and bind the Java service provider across bundle class loaders.
- DBeaver composites use the upstream `FRAG.FMF` exports/imports and bundle
  versions, with nested locally built JARs. The nested-library inventory
  records SHA-256 digests in each composite's META-INF directory.
- Javassist retains its Java 21 legacy Applet overload. Its class-loading
  check excludes that one class on the OpenJDK 28 build host, where Applet
  no longer exists.

`makepkg --cleanbuild --force --noconfirm` runs the checks in this recipe.
They exercise SQL/JEXL, JDBC pooling, XLSX/Unicode/schema data and the
temp-backed streaming reader, geometry,
EPSG resources, matrix inversion/MAT files, PNG chart rendering, XPath,
SAT solving, SSH cryptography, GraphQL and an actual loopback Jetty HTTP
request. A separate consumer runs representative operations inside Equinox
and rejects unresolved installed bundles. Build-only test prerequisites
are listed in `makedepends`.
