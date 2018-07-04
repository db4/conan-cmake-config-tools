if(WIN32)
    set(lib1 lib1.lib)
    set(lib2 lib2.lib)
    set(lib3 lib3.0.lib)
    set(lib4 lib4.lib)
else()
    set(lib1 liblib1.a)
    set(lib2 liblib2.so)
    set(lib3 :liblib3.0.so.1)
    set(lib4 -llib4)
endif()

set(Test_LIBRARIES
    ${CMAKE_CURRENT_LIST_DIR}/libdir1/${lib1}
    ${CMAKE_CURRENT_LIST_DIR}/libdir2/${lib2}
    ${CMAKE_CURRENT_LIST_DIR}/libdir3/${lib3}
    ${lib4}
)

set(Test_INCLUDE_DIRS ${CMAKE_CURRENT_LIST_DIR}/include_dirs)
set(Test_FOUND ON)
