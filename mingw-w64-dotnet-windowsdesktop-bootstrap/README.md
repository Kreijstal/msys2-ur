# Source WindowsDesktop bootstrap

This recipe builds WPF 8.0.0 and the approved interim WinForms 7.0.20 port from
source using the source-built .NET 8 SDK and C++/CLI compiler. Its framework
version is `8.0.0-bootstrap.wpf.8.0.0`. It includes the desktop SDK/markup tasks,
targeting/runtime packs, all managed shipping implementations, native graphics,
pen input and the source PresentationNative replacement.

The native text/paragraph/NLS replacement is still partial (currently 109 of 139
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

Release 8.0.0-19 adds finite/bottomless subpage layout, original installed
subpage callbacks, typed independent cloned continuations, column/detail queries
and cleanup. Native tests cover exact ranges, two-column geometry, zero-height
structural source, forced visible-line progress, nested object ownership and
lost-output callback rollback. Original table-cell subpage clients render four
finite chunks with all 699 characters covered exactly once in Ideal/Display;
bottomless clients retain their full extent and viewport glyphs. SDK shared/
portable consumers pass. Coverage rises to 99/139; public table/floater/figure
layout, subpage updates/comparison, balancing/span areas, advanced/optimal/bidi/
native-language behavior and broader runtime support remain unfinished.

Release 8.0.0-20 adds bottomless subpage updates through original callbacks.
The existing subpage handle survives complete replacement; failed formatting
preserves the previous native tree. Native gates cover new geometry/source,
invalidated old tracks, output clearing, foreign/stale/wrong-segment rejection
and exact callback cleanup. Original cell subpage clients update after a text
edit and width change, retaining all 1339 characters with changed glyph raster
and full extent in Ideal/Display. Shared-framework/portable SDK consumers pass.
Coverage rises to 100/139. Subpage comparison/display transfer, subtrack updates,
public table/floater/figure layout, balancing/span areas and advanced/optimal/
interruptible/bidi/native-language behavior remain unfinished.

Release 8.0.0-21 adds bottomless subtrack updates and vertical synchronization.
The track keeps its identity during full replacement; failed callbacks retain
its prior tree. Shift plans validate all coordinates before moving retained
lines/bounds and preserve line identity without formatting callbacks. Original
container clients with/without margins and padding update after edits/resizing,
cover all 1339 characters exactly once through actual text records, and render
changed and vertically shifted glyphs in Ideal/Display. Native ownership/error/
overflow gates and shared-framework/portable SDK consumers pass. Coverage rises
to 102/139. Comparison/display transfer, public table/floater/figure layout,
balancing/span areas and advanced/optimal/interruptible/bidi/native-language
behavior remain unfinished.

Release 8.0.0-22 adds public rectangular floaters discovered through original
before-line attachment callbacks. Original content/clients and attachment queries
retain real source and placement; left/right obstacles constrain host line widths
until their bottom edge. Public WPF raster checks render blue floating text on a
red background with black host glyphs beside it and zero overlap, finish three
pages with all 821 characters covered once, and regenerate disposed floating
content. Scrolling viewers update host/floater raster after edits. Native ownership/
query/failure gates and shared-framework/portable SDK consumers pass. Coverage
rises to 103/139. This initial path supports one intact before-line floater;
in-line anchors, multiple/split floaters, center wrapping, figures/tables,
comparison/display transfer, advanced/bidi/native-language behavior and broader
runtime support remain unfinished.

Release 8.0.0-23 adds multiple before-line rectangular floaters. Later colliding
objects move below earlier ones while retaining their horizontal edge; disjoint
opposite-edge rectangles share a row. Actual line height refines obstacle
exclusion so host glyphs cannot cross a wider later rectangle. Public WPF tests
render red/green objects without object/host overlap and finish three pages with
all 944 characters covered once in Ideal/Display, including page regeneration.
Native capacity/placement/later-failure/cleanup checks and shared-framework/
portable SDK consumers pass. Coverage stays 103/139. Placement requiring deferred
or split floater pages, later inline anchors, complex center/clear policies,
figures/tables and other documented WPF paths remain unfinished.

Release 8.0.0-24 defers intact before-line floaters when the occupied page
cannot hold their content or combined collision-free rectangles. The host text
checkpoint remains before the unconsumed anchor; speculative subpage content,
continuation records and clients are released before retrying on a fresh page.
Original WPF single/multiple-floater tests complete four pages with all 1000/1028
characters covered exactly once in Ideal/Display, rendering floating content
only on the next page and regenerating it after disposal. Native no-progress,
speculative split-record and collision rollback cases check exact cleanup.
Coverage stays 103/139. Oversized/split floater content on a fresh page, later
inline anchors, complex center/clear policies, figures/tables and the other
listed WPF paths remain unfinished.

Release 8.0.0-25 discovers floating objects inside original formatted text lines.
Their rectangles constrain subsequent line retries. If wrapping moves an anchor
out of its provisional line, the rectangle moves forward while retaining the
chosen text break, preventing wide/narrow layout oscillation. Late anchors defer
at their incoming host checkpoint when the page lacks room. Original WPF tests
cover early, wrapping-displaced and late-page anchors with exact source/page
ownership, glyph exclusion and page regeneration in Ideal/Display; scrolling
edits also exercise inline anchors. Native retry, invalid-output and callback
cleanup checks pass. Coverage stays 103/139. Oversized/split content, flow across
paragraph boundaries, complex center/clear policies, figures/tables and the
other documented WPF paths remain unfinished.

Release 8.0.0-26 retains original floater content break records across paragraph
continuations and resumes actual subpage chunks on following columns/pages.
Host text and floating content advance independently, including floating-only
chunks after the host ends. Shared record owners support independent cloned
resumes and preserve inputs across no-progress or failed callbacks. Original WPF
checks cover leading/inline/deferred anchors, column continuation, a long host
paragraph and two opposite-edge split floaters with exact source/page ownership,
real chunk glyph raster, page regeneration and GC. Native clone/error/lifetime
checks pass. Coverage stays 103/139. Colliding multi-floater splits beyond one
placement area, cross-paragraph flow, complex center/clear policies, figures/
tables and the other documented WPF paths remain unfinished.

Release 8.0.0-27 adds public tables through original width, row and cell callbacks.
Cells retain their actual managed clients and source-built subpages; maximum
cell height and original spacing determine each row. Whole rows defer to the
next column/page and typed queries return real table/row/cell data. Cell-owned
subpages inherit visual updates after arrangement, allowing original glyph
initialization. Public WPF checks cover auto/fixed widths, borders/padding,
horizontal spans, row groups, preceding text, columns, nested/empty tables and
scrolling edits with exact source ownership and page regeneration. Native query,
row-resume and populated/lost-output cleanup gates pass; ABI checks cover 429
fields. Coverage rises to 109/139. Splitting cells/rows, vertical spans, repeated
headers/footers, figures, advanced/bidi/native-language behavior and other
listed paths remain unfinished.

Release 8.0.0-28 adds independently owned cell break records to row continuations.
Tall rows split on fresh pages/columns while completed neighboring cells stop
producing content handles. Original subpages resume unfinished cells, and later
rows follow completed split rows. Shared immutable checkpoints support cloned
resumes, no-progress preservation and failure cleanup. Public tests cover unequal
cell lengths, initial whole-row deferral, columns, following rows, exact source/
page ownership and chunk regeneration. Tiny pages force actual line progress.
Native clone/failure/lifetime and shared-framework/portable SDK gates pass.
Coverage stays 109/139. Vertical spans, repeated headers/footers, figures,
advanced/bidi/native-language behavior and other documented paths remain open.

Release 8.0.0-29 adds connected vertical table spans that fit a fresh column.
Original first/middle/last merge flags retain one actual cell client across rows.
Natural ordinary-cell heights and span content constraints determine geometry;
shared clients release once. Connected groups defer intact when remaining page
space is insufficient. Public WPF checks cover natural/growing/span-only groups,
staggered overlapping spans, columns, initial deferral, exact source ownership,
actual glyph/background geometry and scrolling edits. Native shared-handle,
merge/query/height/failure/cleanup gates pass. Coverage stays 109/139. Span groups
taller than a column still require continuation support; repeated headers/
footers, figures, advanced/bidi/native-language behavior and other paths remain
unfinished.

Release 8.0.0-30 adds cell continuations for oversized connected vertical spans.
Fresh columns format finite fragments; unfinished masters retain original cell
break records, while completed cells expose null content slots. Ordinary rows
share the available height and span constraints account for content outside each
interval. Original WPF checks cover tall/deferred/column spans, overlapping tall
masters and tall ordinary neighbors with exact source ownership and chunk
regeneration. Native clone/no-progress/failure/single-owner cleanup checks pass.
Coverage stays 109/139. More complex span/row-break layouts, repeated headers/
footers, figures, advanced/bidi/native-language behavior and other documented
paths remain unfinished.

Release 8.0.0-31 connects finite Figure attachments to original WPF content and
positioning callbacks. Real FigureParaClient subpages retain their managed owner;
figure-details queries expose actual flow rectangles and bounds. Page/margin/
column anchors, offsets, initial deferral, autosizing and nested content pass
Ideal/Display checks with exact source ownership, glyph raster and regeneration.
Rectangular wrapping intersects permitted regions before choosing one line
interval. Native context/stale-query and lost/populated callback cleanup gates
pass; ABI checks now cover 441 fields and imported coverage is 110/139. Complex
figure collision/search policies, composite lines using both sides of an inset
obstacle, bidi/native-language and other documented paths remain unfinished.

Release 8.0.0-32 implements finite page updates with stable native page identity.
A complete replacement layout and its outgoing checkpoint are prepared before
commit; old section/column/text handles invalidate on success and release outside
the registry lock. Failed callbacks retain the previous layout and reusable
incoming checkpoint. Native lifecycle/failure/continuation/column gates pass.
Original managed page edits preserve native identity and render changed glyphs;
long edited content resumes across three pages with every character exactly once
in Ideal/Display, with and without columns. ABI remains 441 fields; imported
coverage is 111/139. This reformats a complete page; selective incremental reuse,
advanced layout, bidi/native-language and other documented paths remain open.

Release 8.0.0-33 adds horizontal bidi reversal scopes to source Line Services.
Original managed levels drive visual run ordering, drawing origins and nested
caret/point queries. Coalesced controls retain their scope counts; immutable
break records preserve embedding levels through cloned/wrapped continuations.
Controls do not alter Unicode word boundaries or intrinsic widths. Hebrew,
Arabic, Latin mixtures, numbers, combining marks and trailing spaces pass both
text modes/paragraph directions, including selection, glyph enumeration and
TextBlock layout/hit/raster. Justified mixed FlowDocuments preserve exact source
ownership across pages. ABI remains 441 fields and imported coverage 111/139.
Full RTL paragraph/page layout, advanced bidi decorations/objects/expansion,
selective incremental reuse and other documented paths remain unfinished.

Release 8.0.0-34 adds horizontal RTL page/paragraph/subpage layout. Physical page
margins convert to logical U coordinates; sections preserve writing direction
and columns advance in reading order. Opposite-direction paragraphs format in
their own coordinates and return bounds in the parent track's direction. Local
subpage frames preserve coordinate ownership; synchronization validates the
track's actual direction. Ideal/Display checks cover all page/paragraph/column
combinations, asymmetric margins, exact source/page ownership and first-column
placement, scrolling edits and basic table cell order/glyphs. Native matrix/
failed-update/cleanup checks pass. ABI/import coverage remains 441 fields and
111/139. Advanced bidi objects/decorations/expansion, complex layout, selective
incremental reuse and other documented paths remain unfinished.

Release 8.0.0-35 adds source subtrack/subpage comparison and display transfer.
Comparison validates context, native object kind and direction; opaque fresh
line clients conservatively report changed content. Empty tracks can compare
unchanged or vertically shifted. Original object/cell callbacks handle their
comparison contracts; shared-cell topology is validated. Display transfer moves
original managed visual ownership recursively through source containers and
subpages, preserves new-content flags, and skips already accepted transfers on
retry. Weak ownership records do not retain old layouts. Native checks cover
partial callback failure, retry/idempotence, empty shifted tracks, stale/foreign/
wrong-kind handles and exact cleanup. Original managed clients in Ideal/Display
verify nested visual identity, a same-geometry brush edit, a second-generation
text edit, old-owner disposal/GC and source coverage through shared-framework
and portable self-contained SDK execution. Imported coverage rises to 115/139;
ABI remains 441 fields. Selective line reuse, complex object/layout behavior,
advanced bidi and other documented paths remain unfinished.

Release 8.0.0-36 adds explicit finite column balancing and the two native
subtrack/subpage balancing measurement APIs. Completed multi-column sections
search for a reduced feasible height through original formatting callbacks;
full pages preserve their continuation and capacity. Trial pages/clients/line
records and margin states retain exact ownership on success or callback failure.
KeepTogether and KeepWithNext retain their original paragraph/prefix constraints,
including widow/orphan rules. Ordinary WPF section/subpage defaults remain as in
the original source. Measurements derive from retained original line records,
installed child/floater callbacks and conservative table row units, with checked
counts/heights, actual direction and context/kind validation. Native tests cover
root/subpage balance, exact source, completed/full pages, keep constraints,
failed-trial cleanup and recursive callback measurements. Original managed
Ideal/Display and LTR/RTL clients verify balanced glyph columns, line-record
metrics, exact source ranges, kept/nested content and GC through shared-framework
and portable self-contained execution. Imported coverage rises to 117/139;
paragraph ABI remains 441 fields. General column spans, complex object layouts,
optimal formatting, footnotes and full native-language behavior remain open.

Release 8.0.0-37 adds rectangular composite text rows around centered obstacles.
All permitted horizontal intervals can contain source-formatted elements on one
row. Original element clients/break records retain ownership; row ascent/descent
aggregate element metrics and vertical progress occurs once per row. Pagination,
widow/orphan constraints, forced progress, balancing and keep-prefix measurements
count rows. Inline geometry retries release provisional elements while retaining
valid narrowed text breaks after obstacle postponement. Original composite row/
element queries use source-derived records and context-owned weak row handles;
short arrays, wrong kinds and stale/foreign handles reject without partial counts.
Native checks cover exact intervals/metrics/source, cloned continuations after
old-page destruction, ordinary rows after the obstacle, and later-element failure
cleanup. Original managed Ideal/Display and LTR/RTL consumers render glyphs on
both obstacle sides, check caret/point geometry and exact source/page ownership,
and exercise late anchors, nested figure content, mixed font sizes, narrow
columns, page regeneration and GC through shared-framework and self-contained
execution. Imported coverage rises to 119/139 and ABI coverage to 470 fields.
Polygon/composite-line optimizations, advanced object layout, general column spans,
footnotes, optimal formatting and full native-language behavior remain open.

Release 8.0.0-38 adds source automatic hyphenation. NlCreateHyphenator,
NlHyphenate and NlDestroyHyphenator implement the original HRESULT/out-retval,
UTF-16 bitmask and disposal ABI. The source Hunspell/Hyphen C engine and 36 pinned
UTF-8 text dictionaries are checksum-verified and embedded in the native DLL;
published consumers need no external dictionary path. Original per-language
notices and complete engine/dictionary source are included in the package.
Regional English uses the bundled US patterns; German uses reformed orthography
with a Swiss variant. Only opportunities that preserve original characters are
exposed by WPF's bitmask contract. The line-breaking callback measures inserted
hyphen glyphs when selecting a fitting dictionary break; glyph drawing, caret
cells and enumeration preserve actual source lengths. Cloned break records resume
from the original source position, and prohibited lines retain normal wrapping.
Native checks cover exact/case/surrogate offsets, short arrays, stale resources,
callback errors, invalid positions, marker geometry and continuation ownership.
Original managed tests cover thirteen cultures, direct Ideal/Display LTR/RTL
formatting and public left/justified FlowDocuments: ten pages, 30/39 inserted
glyphs and all 539 source characters/page mappings survive regeneration and GC.
Shared-framework and portable self-contained checks pass. Imported coverage rises
to 122/139; paragraph ABI remains 470 fields. Linguistic results follow the bundled
patterns; legacy spelling, unsupported cultures, nonstandard spelling changes,
advanced layout and other documented paths remain unfinished.
