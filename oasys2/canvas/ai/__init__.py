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

"""
orangecontrib.oasys_ai_fab
==========================
Startup hook for the OASYS AI Beamline Architect Floating Action Button.

This __init__.py is imported automatically by Orange/OASYS when the add-on
is discovered (via the orange.addons entry point). It schedules FAB injection
after the Qt event loop is running, retrying until CanvasMainWindow appears.

No widgets are registered — the FAB injects itself directly into the
CanvasMainWindow as an overlay child widget.
"""

from AnyQt.QtCore import QTimer
from AnyQt.QtWidgets import QApplication

from oasys2.canvas.application.canvasmain import OASYSMainWindow

from .fab import FABInstaller

def _try_install(attempts: int = 0) -> None:
    """
    Find CanvasMainWindow and inject the FAB.
    Retries up to 20 times (20 s total) in case OASYS hasn't finished
    initialising the main window yet.
    """
    app: QApplication = QApplication.instance()
    if app is None: return

    for widget in app.topLevelWidgets():
        if isinstance(widget, OASYSMainWindow) and widget.isVisible():
            try:
                FABInstaller.install(widget)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error(
                    "OASYS AI FAB: install failed: %s", exc, exc_info=True
                )
            return

    if attempts < 20:
        QTimer.singleShot(1000, lambda: _try_install(attempts + 1))

# Kick off after the event loop has had a chance to start
QTimer.singleShot(1500, lambda: _try_install(0))
