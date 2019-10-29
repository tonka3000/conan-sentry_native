import os
from conans import ConanFile, CMake, tools


class LibnameConan(ConanFile):
    name = "sentry_native"
    description = "Sentry SDK for C, C++ and native applications"
    topics = ("conan", "sentry", "sentry-native", "sentry_native", "logging")
    url = "https://github.com/bincrafters/conan-sentry_native"
    homepage = "https://github.com/getsentry/sentry-native"
    license = "MIT"
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": False,
        "fPIC": True
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    build_requires = "cmake_installer/3.10.0@conan/stable"

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name.replace("_", "-") + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure(build_folder=self._build_subfolder)
        return cmake

    def _system_package_architecture(self):
        if tools.os_info.with_apt:
            if self.settings.arch == "x86":
                return ':i386'
            elif self.settings.arch == "x86_64":
                return ':amd64'
            elif self.settings.arch == "armv6" or self.settings.arch == "armv7":
                return ':armel'
            elif self.settings.arch == "armv7hf":
                return ':armhf'
            elif self.settings.arch == "armv8":
                return ':arm64'

        if tools.os_info.with_yum:
            if self.settings.arch == "x86":
                return '.i686'
            elif self.settings.arch == 'x86_64':
                return '.x86_64'
        return ""

    def system_requirements(self):
        pack_names = []
        if tools.os_info.is_linux:
            if tools.os_info.with_apt:
                pack_names = ["uuid-dev",
                              "libcurl4-openssl-dev", "zlib1g-dev"]
            # other package manager not supported at the moment

        if pack_names:
            installer = tools.SystemPackageTool()
            for item in pack_names:
                installer.install(
                    item + self._system_package_architecture())

    def build(self):
        cmakelists = os.path.join(
            self.build_folder, self._source_subfolder, "CMakeLists.txt")

        if not self.options.shared:
            tools.replace_in_file(cmakelists, "SHARED", "STATIC")

        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses",
                  src=self._source_subfolder)
        cmake = self._configure_cmake()
        # cmake.install()
        # sentry-native has no cmake install commands, so we have to copy it manually
        include_folder = os.path.join(self._source_subfolder, "include")
        self.copy(pattern="*", dst="include", src=include_folder)
        self.copy(pattern="*.dll", dst="bin", keep_path=False)
        self.copy(pattern="*.lib", dst="lib", keep_path=False)
        self.copy(pattern="*.a", dst="lib", keep_path=False)
        self.copy(pattern="*.so*", dst="lib", keep_path=False)
        self.copy(pattern="*.dylib", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
