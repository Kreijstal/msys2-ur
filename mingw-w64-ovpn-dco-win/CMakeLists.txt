# GCC/MinGW build of the ovpn-dco-win kernel driver.
#
# ovpn-dco-win is a KMDF 1.15 + NetAdapterCx 2.x client. This builds it
# against the ReactOS DDK, KMDF and NetAdapterCx headers:
#
#   REACTOS_SOURCE_DIR  ReactOS source tree (sdk/include, sdk/include/netcx,
#                       sdk/include/wdf/kmdf/1.17, sdk/cmake/init-section.lds)
#   REACTOS_BUILD_DIR   configured ReactOS amd64 build tree with the generated
#                       headers (ninja xdk psdk bugcodes), the import libraries
#                       of ntoskrnl, wdfldr, netio and cng, libcntpr and the
#                       netadaptercxstub_2_0/2_1 libraries
#
# NETADAPTER_VERSION_MINOR selects the flavor: 0 is OpenVPN's "win10"
# build (NetAdapterCx 2.0), 1 the "win11" build (NetAdapterCx 2.1).

cmake_minimum_required(VERSION 3.20)
project(ovpn-dco-win C CXX RC)

set(REACTOS_SOURCE_DIR "" CACHE PATH "ReactOS source tree")
set(REACTOS_BUILD_DIR "" CACHE PATH "Configured ReactOS amd64 build tree")
set(NETADAPTER_VERSION_MINOR 1 CACHE STRING "NetAdapterCx 2.x minor version")
set(KMDF_VERSION_MINOR 15 CACHE STRING "KMDF 1.x minor version the driver binds")
set(NTOSKRNL_IMPLIB "" CACHE FILEPATH "ntoskrnl import library (default: the ReactOS build tree's)")
set(OVPN_DCO_VERSION "2.8.13" CACHE STRING "Driver version")
set(DRIVER_DATE "" CACHE STRING "INF DriverVer date (MM/DD/YYYY)")

foreach(_v REACTOS_SOURCE_DIR REACTOS_BUILD_DIR)
    if(NOT IS_DIRECTORY "${${_v}}")
        message(FATAL_ERROR "${_v} must name a directory")
    endif()
endforeach()

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# A kernel driver: no user-mode default libraries, flags come from below
foreach(_lang C CXX)
    set(CMAKE_${_lang}_STANDARD_LIBRARIES "")
    foreach(_cfg DEBUG RELEASE RELWITHDEBINFO MINSIZEREL)
        set(CMAKE_${_lang}_FLAGS_${_cfg} "")
    endforeach()
endforeach()

set(ROS ${REACTOS_SOURCE_DIR})
set(ROSB ${REACTOS_BUILD_DIR})
set(GLUE ${CMAKE_CURRENT_SOURCE_DIR}/gcc)
string(REPLACE "." ";" _ver "${OVPN_DCO_VERSION}")
list(GET _ver 0 OVPN_DCO_VERSION_MAJOR)
list(GET _ver 1 OVPN_DCO_VERSION_MINOR)
list(GET _ver 2 OVPN_DCO_VERSION_PATCH)

if(NOT NTOSKRNL_IMPLIB)
    set(NTOSKRNL_IMPLIB ${ROSB}/ntoskrnl/CMakeFiles/libntoskrnl.dir/libntoskrnl.a)
endif()

# Fixed copies of the ReactOS headers ovpn-dco-win trips over
set(OVERLAY ${CMAKE_CURRENT_BINARY_DIR}/overlay)
execute_process(
    COMMAND ${Python3_EXECUTABLE} ${GLUE}/mkoverlay.py ${ROS} ${OVERLAY}
    COMMAND_ERROR_IS_FATAL ANY)

set(OVPN_SOURCES
    adapter.cpp bufferpool.cpp control.cpp crypto.cpp crypto_epoch.cpp
    Driver.cpp mss.cpp notifyqueue.cpp peer.cpp pktid.cpp rxqueue.cpp
    rxworkers.cpp socket.cpp timer.cpp trie.cpp txqueue.cpp)

# The version resource only needs the toolchain's own headers
add_library(ovpn-dco-res OBJECT ovpn-dco.rc)
target_compile_definitions(ovpn-dco-res PRIVATE
    OVPN_DCO_VERSION_MAJOR=${OVPN_DCO_VERSION_MAJOR}
    OVPN_DCO_VERSION_MINOR=${OVPN_DCO_VERSION_MINOR}
    OVPN_DCO_VERSION_PATCH=${OVPN_DCO_VERSION_PATCH}
    OVPN_DCO_VERSION_STR=${OVPN_DCO_VERSION})

add_executable(ovpn-dco
    ${OVPN_SOURCES}
    ${GLUE}/kmdfentry.c
    ${GLUE}/ovpn-gcc-shims.c
    $<TARGET_OBJECTS:ovpn-dco-res>)
set_target_properties(ovpn-dco PROPERTIES SUFFIX ".sys")

target_include_directories(ovpn-dco BEFORE PRIVATE
    ${OVERLAY}
    ${GLUE}
    ${ROS}/sdk/include/netcx/kmdf/adapter
    ${ROS}/sdk/include/netcx/shared/1.0
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
    ${ROS}/sdk/include/wdf/kmdf/1.17
    ${ROS}/sdk/lib/pseh/include)

target_compile_definitions(ovpn-dco PRIVATE
    _AMD64_ _M_AMD64 _M_X64 _WIN64 __REACTOS__ DBG=0
    _KERNEL_MODE _NEW_DELETE_OPERATORS_ _USE_PSEH3=1 USE_COMPILER_EXCEPTIONS
    WINVER=0x0A00 _WIN32_WINNT=0x0A00 NTDDI_VERSION=0x0A00000C DLL_EXPORT_VERSION=0x0A00
    WDF_DEVICE_NO_WDMSEC_H
    KMDF_VERSION_MAJOR=1 KMDF_VERSION_MINOR=${KMDF_VERSION_MINOR}
    NETADAPTER_VERSION_MAJOR=2 NETADAPTER_VERSION_MINOR=${NETADAPTER_VERSION_MINOR}
    RTL_USE_AVL_TABLES=0
    OVPN_DCO_VERSION_MAJOR=${OVPN_DCO_VERSION_MAJOR}
    OVPN_DCO_VERSION_MINOR=${OVPN_DCO_VERSION_MINOR}
    OVPN_DCO_VERSION_PATCH=${OVPN_DCO_VERSION_PATCH}
    OVPN_DCO_VERSION_STR=${OVPN_DCO_VERSION})

target_compile_options(ovpn-dco PRIVATE
    $<$<COMPILE_LANGUAGE:C,CXX>:
        -nostdinc -include ${GLUE}/ovpn-gcc-prelude.h
        -O2 -mcmodel=small -mcx16 -mlong-double-64 -fms-extensions -fno-strict-aliasing
        -fno-common -fno-exceptions -fno-aggressive-loop-optimizations
        -Wall -Wno-multichar -Wno-unknown-pragmas -Wno-write-strings -Wno-unused-result -Wno-unused-value>
    $<$<COMPILE_LANGUAGE:CXX>:-std=gnu++17 -fno-rtti -fpermissive>
    $<$<COMPILE_LANGUAGE:C>:-std=gnu11>)

target_link_options(ovpn-dco PRIVATE
    -nostdlib -s
    -Wl,--subsystem,native:10.0
    -Wl,--major-os-version,10,--minor-os-version,0
    "SHELL:-Xlinker --stack -Xlinker 0x100000,0x1000"
    -Wl,--entry,FxDriverEntry
    -Wl,--image-base,0x140000000
    -Wl,--file-alignment,0x200,--section-alignment,0x1000
    -Wl,--disable-auto-import,--disable-stdcall-fixup,--exclude-all-symbols
    -Wl,--disable-long-section-names
    -Wl,--dynamicbase,--nxcompat,--high-entropy-va
    -Wl,-T,${ROS}/sdk/cmake/init-section.lds)

target_link_libraries(ovpn-dco PRIVATE
    -Wl,--start-group
    ${ROSB}/sdk/lib/drivers/netadaptercxstub/libnetadaptercxstub_2_${NETADAPTER_VERSION_MINOR}.a
    ${ROSB}/sdk/lib/drivers/wdf/wdfldr/CMakeFiles/libwdfldr.dir/libwdfldr.a
    ${ROSB}/drivers/network/netio/CMakeFiles/libnetio.dir/libnetio.a
    ${ROSB}/drivers/crypto/cng/CMakeFiles/libcng.dir/libcng.a
    ${ROSB}/sdk/lib/crt/liblibcntpr.a
    ${NTOSKRNL_IMPLIB}
    gcc
    -Wl,--end-group)

# ReactOS pefixup marks INIT discardable, cleans up the section flags GNU ld
# sets and writes the image checksum the kernel loader checks. Like the WDK
# build, this is a plain kernel driver without the WDM_DRIVER flag.
if(EXISTS ${ROSB}/host-tools/bin/pefixup)
    add_custom_command(TARGET ovpn-dco POST_BUILD
        COMMAND ${ROSB}/host-tools/bin/pefixup --kernelmodedriver $<TARGET_FILE:ovpn-dco>)
endif()

# INF: fill in what stampinf would; no KMDF co-installer
add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/ovpn-dco.inf
    COMMAND ${Python3_EXECUTABLE} ${GLUE}/stampinf.py
            ${CMAKE_CURRENT_SOURCE_DIR}/ovpn-dco.inf ${CMAKE_CURRENT_BINARY_DIR}/ovpn-dco.inf
            amd64 1.${KMDF_VERSION_MINOR} ${OVPN_DCO_VERSION} "${DRIVER_DATE}"
    DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/ovpn-dco.inf ${GLUE}/stampinf.py)
add_custom_target(ovpn-dco-inf ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/ovpn-dco.inf)

install(TARGETS ovpn-dco RUNTIME DESTINATION .)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ovpn-dco.inf DESTINATION .)
