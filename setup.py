#! /usr/bin/env python
import os

from setuptools import setup, find_packages
from setuptools.command.install import install


NAME        = "oasys2"
VERSION     = "0.0.1"
DESCRIPTION = "Core component of OASYS 2.0"

with open("README.md", "rt", encoding="utf-8") as f: LONG_DESCRIPTION = f.read()

URL = "https://www.aps.anl.gov/Science/Scientific-Software/OASYS"
AUTHOR = "Manuel Sanchez del Rio & Luca Rebuffi"
AUTHOR_EMAIL = 'lrebuffi@aps.gov'

LICENSE = "BSD3"
DOWNLOAD_URL = 'https://github.com/oasys-kit/OASYS2'


PACKAGES = [
    "oasys2",
    "oasys2.canvas",
    #"oasys2.canvas.styles",
    "oasys2.canvas.menus",
    "oasys2.widget",
    "oasys2.widgets",
    "oasys2.widgets.test",
    "oasys2.widgets.loops",
    "oasys2.widgets.scanning",
    "oasys2.widgets.tools",
]

PACKAGE_DATA = {
    "oasys2.application": ["data/*.txt"],
    "oasys2.canvas": ["icons/*.png", "icons/*.svg"],
    "oasys2.widgets.test": ["icons/*.png", "icons/*.svg"],
    "oasys2.widgets.loops": ["icons/*.png", "icons/*.svg"],
    "oasys2.widgets.scanning": ["icons/*.png", "icons/*.svg"],
    "oasys2.widgets.tools": ["icons/*.png", "icons/*.svg"],
}

ENTRY_POINTS = {
    'oasys2.widgets' : (
        "Oasys Test = oasys2.widgets.test",
        "Oasys Tools = oasys2.widgets.tools",
        "Oasys Basic Loops = oasys2.widgets.loops",
        "Oasys Scanning Loops = oasys2.widgets.scanning",
    )
}

INSTALL_REQUIRES = (
    "numpy==2.2.6",
    "fabio==2024.9.0",
    "scipy==1.16.1",
    "srxraylib",
    "syned",
    "xoppylib",
    "wofry",
    "wofryimpl",
    "silx==2.2.2",
    "PyQt5==5.15.11",
    "h5py==3.14.0",
    "orange-canvas-core<=0.2.8",
    "orange-widget-base<=4.27.0",
)

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: X11 Applications :: Qt',
    'Environment :: Console',
    'Environment :: Plugins',
    'Programming Language :: Python',
    'Operating System :: POSIX',
    'Operating System :: Microsoft :: Windows',
    'Topic :: Scientific/Engineering :: Artificial Intelligence',
    'Topic :: Scientific/Engineering :: Visualization',
    'Topic :: Software Development :: Libraries :: Python Modules',
    'Intended Audience :: Education',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
]

EXTRAS_REQUIRE = {
}

PROJECT_URLS = {
    "Bug Reports": "https://github.com/oasys-kit/OASYS2/issues",
    "Source": "https://github.com/oasys-kit/OASYS2",
    "Documentation": "https://orange-canvas-core.readthedocs.io/en/latest/",
}

PYTHON_REQUIRES = ">=3.11"

if __name__ == "__main__":
    setup(
        name=NAME,
        version=VERSION,
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        long_description_content_type="text/markdown",
        url=URL,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        license=LICENSE,
        classifiers=CLASSIFIERS,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        entry_points=ENTRY_POINTS,
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRAS_REQUIRE,
        project_urls=PROJECT_URLS,
        python_requires=PYTHON_REQUIRES,
    )
