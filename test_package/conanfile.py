#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools
import os

class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    is_header_only = True

    def build(self):
        pass

    def test(self):
        with tools.pythonpath(self):
            import cmake_config_tools  # pylint: disable=F0401
            cpp_info = cmake_config_tools.cmake_find_package(self, self.source_folder, "Test")

