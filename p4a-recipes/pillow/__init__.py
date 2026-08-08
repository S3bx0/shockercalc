"""python-for-android recipe for Pillow 12.3.0.

Kept as a small, reviewed copy of the Pillow recipe from the project's pinned
python-for-android commit (58d21141f17c889bf8585f5665921d72028f8831).
The local recipe can be removed once upstream provides an equivalent release.
"""

from os.path import join

from pythonforandroid.recipe import PyProjectRecipe


class PillowRecipe(PyProjectRecipe):
    version = "12.3.0"
    url = "https://files.pythonhosted.org/packages/source/p/pillow/pillow-{version}.tar.gz"
    sha256sum = "3b8182a766685eaa002637e28b4ec8d6b18819a0c71f579bf0dbaa5830297cce"
    site_packages_name = "PIL"
    patches = ["setup.py.patch"]
    depends = ["png", "jpeg", "freetype"]
    hostpython_prerequisites = ["setuptools>=77"]
    opt_depends = ["libwebp"]

    # Pillow 12 exposes its cross-build configuration through PEP 517. Avoid
    # probing host paths; all target roots are supplied explicitly below.
    extra_build_args = ["--config-setting", "platform-guessing=disable"]

    def get_recipe_env(self, arch, **kwargs):
        env = super().get_recipe_env(arch, **kwargs)
        env["LDFLAGS"] = env.get("LDFLAGS", "") + " -lm"
        env["PKG_CONFIG"] = "p4a-pkg-config-disabled"

        jpeg = self.get_recipe("jpeg", self.ctx)
        jpeg_inc_dir = jpeg_lib_dir = jpeg.get_build_dir(arch.arch)
        env["JPEG_ROOT"] = f"{jpeg_lib_dir}:{jpeg_inc_dir}"

        freetype = self.get_recipe("freetype", self.ctx)
        free_lib_dir = join(freetype.get_build_dir(arch.arch), "objs", ".libs")
        free_inc_dir = join(freetype.get_build_dir(arch.arch), "include")
        env["FREETYPE_ROOT"] = f"{free_lib_dir}:{free_inc_dir}"

        harfbuzz = self.get_recipe("harfbuzz", self.ctx)
        harf_lib_dir = join(harfbuzz.get_build_dir(arch.arch), "src", ".libs")
        harf_inc_dir = harfbuzz.get_build_dir(arch.arch)
        env["HARFBUZZ_ROOT"] = f"{harf_lib_dir}:{harf_inc_dir}"

        env["ZLIB_ROOT"] = (
            f"{arch.ndk_lib_dir_versioned}:{self.ctx.ndk.sysroot_include_dir}"
        )

        if "libwebp" in self.ctx.recipe_build_order:
            webp = self.get_recipe("libwebp", self.ctx)
            webp_install = join(webp.get_build_dir(arch.arch), "installation")
            env["WEBP_ROOT"] = (
                f"{join(webp_install, 'lib')}:{join(webp_install, 'include')}"
            )
        return env


recipe = PillowRecipe()
