from conans import ConanFile


class CMakeConfigToolsConan(ConanFile):
    name = "cmake_config_tools"
    version = "0.0.1"
    url = "https://github.com/db4/conan-cmake-config-tools.git"
    description = "Shared python/cmake code for various CMake config utilities"
    license = "MIT"
    exports_sources = "cmake_config_tools.py", "main.c"
    requires = "cmake_installer/3.11.3@conan/stable"

    def package(self):
        self.copy('cmake_config_tools.py')
        self.copy('main.c')

    def package_info(self):
        self.output.info("Appending PYTHONPATH env var with : " + self.package_folder)
        self.env_info.PYTHONPATH.append(self.package_folder)

        cmake_root = self.deps_env_info["cmake_installer"].CMAKE_ROOT
        self.output.info("Creating CCT_CMAKE_ROOT env var : " + cmake_root)
        self.env_info.CCT_CMAKE_ROOT = cmake_root
