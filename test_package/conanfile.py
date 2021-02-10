#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools
from conans.errors import ConanException
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    is_header_only = True

    def build(self):
        pass

    def test(self):
        with tools.pythonpath(self):
            import cmake_config_tools  # pylint: disable=F0401
            cpp_info = cmake_config_tools.cmake_find_package(
                self, self.source_folder, "Test")

            def cpp_info_equal(d1, d2):
                return \
                    d1["libs"] == d2["libs"] and \
                    d1["syslibs"] == d2["syslibs"] and \
                    set(d1["libdirs"]) == set(d1["libdirs"]) and \
                    set(d1["includedirs"]) == set(d1["includedirs"])

            expected_cpp_info = {
                "libs": ["lib1", "lib2", "lib3.0", "lib4"],
                "syslibs": [],
                "libdirs": ["libdir1", "libdir2", "libdir3"],
                "includedirs": ["include_dirs"]
            }
            if self.settings.compiler == "Visual Studio":
                expected_cpp_info["syslibs"] = ['kernel32', 'user32', 'gdi32', 'winspool',
                                                'shell32', 'ole32', 'oleaut32', 'uuid', 'comdlg32', 'advapi32']
            if not cpp_info_equal(cpp_info, expected_cpp_info):
                raise ConanException("Error: expected cpp_info %s, but got %s" % (
                    str(expected_cpp_info), str(cpp_info)))
