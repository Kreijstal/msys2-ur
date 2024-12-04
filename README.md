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
