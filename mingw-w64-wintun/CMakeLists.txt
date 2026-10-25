# GCC/MinGW build of Wintun: the wintun.sys NDIS 6 miniport and the
# wintun.dll API library that embeds it.
#
# wintun.sys is a plain NDIS 6.20+ miniport (no KMDF). It is built against
# the ReactOS DDK headers and import libraries:
#
#   REACTOS_SOURCE_DIR  ReactOS source tree (sdk/include, sdk/lib/pseh,
#                       sdk/cmake/init-section.lds)
#   REACTOS_BUILD_DIR   configured ReactOS amd64 build tree with the generated
#                       headers (ninja xdk psdk bugcodes), the import
#                       libraries of ntoskrnl, hal and ndis, librtlver and the
#                       gcc_plugin_seh host plugin that implements PSEH for
#                       GCC on amd64 (ninja native-gcc_plugin_seh)
#
# wintun.dll only needs the toolchain's own Windows headers and libraries.

cmake_minimum_required(VERSION 3.20)
project(wintun C RC)

set(REACTOS_SOURCE_DIR "" CACHE PATH "ReactOS source tree")
set(REACTOS_BUILD_DIR "" CACHE PATH "Configured ReactOS amd64 build tree")
set(NTOSKRNL_IMPLIB "" CACHE FILEPATH "ntoskrnl import library (default: the ReactOS build tree's)")
set(NDIS_IMPLIB "" CACHE FILEPATH "ndis import library (default: the ReactOS build tree's)")
set(HAL_IMPLIB "" CACHE FILEPATH "hal import library (default: the ReactOS build tree's)")
set(WINTUN_VERSION "0.14.1" CACHE STRING "Wintun version")
set(DRIVER_DATE "" CACHE STRING "INF DriverVer date (MM/DD/YYYY)")

foreach(_v REACTOS_SOURCE_DIR REACTOS_BUILD_DIR)
    if(NOT IS_DIRECTORY "${${_v}}")
        message(FATAL_ERROR "${_v} must name a directory")
    endif()
endforeach()
if(NOT DRIVER_DATE)
    string(TIMESTAMP DRIVER_DATE "%m/%d/%Y" UTC)
endif()

find_package(Python3 REQUIRED COMPONENTS Interpreter)

if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(AMD64|x86_64)$" OR CMAKE_C_COMPILER_TARGET MATCHES "^x86_64" OR CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(WINTUN_ARCH amd64)
else()
    message(FATAL_ERROR "Only the amd64 build is supported")
endif()

set(ROS ${REACTOS_SOURCE_DIR})
set(ROSB ${REACTOS_BUILD_DIR})
set(GLUE ${CMAKE_CURRENT_SOURCE_DIR}/gcc)
set(GEN ${CMAKE_CURRENT_BINARY_DIR})
string(REPLACE "." ";" _ver "${WINTUN_VERSION}")
list(GET _ver 0 WINTUN_VERSION_MAJ)
list(GET _ver 1 WINTUN_VERSION_MIN)
list(LENGTH _ver _n)
if(_n GREATER 2)
    list(GET _ver 2 WINTUN_VERSION_REL)
else()
    set(WINTUN_VERSION_REL 0)
endif()
set(WINTUN_VERSION_DEFS
    WINTUN_VERSION_MAJ=${WINTUN_VERSION_MAJ}
    WINTUN_VERSION_MIN=${WINTUN_VERSION_MIN}
    WINTUN_VERSION_REL=${WINTUN_VERSION_REL}
    WINTUN_VERSION="${WINTUN_VERSION}")

if(NOT NTOSKRNL_IMPLIB)
    set(NTOSKRNL_IMPLIB ${ROSB}/ntoskrnl/CMakeFiles/libntoskrnl.dir/libntoskrnl.a)
endif()
if(NOT HAL_IMPLIB)
    set(HAL_IMPLIB ${ROSB}/hal/halx86/CMakeFiles/libhal.dir/libhal.a)
endif()
if(NOT NDIS_IMPLIB)
    set(NDIS_IMPLIB ${ROSB}/drivers/network/ndis/CMakeFiles/libndis.dir/libndis.a)
endif()
# SEH (MmProbeAndLockPages raises on bad user buffers) needs the plugin
find_file(GCC_PLUGIN_SEH NAMES gcc_plugin_seh.so gcc_plugin_seh.dll
    PATHS ${ROSB}/host-tools/bin NO_DEFAULT_PATH NO_CMAKE_FIND_ROOT_PATH)
if(NOT GCC_PLUGIN_SEH)
    message(FATAL_ERROR "${ROSB}/host-tools/bin has no gcc_plugin_seh: run ninja native-gcc_plugin_seh there")
endif()

# No default flags: each target below brings its own
foreach(_cfg DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
    set(CMAKE_C_FLAGS_${_cfg} "")
endforeach()
set(CMAKE_C_STANDARD_LIBRARIES "")

##
## wintun.sys
##

# The version resource only needs the toolchain's own headers
add_library(wintun-sys-res OBJECT driver/wintun.rc)
target_compile_definitions(wintun-sys-res PRIVATE ${WINTUN_VERSION_DEFS})

add_executable(wintun-sys driver/wintun.c $<TARGET_OBJECTS:wintun-sys-res>)
set_target_properties(wintun-sys PROPERTIES OUTPUT_NAME wintun SUFFIX ".sys"
    RUNTIME_OUTPUT_DIRECTORY ${GEN}/driver)

target_include_directories(wintun-sys BEFORE PRIVATE
    ${GLUE}/ddk
    ${ROS}/sdk/include
    ${ROS}/sdk/include/crt
    ${ROS}/sdk/include/ddk
    ${ROS}/sdk/include/ndk
    ${ROS}/sdk/include/psdk
    ${ROS}/sdk/include/reactos
    ${ROS}/sdk/include/reactos/libs
    ${ROS}/sdk/include/vcruntime
    ${ROSB}/sdk/include
    ${ROSB}/sdk/include/psdk
    ${ROSB}/sdk/include/ddk
    ${ROSB}/sdk/include/reactos
    ${ROSB}/sdk/include/reactos/mc
    ${ROS}/sdk/lib/pseh/include)

# The WDK project's definitions (driver.vcxproj), plus the target the ReactOS
# headers need. Upstream targets Windows 7 for amd64.
target_compile_definitions(wintun-sys PRIVATE
    _AMD64_ _M_AMD64 _M_X64 _WIN64 __REACTOS__ DBG=0 _KERNEL_MODE
    WINVER=0x0601 _WIN32_WINNT=0x0601 NTDDI_VERSION=0x06010000
    NDIS_MINIPORT_DRIVER=1 NDIS620_MINIPORT=1 NDIS683_MINIPORT=1 NDIS_WDM=1
    # the ReactOS ndis.h only builds with its NDIS 5 declarations, as its
    # own NDIS 6 miniports do
    NDIS_LEGACY_DRIVER=1 NDIS_LEGACY_MINIPORT=1
    POOL_ZERO_DOWN_LEVEL_SUPPORT POOL_NX_OPTIN=1
    ${WINTUN_VERSION_DEFS})

target_compile_options(wintun-sys PRIVATE
    -nostdinc -fplugin=${GCC_PLUGIN_SEH} -fno-reorder-blocks
    -std=gnu11 -O2 -mcmodel=small -mcx16 -mlong-double-64 -fms-extensions -fno-strict-aliasing
    -fno-common -fno-aggressive-loop-optimizations
    -Wall -Wno-multichar -Wno-unknown-pragmas -Wno-missing-braces -Wno-int-to-pointer-cast)

target_link_options(wintun-sys PRIVATE
    -nostdlib -s
    -Wl,--subsystem,native:6.1
    -Wl,--major-os-version,6,--minor-os-version,1
    "SHELL:-Xlinker --stack -Xlinker 0x100000,0x1000"
    -Wl,--entry,DriverEntry
    -Wl,--image-base,0x140000000
    -Wl,--file-alignment,0x200,--section-alignment,0x1000
    -Wl,--disable-auto-import,--disable-stdcall-fixup,--exclude-all-symbols
    -Wl,--disable-long-section-names
    -Wl,--dynamicbase,--nxcompat,--high-entropy-va
    -Wl,-T,${ROS}/sdk/cmake/init-section.lds)

target_link_libraries(wintun-sys PRIVATE
    -Wl,--start-group
    ${NDIS_IMPLIB} ${NTOSKRNL_IMPLIB} ${HAL_IMPLIB}
    ${ROSB}/sdk/lib/drivers/rtlver/librtlver.a
    gcc
    -Wl,--end-group)

# ReactOS pefixup marks INIT discardable, cleans up the section flags GNU ld
# sets and writes the image checksum the kernel loader checks.
if(EXISTS ${ROSB}/host-tools/bin/pefixup)
    add_custom_command(TARGET wintun-sys POST_BUILD
        COMMAND ${ROSB}/host-tools/bin/pefixup --kernelmodedriver $<TARGET_FILE:wintun-sys>)
endif()

# wintun.inf and the wintun-inf.h the API library compares driver versions with
add_custom_command(OUTPUT ${GEN}/driver/wintun.inf ${GEN}/wintun-inf.h
    COMMAND ${Python3_EXECUTABLE} ${GLUE}/stampinf.py
            ${CMAKE_CURRENT_SOURCE_DIR}/driver/wintun.inf ${GEN}/driver/wintun.inf ${GEN}/wintun-inf.h
            ${WINTUN_ARCH} ${WINTUN_VERSION} "${DRIVER_DATE}"
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/driver/wintun.inf ${GLUE}/stampinf.py)
add_custom_target(wintun-inf ALL DEPENDS ${GEN}/driver/wintun.inf ${GEN}/wintun-inf.h)

##
## wintun.dll
##

# Probe for what mingw-w64 lacks of the Windows SDK; wintun-gcc-compat.h,
# force-included into every source, fills in exactly that.
include(CheckIncludeFile)
include(CheckCSourceCompiles)
include(CheckSymbolExists)
set(COMPAT ${GEN}/compat)
file(MAKE_DIRECTORY ${COMPAT})
set(CMAKE_REQUIRED_DEFINITIONS -DUNICODE -D_WIN32_WINNT=0x0601 -DNTDDI_VERSION=0x06010000)
set(_compat_defs)
check_include_file(swdevice.h HAVE_SWDEVICE_H)
check_include_file(devquery.h HAVE_DEVQUERY_H)
foreach(_h swdevice devquery)
    string(TOUPPER ${_h} _H)
    if(HAVE_${_H}_H)
        list(APPEND _compat_defs WINTUN_GCC_HAVE_${_H})
    else()
        file(WRITE ${COMPAT}/${_h}.h "#include \"${GLUE}/wintun-gcc-compat.h\"\n")
    endif()
endforeach()
check_c_source_compiles("#include <windows.h>\n#include <devpropdef.h>\nDEVPROPCOMPKEY k;\nint main(void) { return 0; }" HAVE_DEVPROPCOMPKEY)
if(NOT HAVE_DEVPROPCOMPKEY)
    list(APPEND _compat_defs WINTUN_GCC_NEED_DEVPROPCOMPKEY)
endif()
check_symbol_exists(SetupDiSetDevicePropertyW "windows.h;setupapi.h" HAVE_SETUPDISETDEVICEPROPERTYW)
if(NOT HAVE_SETUPDISETDEVICEPROPERTYW)
    list(APPEND _compat_defs WINTUN_GCC_NEED_SETUPDISETDEVICEPROPERTY)
endif()
check_symbol_exists(ReadULongAcquire "windows.h" HAVE_READULONGACQUIRE)
if(NOT HAVE_READULONGACQUIRE)
    list(APPEND _compat_defs WINTUN_GCC_NEED_MEMACCESS)
endif()
# ndisguid.h lives in the DDK directory of mingw-w64
check_include_file(ndisguid.h HAVE_NDISGUID_H)
if(NOT HAVE_NDISGUID_H)
    file(WRITE ${COMPAT}/ndisguid.h "#include <ddk/ndisguid.h>\n")
endif()
unset(CMAKE_REQUIRED_DEFINITIONS)

set(API_SOURCES
    api/adapter.c api/driver.c api/logger.c api/main.c api/namespace.c
    api/registry.c api/resource.c api/rundll32.c api/session.c)
add_library(wintun-objs OBJECT ${API_SOURCES})
add_dependencies(wintun-objs wintun-inf)
target_include_directories(wintun-objs PRIVATE ${GEN} api)
target_compile_options(wintun-objs PRIVATE
    -idirafter ${COMPAT} -include ${GLUE}/wintun-gcc-compat.h
    -std=gnu11 -O2 -fno-strict-aliasing
    -Wall -Wno-unknown-pragmas -Wno-missing-braces -Wno-cpp -Wno-unused-but-set-variable)
# The VS project: Unicode, Windows 7 baseline for amd64, WOW64-aware
target_compile_definitions(wintun-objs PRIVATE
    UNICODE _UNICODE _WINDOWS _USRDLL MAYBE_WOW64 NDEBUG WINTUN_NO_CATALOG
    WINVER=0x0601 _WIN32_WINNT=0x0601 NTDDI_VERSION=0x06010000 ${_compat_defs}
    ${WINTUN_VERSION_DEFS})

add_library(wintun SHARED $<TARGET_OBJECTS:wintun-objs> api/resources.rc api/exports.def)
set_target_properties(wintun PROPERTIES PREFIX "" IMPORT_PREFIX "lib")
target_compile_definitions(wintun PRIVATE WINTUN_NO_CATALOG ${WINTUN_VERSION_DEFS})
# resources.rc embeds the driver package from the build directory
target_include_directories(wintun PRIVATE ${GEN})
set_source_files_properties(api/resources.rc PROPERTIES
    OBJECT_DEPENDS "${GEN}/driver/wintun.sys;${GEN}/driver/wintun.inf")
add_dependencies(wintun wintun-sys wintun-inf)

# Like the VS project, every system library except ntdll and kernel32 is
# delay-loaded (and resolved from System32 by main.c's hook), so wintun.dll
# loads where newer functions such as SwDeviceCreate are missing.
set(DELAYLOAD_DLLS advapi32 cfgmgr32 iphlpapi ole32 setupapi shlwapi version shell32)
set(_delaylibs)
foreach(_dll ${DELAYLOAD_DLLS})
    list(APPEND _delaylibs ${GEN}/delay/lib${_dll}.delay.a)
endforeach()
list(APPEND _delaylibs ${GEN}/delay/libnci.delay.a)
add_custom_command(OUTPUT ${_delaylibs}
    COMMAND ${Python3_EXECUTABLE} ${GLUE}/mkdelaylib.py
            --dlltool ${CMAKE_DLLTOOL} --nm ${CMAKE_NM} --cc ${CMAKE_C_COMPILER}
            --out ${GEN}/delay --def nci=${CMAKE_CURRENT_SOURCE_DIR}/api/nci.def
            --dlls ${DELAYLOAD_DLLS}
            --objects $<TARGET_OBJECTS:wintun-objs>
    DEPENDS wintun-objs $<TARGET_OBJECTS:wintun-objs> ${GLUE}/mkdelaylib.py ${CMAKE_CURRENT_SOURCE_DIR}/api/nci.def
    COMMAND_EXPAND_LISTS VERBATIM)
add_custom_target(wintun-delaylibs DEPENDS ${_delaylibs})
add_dependencies(wintun wintun-delaylibs)

target_link_options(wintun PRIVATE -s -Wl,--dynamicbase,--nxcompat,--high-entropy-va)
target_link_libraries(wintun PRIVATE ${_delaylibs} ntdll kernel32 uuid)

install(TARGETS wintun RUNTIME DESTINATION bin ARCHIVE DESTINATION lib)
install(FILES api/wintun.h DESTINATION include)
install(FILES ${GEN}/driver/wintun.sys ${GEN}/driver/wintun.inf DESTINATION lib/wintun)
