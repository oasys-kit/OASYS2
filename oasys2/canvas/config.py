#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
# Copyright (c) 2025, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2025. UChicago Argonne, LLC. This software was produced       #
# under U.S. Government contract DE-AC02-06CH11357 for Argonne National   #
# Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    #
# U.S. Department of Energy. The U.S. Government has rights to use,       #
# reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    #
# UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        #
# ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     #
# modified to produce derivative works, such modified software should     #
# be clearly marked, so as not to confuse it with the version available   #
# from ANL.                                                               #
#                                                                         #
# Additionally, redistribution and use in source and binary forms, with   #
# or without modification, are permitted provided that the following      #
# conditions are met:                                                     #
#                                                                         #
#     * Redistributions of source code must retain the above copyright    #
#       notice, this list of conditions and the following disclaimer.     #
#                                                                         #
#     * Redistributions in binary form must reproduce the above copyright #
#       notice, this list of conditions and the following disclaimer in   #
#       the documentation and/or other materials provided with the        #
#       distribution.                                                     #
#                                                                         #
#     * Neither the name of UChicago Argonne, LLC, Argonne National       #
#       Laboratory, ANL, the U.S. Government, nor the names of its        #
#       contributors may be used to endorse or promote products derived   #
#       from this software without specific prior written permission.     #
#                                                                         #
# THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     #
# Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        #
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    #
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        #
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      #
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       #
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         #
# POSSIBILITY OF SUCH DAMAGE.                                             #
# ----------------------------------------------------------------------- #
import os
import sys
import logging
import warnings
import typing
import pkgutil

from typing import Dict, Optional, Tuple, List, Union, Iterable, Any

import packaging.version

from AnyQt.QtGui import (
    QPainter, QFont, QFontMetrics, QColor, QPixmap, QImage, QIcon
)

from AnyQt.QtCore import (
    Qt, QCoreApplication, QPoint, QRect
)

from orangecanvas.utils.pkgmeta import EntryPoint, entry_points

import orangecanvas.config as orangeconfig


#: Entry point by which widgets are registered.
WIDGETS_ENTRY = "oasys2.widgets"
MENU_ENTRY = "oasys2.menus"

#: Entry point by which add-ons register with importlib.metadata
ADDONS_ENTRY = "oasys2.addon"

#: Parameters for searching add-on packages in PyPi using xmlrpc api.
ADDON_PYPI_SEARCH_SPEC = {"keywords": ["oasys2", "add-on"]}

EXAMPLE_WORKFLOWS_ENTRY = "oasys2.examples"

class Default(orangeconfig.Config):

    OrganizationDomain = "Oasys Organization"
    ApplicationName = "Oasys"
    ApplicationVersion = "2.0"

    @staticmethod
    def application_icon():
        """
        Return the main application icon.
        """
        contents = pkgutil.get_data(__name__, "icons/oasys.png")
        img = QImage.fromData(contents, "png")
        pm = QPixmap.fromImage(img)
        return QIcon(pm)

    @staticmethod
    def splash_screen():
        # type: () -> Tuple[QPixmap, QRect]
        """
        Return a splash screen pixmap and an text area within it.

        The text area is used for displaying text messages during application
        startup.

        The default implementation returns a bland rectangle splash screen.

        Returns
        -------
        t : Tuple[QPixmap, QRect]
            A QPixmap and a rect area within it.
        """

        contents = pkgutil.get_data(__name__, "icons/oasys-splash-screen.png")
        img = QImage.fromData(contents, "png")
        pm = QPixmap.fromImage(img)
        version = QCoreApplication.applicationVersion()
        if version:
            version_parsed = packaging.version.Version(version)
            version_comp = version_parsed.release
            version = ".".join(map(str, version_comp[:2]))
        size = 21 if len(version) < 5 else 16
        font = QFont()
        font.setPixelSize(size)
        font.setBold(True)
        font.setItalic(True)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        metrics = QFontMetrics(font)
        br = metrics.boundingRect(version).adjusted(-5, 0, 5, 0)
        #br.moveBottomRight(QPoint(pm.width() - 15, pm.height() - 15))
        br.moveCenter(QPoint(412, 214))

        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(font)
        p.setPen(QColor("#231F20"))
        p.drawText(br, Qt.AlignCenter, version)
        p.end()
        textarea = QRect(15, 15, 170, 20)
        return pm, textarea

    @staticmethod
    def widgets_entry_points() -> Iterable[EntryPoint]:
        """
        Return an iterator over entry points defining the set of
        'nodes/widgets' available to the workflow model.
        """
        return iter(entry_points(group=WIDGETS_ENTRY))

    @staticmethod
    def addon_entry_points() -> Iterable[EntryPoint]:
        return  iter(entry_points(group=ADDONS_ENTRY))

    @staticmethod
    def addon_pypi_search_spec():
        return dict(ADDON_PYPI_SEARCH_SPEC)

    @staticmethod
    def addon_defaults_list(session=None):
        """
        Return a list of default add-ons.

        The return value must be a list with meta description following the
        `PyPI JSON api`_ specification. At the minimum 'info.name' and
        'info.version' must be supplied. e.g.

            `[{'info': {'name': 'Super Pkg', 'version': '4.2'}}]

        .. _`PyPI JSON api`:
            https://warehouse.readthedocs.io/api-reference/json/
        """
        return []

    @staticmethod
    def core_packages():
        # type: () -> List[str]
        """
        Return a list of core packages.

        List of packages that are core of the product. Most importantly,
        if they themselves define add-on/plugin entry points they must
        not be 'uninstalled' via a package manager, they can only be
        updated.

        Return
        ------
        packages : List[str]
            A list of package names (can also contain PEP-440 version
            specifiers).
        """
        return ["orange-canvas-core >= 0.0, < 0.1a"]

    @staticmethod
    def examples_entry_points():
        return iter(entry_points(group=EXAMPLE_WORKFLOWS_ENTRY))

    @staticmethod
    def widget_discovery(*args, **kwargs):
        from orangecanvas import registry
        return registry.WidgetDiscovery(*args, **kwargs)

    @staticmethod
    def workflow_constructor(*args, **kwargs):
        from orangecanvas import scheme
        return scheme.Scheme(*args, **kwargs)

orangeconfig.default = Default()