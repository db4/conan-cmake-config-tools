from conans import ConanFile


class CMakeConfigToolsConan(ConanFile):
    name = "cmake_config_tools"
    version = "0.0.1"
    url = "https://github.com/db4/conan-cmake-config-tools.git"
    description = "Shared python/cmake code for various CMake config utilities"
    license = "MIT"
    exports_sources = "*.cmake", "cmake_config_tools.py"

    def package(self):
        self.copy('*.cmake')
        self.copy('cmake_config_tools.py')

    def package_info(self):
        self.env_info.PYTHONPATH.append(self.package_folder)
