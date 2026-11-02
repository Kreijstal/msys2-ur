# Build system for XEDParse on MinGW (upstream ships only Visual Studio
# projects). Links Intel XED statically, like the upstream DLL.
cmake_minimum_required(VERSION 3.16)
project(XEDParse LANGUAGES CXX)

set(XED_KIT "" CACHE PATH "Intel XED kit (include/xed, lib/libxed.a)")
if(NOT EXISTS "${XED_KIT}/lib/libxed.a")
  message(FATAL_ERROR "XED_KIT must point at a built static XED kit")
endif()
add_library(xed_static STATIC IMPORTED)
set_target_properties(xed_static PROPERTIES
  IMPORTED_LOCATION "${XED_KIT}/lib/libxed.a"
  INTERFACE_INCLUDE_DIRECTORIES "${XED_KIT}/include")

file(GLOB XEDPARSE_SOURCES CONFIGURE_DEPENDS src/*.cpp)
add_library(XEDParse SHARED ${XEDPARSE_SOURCES})
set_target_properties(XEDParse PROPERTIES PREFIX "" IMPORT_PREFIX "lib"
  CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
target_compile_definitions(XEDParse PRIVATE XEDPARSE_BUILD)
target_compile_options(XEDParse PRIVATE -Wno-switch -Wno-writable-strings -Wno-write-strings
  -Wno-unknown-warning-option -Wno-nonportable-include-path)
target_link_libraries(XEDParse PRIVATE xed_static)

add_executable(XEDParseTest XEDParseTest/XEDParseTest.cpp)
set_target_properties(XEDParseTest PROPERTIES CXX_STANDARD 17)
target_include_directories(XEDParseTest PRIVATE src)
target_link_libraries(XEDParseTest PRIVATE XEDParse)

include(GNUInstallDirs)
install(TARGETS XEDParse
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES src/XEDParse.h DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/XEDParse)
