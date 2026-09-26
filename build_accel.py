# Compile C extensions: python build_accel.py build_ext --inplace
from setuptools import setup, Extension

setup(
    name="gamekit_accel",
    ext_modules=[
        Extension(
            "gamekit._accel",
            sources=["gamekit/_accel.c"],
            libraries=["gdi32"],
        ),
        Extension(
            "gamekit._d2d",
            sources=["gamekit/_d2d.cpp"],
            libraries=["d2d1", "ole32", "user32"],
        ),
        Extension(
            "gamekit._d3d11",
            sources=["gamekit/_d3d11.cpp"],
            libraries=["d3d11", "dxgi", "d3dcompiler", "user32"],
        ),
    ],
)
