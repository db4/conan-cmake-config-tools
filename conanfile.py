from conans import ConanFile


class CMakeConfigToolsConan(ConanFile):
    name = "cmake_config_tools"
    version = "0.0.2"
    url = "https://github.com/db4/conan-cmake-config-tools.git"
    description = "Shared python/cmake code for various CMake config utilities"
    license = "MIT"
    exports_sources = "cmake_config_tools.py", "main.c"

    def package(self):
        self.copy('cmake_config_tools.py')
        self.copy('main.c')

    def package_info(self):
        self.output.info("Appending PYTHONPATH env var with : " + self.package_folder)
        self.env_info.PYTHONPATH.append(self.package_folder)
