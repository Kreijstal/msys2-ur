# The MSYS2 prefix (@MINGW_PREFIX@) as a Bazel repository.

# Python headers; extensions link libpython@PYVER@.dll (import library
# lib/libpython@PYVER@.dll.a).
cc_library(
    name = "python_headers",
    hdrs = glob(["include/python@PYVER@/**/*.h"]),
    includes = ["include/python@PYVER@"],
    linkopts = ["-lpython@PYVER@"],
    visibility = ["//visibility:public"],
)

# The MinGW C++ runtime DLLs. Every cc_binary executable gets them through
# --@rules_cc//:link_extra_libs (and the @bazel_tools one), so the
# copy_dynamic_libraries_to_binary feature puts the DLLs next to it: build
# tools are run by Starlark actions without PATH and would not find them.
# cc_import wants a .lib-style name for the import library.
[
    genrule(
        name = name + "_implib",
        srcs = [implib],
        outs = [name + ".if.lib"],
        cmd = "cp $< $@",
    )
    for name, implib in [
        ("libstdcxx", "lib/libstdc++.dll.a"),
        ("libgcc_s", "lib/libgcc_s.a"),
        ("libwinpthread", "lib/libwinpthread.dll.a"),
    ]
]

cc_import(
    name = "libstdcxx",
    interface_library = ":libstdcxx_implib",
    shared_library = "bin/libstdc++-6.dll",
)

cc_import(
    name = "libgcc_s",
    interface_library = ":libgcc_s_implib",
    shared_library = "bin/libgcc_s_seh-1.dll",
)

cc_import(
    name = "libwinpthread",
    interface_library = ":libwinpthread_implib",
    shared_library = "bin/libwinpthread-1.dll",
)

cc_library(
    name = "runtime_dlls",
    visibility = ["//visibility:public"],
    deps = [
        ":libgcc_s",
        ":libstdcxx",
        ":libwinpthread",
    ],
)
