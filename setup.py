#! /usr/bin/env python
import os

from setuptools import setup, find_packages
from setuptools.command.install import install


NAME = "oasys2"
VERSION = "0.0.1"
DESCRIPTION = "Core component of OASYS 2.0"

with open("README.md", "rt", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

URL = "https://www.aps.anl.gov/Science/Scientific-Software/OASYS"
AUTHOR = "Manuel Sanchez del Rio & Luca Rebuffi"
AUTHOR_EMAIL = 'lrebuffi@aps.gov'

LICENSE = "BSD3"
DOWNLOAD_URL = 'https://github.com/oasys-kit/OASYS2'
PACKAGES = find_packages()

PACKAGE_DATA = {
    "oasys2.canvas": ["icons/*.svg", "icons/*png"],
    "oasys2.canvas.styles": ["*.qss", "orange/*.svg"],
}

INSTALL_REQUIRES = (
    "orange-canvas-core<=0.2.8",
    "orange-widget-base<=4.27.0",
)

CLASSIFIERS = (
    "Development Status :: 1 - Planning",
    "Environment :: X11 Applications :: Qt",
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent",
    "Topic :: Scientific/Engineering :: Visualization",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Intended Audience :: Education",
    "Intended Audience :: Developers",
)

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
        long_description_content_type="text/x-md",
        url=URL,
        author=AUTHOR,
        author_email=AUTHOR_EMAIL,
        license=LICENSE,
        packages=PACKAGES,
        package_data=PACKAGE_DATA,
        install_requires=INSTALL_REQUIRES,
        extras_require=EXTRAS_REQUIRE,
        project_urls=PROJECT_URLS,
        python_requires=PYTHON_REQUIRES,
    )
