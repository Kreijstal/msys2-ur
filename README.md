# MSYS2-UR

**MSYS2-UR** aims to bring an AUR-like experience to the MSYS2 ecosystem. This repository serves as a community-driven collection of PKGBUILD files and build recipes for MSYS2 packages. By sharing and contributing PKGBUILD files here, we hope to make it easier for users to build and install additional tools in the MSYS2 environment.

---

## Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Kreijstal/msys2-ur.git
   cd msys2-ur
   ```

2. **Find a Package**
   Browse the directory structure to locate the package you are interested in. Each package has its own directory containing the necessary files to build it.

3. **Build and Install**
   Use `makepkg` to build the package from the provided PKGBUILD. For example:
   ```bash
   cd some-package-directory
   makepkg -si
   ```

---

## Using the Binary Package Repository

Prebuilt packages are published as one pacman repository per environment, each
in its own release with its database:

| Repository | Environment |
| --- | --- |
| [`msys2ur-ucrt64`](https://github.com/Kreijstal/msys2-ur/releases/tag/msys2ur-ucrt64) | UCRT64 |
| [`msys2ur-clang64`](https://github.com/Kreijstal/msys2-ur/releases/tag/msys2ur-clang64) | CLANG64 |
| [`msys2ur-mingw64`](https://github.com/Kreijstal/msys2-ur/releases/tag/msys2ur-mingw64) | MINGW64 |
| [`msys2ur-msys`](https://github.com/Kreijstal/msys2-ur/releases/tag/msys2ur-msys) | MSYS (Cygwin-based X11 stack) |

Add the repositories for the environments you use to `/etc/pacman.conf`, for
example:

```ini
[msys2ur-ucrt64]
SigLevel = Optional TrustAll
Server = https://github.com/Kreijstal/msys2-ur/releases/download/$repo

[msys2ur-clang64]
SigLevel = Optional TrustAll
Server = https://github.com/Kreijstal/msys2-ur/releases/download/$repo
```

The former single `[msys2ur]` repository in the `x11-shared-20260731` release is
no longer updated; replace it with the sections above.

Refresh the package databases:

```bash
pacman -Sy
```

Install packages by their environment-specific names. For example, bchunk is
available for MINGW64, UCRT64, and CLANG64:

```bash
# MINGW64
pacman -S mingw-w64-x86_64-bchunk

# UCRT64
pacman -S mingw-w64-ucrt-x86_64-bchunk

# CLANG64
pacman -S mingw-w64-clang-x86_64-bchunk
```

The repository is currently unsigned, which is why the configuration uses
`SigLevel = Optional TrustAll`. Review package recipes and release assets before
installation.

---

## Source-built .NET and C++/CLI

The [dotnet-bootstrap recipe](mingw-w64-dotnet-bootstrap/README.md) builds
split CLANG64 packages for the self-hosted SDK, CoreCLR and Mono runtimes,
reference pack, host/embedding development files and bootstrap tools. The
[cppcli recipe](mingw-w64-cppcli/README.md) packages the Clang-based C++/CLI
subset. [pnet-bootstrap](mingw-w64-pnet-bootstrap/README.md) packages the
independent C-only Portable.NET root for UCRT64.

[PowerShell 7.4.20](mingw-w64-powershell/README.md) is built from source on
this stack for CLANG64 and UCRT64 (UCRT64 without the WindowsDesktop
GraphicalHost) and published together with its runtime dependencies and
bundled modules. The SDK, compiler and other build-only packages are
experimental and not yet part of the published binary repository. See each
recipe's build instructions.

---

## Contributing

1. **Fork the Repository**
   - Click the "Fork" button on the top right of this repository to create your own copy.

2. **Add Your Package**
   - Create a new directory for your package under the repository root.
   - Include the following files:
     - `PKGBUILD`: The build recipe for your package.
     - Optional: Additional patches or files required for the build.

   Example directory structure:
   ```
   my-new-package/
   ├── PKGBUILD
   ├── patch.diff (optional)
   └── other-files (optional)
   ```

3. **Submit a Pull Request**
   - Once you've added and tested your package, push your changes to your fork and submit a Pull Request (PR) to the main repository.

4. **Follow Package Guidelines**
   - Ensure your PKGBUILD follows MSYS2 packaging standards where possible.
   - Include clear comments in your PKGBUILD if any special steps or dependencies are required.

---

## Notes

- **No CI (for now)**: Packages are community-maintained, and users are responsible for ensuring their builds work correctly. Over time, we may explore adding CI to validate builds.
- **Dependencies**: For now, users will need to manually build and install package dependencies.
- **Helpers**: We recommend creating or repurposing an existing AUR helper if you plan to manage multiple packages. Contributions to develop such a helper are welcome!

---

## Why MSYS2-UR?

This project was created to address the gap in sharing community-built packages for MSYS2. By enabling users to contribute their own PKGBUILDs, we aim to make the MSYS2 ecosystem more extensible and flexible. Whether you're adding new tools, porting Unix utilities, or experimenting with MSYS2, this is the place to share your efforts!

---

**Let's make MSYS2 great together!**
