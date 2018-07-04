from conans import CMake, tools
import json
import os
import re
import subprocess
import sys


def _realpath(path):
    # work around Windows bug https://stackoverflow.com/questions/43333640/python-os-path-realpath-for-symlink-in-windows
    real_path = path if not os.path.islink(path) else os.readlink(path)
    head, tail = os.path.split(real_path)
    if tail == '':
        return head
    else:
        return os.path.join(_realpath(head), tail)

def _normpath(path):
    return _realpath(
        os.path.normcase(
            os.path.normpath(path)))

def cmake_find_package(conanfile, package_dir, package_name, cmake_subdir=""):
    """
    Use {package_name}Config.cmake to fetch CMake info about compiler and linker options"
    """
    detect_dir = os.path.join(conanfile.build_folder, "_cmake_config_tools")
    export_dir = os.path.dirname(os.path.abspath(__file__))
    cmake_dir = os.path.abspath(os.path.join(package_dir, cmake_subdir))
    cmakelists_txt = """
cmake_minimum_required(VERSION 2.8.12)
include({cmake_dir}/{package_name}Config.cmake)

add_executable(exe_with_lib {export_dir}/main.c)
target_include_directories(exe_with_lib PUBLIC ${{{package_name}_INCLUDE_DIRS}})
target_link_libraries(exe_with_lib ${{{package_name}_LIBRARIES}})

add_executable(exe_clean {export_dir}/main.c)
"""
    cmakelists_txt = cmakelists_txt.format(cmake_dir=cmake_dir.replace("\\", "/"),
                                           export_dir=export_dir.replace(
                                               "\\", "/"),
                                           package_name=package_name)
    cmakelists_txt_path = os.path.join(detect_dir, "CMakeLists.txt")
    tools.save(cmakelists_txt_path, cmakelists_txt)

    cmake = CMake(conanfile)
    cmake.configure(source_folder=detect_dir, build_folder=detect_dir)

    cmake_exe = os.path.join(os.environ["CCT_CMAKE_ROOT"], "bin", "cmake")
    p = subprocess.Popen([cmake_exe,
                          "-E", "server", "--debug", "--experimental"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

    prolog = '[== "CMake Server" ==['
    epilog = ']== "CMake Server" ==]'
    encoding = "utf-8" if sys.stdout.encoding is None else sys.stdout.encoding

    def write_json(d):
        s = '\n'.join([prolog, json.dumps(d), epilog, ''])
        p.stdin.write(s.encode(encoding))

    def read_json():
        f = p.stdout
        while True:
            line = f.readline().strip().decode(encoding)
            if line != '':
                break
        if line != prolog:
            raise Exception("cmake server unexpected response: '%s'\n" % line)
        s = ''
        while True:
            line = f.readline().strip().decode(encoding)
            if line == epilog:
                break
            s += line
        return json.loads(s)

    def cmake_cmd(req):
        # print(">>>", req)
        write_json(req)
        while True:
            res = read_json()
            # print("<<<", res)
            typ = res["type"]
            if typ == "error":
                raise Exception("cmake server error: '%s'\n" %
                                res["errorMessage"])
            elif typ == "message":
                sys.stdout.write("cmake server: " + res["message"]+"\n")
            elif typ == "progress":
                sys.stdout.write("cmake server: " +
                                 res["progressMessage"]+"\n")
            elif typ == "reply":
                return res

    res = read_json()
    if res["type"] != "hello":
        raise Exception("unexpected cmake server handshake: '%s'\n" % str(res))
    supported_protocols = res["supportedProtocolVersions"]
    expected_protocols = [{"isExperimental": True, "major": 1, "minor": 2}]
    protocol = None
    for p1 in supported_protocols:
        for p2 in expected_protocols:
            if p1["isExperimental"] == p2["isExperimental"] and \
                    p1["major"] == p2["major"] and \
                    p1["minor"] == p2["minor"]:
                protocol = p1
    if protocol is None:
        cmake_cmd({"type": "handshake",
                   "protocolVersion": supported_protocols[0], "buildDirectory": detect_dir})
        res = cmake_cmd({"type": "globalSettings"})
        version = res["capabilities"]["version"]["string"]
        raise Exception("cmake server %s: protocols %s are not in supported protocols %s\n" % (
            version, str(expected_protocols), str(supported_protocols)))
    cmake_cmd({"type": "handshake", "protocolVersion": protocol,
               "buildDirectory": detect_dir})
    cmake_cmd({"type": "configure"})
    cmake_cmd({"type": "compute"})
    res = cmake_cmd({"type": "codemodel"})
    p.terminate()

    includedirs = []
    libpaths = []
    libpaths_clean = []

    for config in res["configurations"]:
        if config["name"] != conanfile.settings.build_type:
            continue
        for projects in config["projects"]:
            for target in projects["targets"]:
                name = target["name"]
                if "linkLibraries" in target:
                    linkLibraries = target["linkLibraries"].split(' ')
                else:
                    linkLibraries = []
                if name == "exe_with_lib":
                    includedirs = []
                    for fileGroup in target["fileGroups"]:
                        for includePath in fileGroup["includePath"]:
                            includedirs.append(includePath["path"])
                    libpaths = linkLibraries
                elif name == "exe_clean":
                    libpaths_clean = linkLibraries

    def unique(seq):
        # preserves order
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]

    includedirs = unique(includedirs)
    libpaths = [p for p in libpaths if p not in libpaths_clean]
    # cmake may duplicate libs, leave an element nearest to the end
    libpaths = list(reversed(unique(reversed(libpaths))))

    cpp_info = {}
    package_dir_norm = _normpath(package_dir)
    includedirs = [os.path.relpath(_normpath(d), package_dir_norm)
                   if _normpath(d).startswith(package_dir_norm) else d for d in includedirs]
    if includedirs == []:
        raise Exception("No {0} includedirs extracted".format(package_name))
    cpp_info["includedirs"] = includedirs
    libs = []
    libdirs = []
    for libpath in libpaths:
        wl_rpath = "-Wl,-rpath,"
        if conanfile.settings.compiler != "Visual Studio" and libpath.startswith(wl_rpath):
            for libdir in libpath[len(wl_rpath):].split(os.sep):
                libdir_norm = _normpath(libdir)
                if libdir_norm.startswith(package_dir_norm):
                    libdirs.append(os.path.relpath(libdir_norm, package_dir_norm))
        else:
            libdir, lib = os.path.split(libpath)
            libdir_norm = _normpath(libdir)
            # extract lib name
            if conanfile.settings.compiler == "Visual Studio":
                if lib.lower().endswith(".lib"):
                    lib = lib[:-4]
            else:
                if lib.startswith("-l"):
                    lib = lib[2:]
                elif libdir != "" and not lib.startswith(':'):
                    # prevent lib<lib>.a expansion
                    lib = ':' + lib
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
    cpp_info["libdirs"] = unique(libdirs)

    return cpp_info
