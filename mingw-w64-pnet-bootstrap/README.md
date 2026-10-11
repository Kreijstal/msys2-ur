# Portable.NET bootstrap root

This UCRT64 package builds DotGNU Portable.NET and pnetlib from pinned Git
commits, with treecc built from its checksum-pinned release source. It needs
only native C tools. The recipe poisons Mono/.NET compiler commands during
the build and rejects prebuilt binaries in the source trees.

It was imported from `dotnet-bootstrap/bootstrap/mingw-w64-pnet-bootstrap`, with
its Guix and MSYS2/Win64 patches. All patch inputs are local to this directory.

From a **UCRT64** shell:

```bash
makepkg-mingw -s
pacman -U mingw-w64-ucrt-x86_64-pnet-bootstrap-*.pkg.tar.zst
```

Tools and libraries are installed under
`/ucrt64/lib/dotnet-bootstrap/pnet`, avoiding conflicts with Mono's ilasm,
resgen and other commands. Add its `bin` directory to PATH when using cscc
and ilrun. `check()` compiles a C# foreach/array console program with cscc,
runs it with ilrun and requires `sum=6`.

This packages the C-only bootstrap root. The later zero-seed Mono bootstrap
is still separate work. The [SDK package](../mingw-w64-dotnet-bootstrap/README.md)
uses the already trusted MSYS2 Mono 6.12 seed instead.

Native debug information is retained and managed PE files are preserved.
makepkg reports source-directory references in native outputs. The installed
compiler/runtime smoke test also passes with the entire build tree hidden.
