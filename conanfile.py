import os
from conans import ConanFile, CMake, tools, MSBuild

_sentry_use_cmake = os.environ.get("SENTRY_USE_CMAKE", "False").lower()
_force_use_cmake = True if _sentry_use_cmake in ["true", "1"] else False


class LibnameConan(ConanFile):
    name = "sentry_native"
    description = "Sentry SDK for C, C++ and native applications"
    topics = ("conan", "sentry", "sentry-native", "sentry_native", "logging")
    url = "https://github.com/bincrafters/conan-sentry_native"
    homepage = "https://github.com/getsentry/sentry-native"
    license = "MIT"
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    short_paths = True

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False]
    }
    default_options = {
        "shared": True,
        "fPIC": True
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def build_requirements(self):
        if self.settings.os == "Windows":
            self.build_requires("msys2/20161025")  # for make on windows
        if self._use_cmake:
            self.build_requires("cmake_installer/3.10.0@conan/stable")
        else:
            self.build_requires(
                "premake_installer/5.0.0-alpha14@bincrafters/stable")

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name.replace("_", "-") + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)
        with tools.chdir(self._source_subfolder):
            self.output.info("fetch breakpad")
            self.run("make fetch-breakpad")

            self.output.info("fetch crashpad")
            self.run("make fetch-crashpad")

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

    @property
    def _use_cmake(self):
        return _force_use_cmake or self.settings.os == "Macos"

    def build(self):
        if self._use_cmake:
            # premake does not work nice in Macos, so we use cmake build here
            self._build_cmake()
        else:
            self._build_premake()

    def _build_cmake(self):
        cmakelists = os.path.join(
            self.build_folder, self._source_subfolder, "CMakeLists.txt")

        if not self.options.shared:
            tools.replace_in_file(cmakelists, "SHARED", "STATIC")

        cmake = self._configure_cmake()
        cmake.build()

    def _build_premake(self):
        premake_folder = os.path.join(
            self.build_folder, self._source_subfolder, "premake")
        premake_file = os.path.join(premake_folder, "premake5.lua")
        tools.replace_in_file(premake_file,
                              'targetdir "bin/%{cfg.architecture}/%{cfg.buildcfg}"',
                              'targetdir "bin"')

        premake_file_sentry = os.path.join(
            premake_folder, "premake5.sentry.lua")
        tools.replace_in_file(premake_file_sentry, '"bin/Release"', '"bin"')

        config = "release" if self.settings.build_type != "Debug" else "debug"

        with tools.chdir("{}/premake".format(self._source_subfolder)):
            if self.settings.compiler == "Visual Studio":
                premake_vs = {
                    "14": "vs2015",
                    "15": "vs2017",
                    "16": "vs2019"
                }
                premake_vs_tag = premake_vs.get(
                    str(self.settings.compiler.version))
                if not premake_vs_tag:
                    raise Exception("unsupported Visual Studio version {}".format(
                        str(self.settings.compiler.version)))

                self.output.info("configure with premake")
                self.run("premake5 {}".format(premake_vs_tag))
                self.run("ls -la")
                msbuild = MSBuild(self)
                msbuild.build("Sentry-Native.sln")  # sentry.vcxproj

            else:
                self.output.info("configure with premake")
                self.run("premake5 gmake2")
                self.output.info("make {}".format(config))
                self.run("make config={} sentry".format(config))

    def package(self):
        self.copy(pattern="LICENSE", dst="licenses",
                  src=self._source_subfolder)

        # sentry-native has no cmake install commands, so we have to copy it manually
        bin_folder = os.path.join(self._source_subfolder, "premake", "bin")
        include_folder = os.path.join(self._source_subfolder, "include")
        self.copy(pattern="*", dst="include", src=include_folder)
        if self._use_cmake:
            self.copy(pattern="*.dll", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)
            self.copy(pattern="*.a", dst="lib", keep_path=False)
            self.copy(pattern="*.so*", dst="lib", keep_path=False)
            self.copy(pattern="*.dylib*", dst="lib", keep_path=False)
        else:
            self.copy(pattern="*.dll", dst="bin",
                      src=bin_folder, keep_path=False)
            self.copy(pattern="*.lib", dst="lib",
                      src=bin_folder, keep_path=False)
            self.copy(pattern="*.a", dst="lib",
                      src=bin_folder, keep_path=False)
            self.copy(pattern="*.so*", dst="lib",
                      src=bin_folder, keep_path=False)
            self.copy(pattern="*.dylib*", dst="lib",
                      src=bin_folder, keep_path=False)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
