from conans import ConanFile, CMake, tools
import os
import re
import sys
from six import StringIO


def _parse_cmake_vars(output):
    res = {}
    start_reached = False
    for line in output.splitlines():
        if not start_reached:
            if "__BEGIN__" in line:
                start_reached = True
            continue
        elif "__END__" in line:
            break
        mobj = re.match(r"-- (\w+)=(.*)", line)
        if mobj:
            name = mobj.group(1)
            value = mobj.group(2)
            if ";" in value:
                value = value.split(";")
            res[name] = value
    return res


def cmake_find_package(conanfile, package_dir, package_name, cmake_subdir=""):
    """
    Use {package_name}Config.cmake to fetch CMake info about compiler and linker options"
    """
    detect_dir = os.path.join(conanfile.build_folder, "_cmake_config_tools")
    cmake_expand_imported_targets = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "CMakeExpandImportedTargets.cmake")
    cmake_dir = os.path.abspath(os.path.join(package_dir, cmake_subdir))
    cmakelists_txt = """
cmake_minimum_required(VERSION 2.8.12)
include({cmake_expand_imported_targets})
include({cmake_dir}/{package_name}Config.cmake)
cmake_expand_imported_targets({package_name}_LIBRARIES_DEBUG_EXPANDED LIBRARIES ${{{package_name}_LIBRARIES}} CONFIGURATION DEBUG)
cmake_expand_imported_targets({package_name}_LIBRARIES_RELEASE_EXPANDED LIBRARIES ${{{package_name}_LIBRARIES}} CONFIGURATION RELEASE)
set({package_name}_LIBRARIES ${{{package_name}_LIBRARIES_DEBUG_EXPANDED}} ${{{package_name}_LIBRARIES_RELEASE_EXPANDED}})
message(STATUS __BEGIN__)
get_cmake_property(_variableNames VARIABLES)
foreach (_variableName ${{_variableNames}})
    string(REGEX MATCH "^{package_name}" _ovar ${{_variableName}})
    if(NOT _ovar STREQUAL "")
        message(STATUS "${{_variableName}}=${{${{_variableName}}}}")
    endif()
endforeach()
message(STATUS __END__)
"""
    cmakelists_txt = cmakelists_txt.format(cmake_expand_imported_targets=cmake_expand_imported_targets.replace("\\", "/"),
                                           cmake_dir=cmake_dir.replace("\\", "/"),
                                           package_name=package_name)

    cmakelists_txt_path = os.path.join(detect_dir, "CMakeLists.txt")
    tools.save(cmakelists_txt_path, cmakelists_txt)

    cmake = CMake(conanfile)
    cmd = "cmake . " + cmake.command_line
    output = StringIO()
    try:
        conanfile.run(cmd, cwd=detect_dir, output=output)
    except:
        sys.stderr.write(output.getvalue())
        raise
    cmake_vars = _parse_cmake_vars(output.getvalue())
    # for (key, value) in cmake_vars.items():
    #     sys.stderr.write("{0}={1}\n".format(key, value))

    for key in ["INCLUDE_DIRS", "LIBRARIES"]:
        var = package_name+"_"+key
        if not var in cmake_vars:
            sys.stderr.write(output.getvalue())
            raise Exception("Missing variable {0}".format(var))
    output.close()

    cpp_info = {}
    cpp_info["cmake_vars"] = cmake_vars
    cpp_info["includedirs"] = [os.path.relpath(path, package_dir)
                               for path in cmake_vars[package_name+"_INCLUDE_DIRS"]]
    if cpp_info["includedirs"] == []:
        raise Exception("No {0} includedirs extracted".format(package_name))
    libs = []
    libdirs = []
    package_dir_norm = os.path.normpath(os.path.normcase(package_dir))
    for libpath in cmake_vars[package_name+"_LIBRARIES"]:
        libdir, lib = os.path.split(libpath)
        libdir_norm = os.path.normpath(os.path.normcase(libdir))
        # libname.so.1.2 -> name (conan links libs as -lname under Linux)
        if lib.startswith("lib") and conanfile.settings.os != "Windows":
            lib = lib[3:]
        lib = lib.split(".")[0]
        if libdir == "" or libdir_norm.startswith(package_dir_norm):
            # include system libs like ws2_32, exclude external libs
            if libdir != "":
                libdirs.append(os.path.relpath(libdir_norm, package_dir_norm))
            libs.append(lib)
    if libs == []:
        raise Exception("No {0} libs extracted".format(package_name))
    cpp_info["libs"] = libs
    if libdirs == []:
        raise Exception("No {0} libdirs extracted".format(package_name))
    cpp_info["libdirs"] = list(set(libdirs))

    return cpp_info
