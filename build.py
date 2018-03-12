from conan.packager import ConanMultiPackager


if __name__ == "__main__":
    builder = ConanMultiPackager(username="dbely")
    builder.add(settings={}, options={}, env_vars={}, build_requires={})
    builder.run()
