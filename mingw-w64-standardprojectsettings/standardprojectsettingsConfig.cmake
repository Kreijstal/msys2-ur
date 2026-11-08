# The helpers Ultimaker's projects call; Conan normally injects them.
include(GNUInstallDirs)

function(use_threads target)
  find_package(Threads REQUIRED)
  get_target_property(_type ${target} TYPE)
  if(_type STREQUAL "INTERFACE_LIBRARY")
    target_link_libraries(${target} INTERFACE Threads::Threads)
  else()
    target_link_libraries(${target} PRIVATE Threads::Threads)
  endif()
endfunction()

# warnings and sanitizers stay the distribution's choice
function(set_project_warnings target)
endfunction()

function(enable_sanitizers target)
endfunction()

function(AssureOutOfSourceBuilds)
endfunction()
