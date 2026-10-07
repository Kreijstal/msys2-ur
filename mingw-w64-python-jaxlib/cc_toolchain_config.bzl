"""cc_toolchain_config for MSYS2 MinGW-w64 clang (x86_64-w64-windows-gnu).

GNU-style driver flags, lld, libstdc++/libgcc from the MSYS2 environment.
compiler = "clang" so that @rules_cc//cc/compiler:compiler == "clang" on
@platforms//os:windows, which is what LLVM's Bazel overlay calls
"is_windows_clang_mingw".

Legacy features (include paths, defines, -c/-o, libraries_to_link with
--whole-archive, param files, ...) are left to Bazel; this file only adds
what MinGW needs on top of them.
"""

load("@rules_cc//cc:action_names.bzl", "ACTION_NAMES")
load(
    "@rules_cc//cc:cc_toolchain_config_lib.bzl",
    "action_config",
    "artifact_name_pattern",
    "env_entry",
    "env_set",
    "feature",
    "flag_group",
    "flag_set",
    "tool",
    "tool_path",
    "variable_with_value",
    "with_feature_set",
)
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")
load("@rules_cc//cc/toolchains:cc_toolchain_config_info.bzl", "CcToolchainConfigInfo")

_c_compile = [ACTION_NAMES.c_compile]

_cpp_compile = [
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.cpp_module_codegen,
]

_all_compile = _c_compile + _cpp_compile + [
    ACTION_NAMES.assemble,
    ACTION_NAMES.preprocess_assemble,
]

_dll_link = [
    ACTION_NAMES.cpp_link_dynamic_library,
    ACTION_NAMES.cpp_link_nodeps_dynamic_library,
]

_all_link = [ACTION_NAMES.cpp_link_executable] + _dll_link

def _impl(ctx):
    artifact_name_patterns = [
        artifact_name_pattern(category_name = "executable", prefix = "", extension = ".exe"),
        artifact_name_pattern(category_name = "dynamic_library", prefix = "", extension = ".dll"),
        # cc_import only accepts .ifso/.tbd/.lib/.so/.dylib interface
        # libraries; lld's MinGW driver reads a GNU import library under any
        # name, so use MSVC's naming like Bazel's clang-cl toolchain.
        artifact_name_pattern(category_name = "interface_library", prefix = "", extension = ".if.lib"),
    ]

    features = [
        feature(name = "targets_windows", implies = ["copy_dynamic_libraries_to_binary"], enabled = True),
        feature(name = "copy_dynamic_libraries_to_binary"),
        feature(name = "supports_dynamic_linker", enabled = True),
        feature(name = "supports_interface_shared_libraries", enabled = True),
        # Use the action_configs' tool for DLL links (not
        # link_dynamic_library.sh, see below).
        feature(name = "has_configured_linker_path", enabled = True),
        # Replace the legacy features that pass the ELF ifso builder's
        # arguments ("yes", builder, input, output) to the link command.
        feature(name = "build_interface_libraries"),
        feature(name = "dynamic_library_linker_tool"),
        feature(name = "windows_export_all_symbols"),
        feature(name = "no_windows_export_all_symbols"),
        feature(name = "compiler_param_file", enabled = True),
        feature(name = "archive_param_file", enabled = True),
        # No ELF rpaths on PE/COFF; the legacy feature would pass -rpath.
        feature(name = "runtime_library_search_directories", enabled = True),
        feature(
            name = "gcc_env",
            enabled = True,
            env_sets = [
                env_set(
                    actions = _all_compile + _all_link + [ACTION_NAMES.cpp_link_static_library],
                    env_entries = [env_entry(key = "PATH", value = ctx.attr.tool_bin_path)],
                ),
            ],
        ),
        feature(
            name = "default_compile_flags",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = _all_compile,
                    flag_groups = [flag_group(flags = ctx.attr.compile_flags)],
                ),
                flag_set(
                    actions = _cpp_compile,
                    flag_groups = [flag_group(flags = ctx.attr.cxx_flags)],
                ),
                flag_set(
                    actions = _c_compile + _cpp_compile,
                    flag_groups = [flag_group(flags = ["-g0", "-O2", "-DNDEBUG", "-ffunction-sections", "-fdata-sections"])],
                    with_features = [with_feature_set(features = ["opt"])],
                ),
                flag_set(
                    actions = _c_compile + _cpp_compile,
                    flag_groups = [flag_group(flags = ["-g", "-O0"])],
                    with_features = [with_feature_set(features = ["dbg"])],
                ),
            ],
        ),
        feature(
            name = "default_link_flags",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = _all_link,
                    flag_groups = [flag_group(flags = ctx.attr.link_flags)],
                ),
                flag_set(
                    actions = _all_link,
                    flag_groups = [flag_group(flags = ["-Wl,--gc-sections", "-s"])],
                    with_features = [with_feature_set(features = ["opt"])],
                ),
            ],
        ),
        # Import library of a DLL (cc_binary linkshared / cc_library DLLs).
        feature(
            name = "interface_library_output",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = _dll_link,
                    flag_groups = [flag_group(
                        flags = ["-Wl,--out-implib,%{interface_library_output_path}"],
                        expand_if_equal = variable_with_value(
                            name = "generate_interface_library",
                            value = "yes",
                        ),
                    )],
                ),
            ],
        ),
        # lld's MinGW driver takes a .def file as a plain input.
        feature(
            name = "def_file",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = _dll_link,
                    flag_groups = [flag_group(
                        flags = ["%{def_file_path}"],
                        expand_if_available = "def_file_path",
                    )],
                ),
            ],
        ),
        feature(name = "dbg"),
        feature(name = "fastbuild"),
        feature(name = "opt"),
    ]

    # Bazel's legacy action configs link DLLs through link_dynamic_library.sh
    # whenever interface libraries are supported (it builds ELF .ifso stubs);
    # link them with the compiler driver directly, lld writes the import
    # library (interface_library_output above).
    action_configs = [
        action_config(
            action_name = name,
            tools = [tool(path = ctx.attr.tool_paths["gcc"])],
            implies = [
                "strip_debug_symbols",
                "shared_flag",
                "linkstamps",
                "output_execpath_flags",
                "runtime_library_search_directories",
                "library_search_directories",
                "libraries_to_link",
                "user_link_flags",
                "legacy_link_flags",
                "linker_param_file",
                "fission_support",
                "sysroot",
            ],
        )
        for name in _dll_link
    ]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        action_configs = action_configs,
        artifact_name_patterns = artifact_name_patterns,
        cxx_builtin_include_directories = ctx.attr.cxx_builtin_include_directories,
        toolchain_identifier = "mingw-w64-ucrt64-clang",
        host_system_name = "x86_64-w64-windows-gnu",
        target_system_name = "x86_64-w64-windows-gnu",
        target_cpu = "x64_windows",
        target_libc = "ucrt",
        compiler = "clang",
        abi_version = "local",
        abi_libc_version = "local",
        tool_paths = [tool_path(name = k, path = v) for k, v in ctx.attr.tool_paths.items()],
    )

cc_toolchain_config = rule(
    implementation = _impl,
    attrs = {
        "compile_flags": attr.string_list(),
        "cxx_builtin_include_directories": attr.string_list(),
        "cxx_flags": attr.string_list(),
        "link_flags": attr.string_list(),
        "tool_bin_path": attr.string(mandatory = True),
        "tool_paths": attr.string_dict(mandatory = True),
    },
    provides = [CcToolchainConfigInfo],
)
