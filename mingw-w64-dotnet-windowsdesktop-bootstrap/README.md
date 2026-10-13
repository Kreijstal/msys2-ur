# Source WindowsDesktop bootstrap

This recipe builds WPF 8.0.0 and the approved interim WinForms 7.0.20 port from
source using the source-built .NET 8 SDK and C++/CLI compiler. Its framework
version is `8.0.0-bootstrap.wpf.8.0.0`. It includes the desktop SDK/markup tasks,
targeting/runtime packs, all managed shipping implementations, native graphics,
pen input and the source PresentationNative replacement.

The native text/paragraph/NLS replacement is still partial (currently 91 of 139
imported exports). Bidi, full paragraph/pagination layout and other documented text behavior
remain unfinished. This experimental package is part of the ongoing bootstrap;
it does not establish complete upstream WPF compatibility. WinForms 8 awaits its
source metadata-generator bootstrap. The framework records this scope and its
source/assembly/dependency hashes in `source-bootstrap.json`.

The recipe recompiles both desktop components in its private build tree; no
existing desktop installation is used as an implementation input. The installed
source-built core SDK/compiler and trusted MSYS2 native/Mono tools are its seeds.
Executable fixtures in the upstream source archives are deleted before building.
Native libc++/ICU dependencies are bundled for self-contained publish, with their
MSYS2 package owners, hashes and licenses recorded.

Run `python make-source.py` to export the pinned local bootstrap commit, then
build in a CLANG64 shell with `makepkg-mingw -s`. An interactive Windows desktop
is needed by `check()`. It validates the real bridge assemblies, printer
enumeration, a local XPS document, automation/Ribbon/interop, native graphics,
text-decoration callback geometry and public raster output, and ordinary offline
WPF/WinForms build and self-contained publish.

This package replaces the WinForms-only bootstrap package because both own the
desktop SDK. It preserves the freshly source-built legacy WinForms framework and
pack versions for existing interim applications. The installed core .NET SDK
remains a separate package.

Normal projects use `net8.0-windows` and `<UseWPF>true</UseWPF>` with
`Microsoft.NET.Sdk`. With no external NuGet dependencies, an empty package feed
is sufficient. `dotnet publish -r win-x64 --self-contained true` produces an app
with the source framework and its native dependencies.

Release 8.0.0-2 adds original native text-decoration callbacks. Public tests
verify underline, strikethrough, overline and baseline with custom pens across
compacting GC. This improves existing exports; the imported-symbol count stays
58/139.

Release 8.0.0-3 adds explicit and incremental tab layout, dotted leaders,
caret/selection geometry and original tab enumeration callbacks. It also fixes
embedding all four source composite-font resources in PresentationCore, needed
for font fallback. A wrap that cuts an aligned field and moves its stop beyond
the column still returns an explicit error; bidi tabs and exact legacy leader
spacing remain unfinished. Native imported-symbol coverage stays 58/139.

Release 8.0.0-4 chooses aligned-tab line breaks using the retained field and
validates geometry again after prefix remeasurement/reshaping. Its normal SDK
checks cover all four WPF alignments, whole/split fields, continuation and
indivisible leading-tab overflow. This resolves the release 3 aligned-field
wrapping error; full bidi/paragraph layout and exact legacy leader spacing
remain unfinished. Imported-symbol coverage stays 58/139.

Release 8.0.0-5 adds original inline object format/draw callbacks, atomic
geometry/wrapping and the documented break-condition table. Normal SDK checks
cover fixed/flexible TextEmbeddedObject and actual TextBlock InlineUIContainer
rendering and point hits. SDK validation unlinks replacement desktop hardlinks
before overlaying source output. Position-dependent objects following aligned
tabs, full bidi/paragraph layout and justification remain unfinished. Native
imported-symbol coverage remains 58/139.

Release 8.0.0-6 adds regular inter-word justification through original nominal
and shaped-glyph expansion callbacks, retaining real caret/selection and drawing
advances. Normal SDK checks cover Latin/Indic Ideal/Display paragraphs and an
actual justified TextBlock. Final/hard-break/no-opportunity lines stay ragged.
Aligned-tab/other justification modes, ink insertion, compression/optimal
algorithms and full bidi/paragraph layout remain incomplete; imported-symbol
coverage remains 58/139.

Release 8.0.0-7 adds paragraph minimum/maximum widths using retained Unicode,
cluster and object break geometry. Normal SDK checks cover nominal/Indic text,
NBSP, hard lines, trailing/empty content, cached calls across GC, original
FormattedText.MinWidth and intrinsic/wrapped TextBlock layout. Full RTL,
hyphenation/compression/optimal algorithms and paragraph/natural-language
behavior remain incomplete; imported-symbol coverage remains 58/139.

Release 8.0.0-8 adds owned paragraph object registrations/document contexts
and Line Services penalty-resource wrapper lifetimes. Native ABI/callback/
rollback tests and original PtsContext Ideal/Display with and without penalty
resources pass through normal SDK and portable publishes. Imported-symbol
coverage increases to 65/139. FlowDocument now reaches missing FsCreatePageFinite;
page layout, penalty scoring/optimal breaking and full bidi/natural-language
behavior remain unfinished.

Release 8.0.0-9 adds paragraph rectangle/bounding-box transforms for all eight
writing directions, with aliasing and overflow checks. The source ABI generator
now emits page/section/track/text/line records and checks 277 field sizes/offsets
against original managed WPF, including both arms of nested unions. Native
imported-symbol coverage increases to 67/139; FlowDocument pagination still
requires FsCreatePageFinite and the remaining page services.

Release 8.0.0-10 adds callback-driven finite single-column text pages and
recursive container subtracks. Original FlowDocument now lays out and renders
short/wrapped paragraphs in Ideal/Display modes through ordinary SDK projects,
with cached pages, real page counts, compacting GC and dispatcher cleanup.
Native gates check exact paragraph/line/break ownership and failure rollback.
Imported-symbol coverage increases to 80/139. Multi-page continuation, bottomless
layout, multiple columns, RTL page text, optimal/keep policies and tables/floaters
remain unfinished; overflow rejects without claiming the remaining text fits.

Release 8.0.0-11 adds bottomless pages/subtracks and full-page replacement on
text updates. Original FlowDocumentScrollViewer and RichTextBox now render,
scroll and edit in Ideal/Display modes through normal SDK projects and portable
publishes. It also corrects release 10 line query coordinates: WPF expects page
coordinates, so paragraphs previously could overlap and scrolled text disappear.
Two-color raster checks verify page padding and separated paragraph rows.
Imported-symbol coverage is 83/139. Multi-page continuation, advanced paragraph
layout, incremental/interruptible formatting and full bidi/optimal/native
language behavior remain incomplete.

Release 8.0.0-12 adds finite multi-page text continuation through original
container/line callbacks. Page and subtrack break records independently retain
resume state after page disposal; cloned records have separate identities.
Native gates validate exact four-page ranges, cleanup and failed callback
rollback. Original WPF paginator checks render six pages, cover all 1278 source
characters exactly once and verify content/page mapping in both formatting
modes through shared-framework and portable SDK consumers. Imported-symbol
coverage is 86/139. Tiny pages that cannot fit a line, hard/keep/optimal policies,
multiple columns, advanced layout and full bidi/native language remain unfinished.

Release 8.0.0-13 adds finite multi-column text flow using original width/gap
callbacks and an owned page/section/column query hierarchy. Original WPF tests
render two columns and their rule across 12 Ideal/9 Display pages, cover all 1278
source characters exactly once, verify glyphs in both columns and a clear gap,
and validate cleanup after a later-column failure. Shared-framework and portable
SDK consumers pass. Imported-symbol coverage is 89/139. Balancing/span areas,
hard/keep/optimal/forced-line policies, tables/floaters/figures, advanced algorithms
and full bidi/native language behavior remain incomplete.

Release 8.0.0-14 adds explicit paragraph page/column breaks, correct destination
suppression and propagation through nested Section/container callbacks. Page
breaks preserve remaining empty columns and the next source position; column
breaks resume within the same page. Original flat/nested WPF raster and source
mapping checks pass in Ideal/Display through normal SDK and portable publishes.
Imported-symbol coverage remains 89/139. Keep/optimal/forced-line policies,
balancing/span areas, tables/floaters/figures, advanced algorithms and full
bidi/native language behavior remain incomplete.

Release 8.0.0-15 adds KeepTogether paragraph deferral and nested fresh-area
propagation. Original WPF comparisons show that the same paragraph splits with
keep disabled and moves intact with keep enabled, in flat/nested documents and
Ideal/Display. Oversized kept paragraphs make bounded progress, and kept text
can move intact into the next column of the same page. Native resource/source
checks and shared-framework/portable SDK consumers pass. Coverage remains
89/139; KeepWithNext chains, optimal/forced-line policies, balancing/span areas,
advanced algorithms, tables/floaters/figures and full bidi/native language remain
incomplete.

Release 8.0.0-16 adds KeepWithNext heading chains with margin-preserving rollback
and the implied unbroken heading paragraph. Original WPF comparisons cover one/
three-heading flat/nested chains, nonzero margins, multi-line headings, oversized
chain progress and heading/body glyphs together in the next column. Native
source/resource checks and normal shared-framework/portable SDK consumers pass.
Imported-symbol coverage remains 89/139. Optimal/forced-line policies, balancing/
span areas, tables/floaters/figures, advanced algorithms and full bidi/native
language behavior remain incomplete.

Release 8.0.0-17 adds forced progress for finite areas too short to fit a line.
The formatter retains one actual original line, its glyph geometry and the exact
next source position, bounds used height by the available extent and propagates
the forced-result flag through containers and pages. Native flat/nested tests
cover undersized and zero-height areas, terminal continuations and exact cleanup.
Original WPF flat/nested documents, including keep constraints, finish on tiny
pages at the requested size in Ideal/Display with exact character/page mapping
and retained oversized glyph ink. Shared-framework/portable SDK consumers pass.
Imported-symbol coverage remains 89/139. Optimal policies, balancing/span areas,
tables/floaters/figures, advanced algorithms and full bidi/native language remain
incomplete.

Release 8.0.0-18 adds BlockUIContainer formatting through original floater
callbacks, UIElementIsland child layout and margin handling. Original flat/nested
WPF documents defer a real button intact to the next page with expected child
bounds, colored raster, content/page mapping, point hits, routed events and page
regeneration. Oversized/empty blocks finish without phantom continuations; blocks
can move intact into the second column. Scrolling controls update when their
embedded child resizes. Native tests cover handler registration, query/update
state, deferral/forced progress, callback failures and exact resource cleanup.
Shared-framework/portable SDK consumers pass. Imported-symbol coverage rises to
91/139. Floating obstacles/figures, tables, balancing/span areas, advanced/optimal/
incremental/interruptible algorithms and full bidi/native language remain
incomplete.
