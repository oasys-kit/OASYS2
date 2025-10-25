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

########### DO NOT REMOVE! -> RETROCOMPATIBILITY
# Allows from oasys2.widget.util.widget_util import get_fwhm.
#
#
########### DO NOT REMOVE! -> RETROCOMPATIBILITY

import os, numpy, threading
import h5py, time

from AnyQt.QtWidgets import QWidget
from AnyQt.QtGui import QPainter, QPalette, QBrush, QPen, QColor
from AnyQt.QtCore import Qt, QObject, pyqtSignal

subgroup_name = "surface_file"

def read_surface_file(file_name):
    if not os.path.isfile(file_name): raise ValueError("File " + file_name + " not existing")

    file = h5py.File(file_name, 'r')
    xx = file[subgroup_name + "/X"][()]
    yy = file[subgroup_name + "/Y"][()]
    zz = file[subgroup_name + "/Z"][()]

    return xx, yy, zz

def write_surface_file(zz, xx, yy, file_name, overwrite=True):

    if (os.path.isfile(file_name)) and (overwrite==True): os.remove(file_name)

    if not os.path.isfile(file_name):  # if file doesn't exist, create it.
        file = h5py.File(file_name, 'w')
        # points to the default data to be plotted
        file.attrs['default']          = subgroup_name
        # give the HDF5 root some more attributes
        file.attrs['file_name']        = file_name
        file.attrs['file_time']        = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        file.attrs['creator']          = 'write_surface_file'
        file.attrs['code']             = 'Oasys'
        file.attrs['HDF5_Version']     = h5py.version.hdf5_version
        file.attrs['h5py_version']     = h5py.version.version
        file.close()

    file = h5py.File(file_name, 'a')

    try:
        f1 = file.create_group(subgroup_name)
    except:
        f1 = file[subgroup_name]

    f1z = f1.create_dataset("Z", data=zz)
    f1x = f1.create_dataset("X", data=xx)
    f1y = f1.create_dataset("Y", data=yy)


    # NEXUS attributes for automatic plot
    f1.attrs['NX_class'] = 'NXdata'
    f1.attrs['signal'] = "Z"
    f1.attrs['axes'] = [b"Y", b"X"]

    f1z.attrs['interpretation'] = 'image'
    f1x.attrs['long_name'] = "X [m]"
    f1y.attrs['long_name'] = "Y [m]"


    file.close()

try:
    class TTYGrabber:
        def __init__(self, tmpFileName='out.tmp.dat'):
            self.tmpFileName = tmpFileName
            self.ttyData = []
            self.outfile = False
            self.save = False

        def start(self):
            self.outfile = os.open(self.tmpFileName, os.O_RDWR | os.O_CREAT)
            self.save = os.dup(1)
            os.dup2(self.outfile, 1)
            return

        def stop(self):
            if not self.save:
                return
            os.dup2(self.save, 1)
            tmpFile = open(self.tmpFileName, "r")
            self.ttyData = tmpFile.readlines()
            tmpFile.close()
            os.close(self.outfile)
            os.remove(self.tmpFileName)
except:
    pass

try:
    class EmittingStream(QObject):
        textWritten = pyqtSignal(str)

        def write(self, text):
            self.textWritten.emit(str(text))

        def flush(self):
            pass
except:
    pass

try:
    class Overlay(QWidget):

        def __init__(self, container_widget=None, target_method=None, wait=0.001):

            QWidget.__init__(self, container_widget)
            self.container_widget = container_widget
            self.target_method = target_method
            palette = QPalette(self.palette())
            palette.setColor(palette.Background, Qt.transparent)
            self.setPalette(palette)
            self.__wait = wait

        def paintEvent(self, event):
            painter = QPainter()
            painter.begin(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))
            painter.setPen(QPen(Qt.NoPen))

            for i in range(1, 7):
                if self.position_index == i:
                    painter.setBrush(QBrush(QColor(255, 165, 0)))
                else:
                    painter.setBrush(QBrush(QColor(127, 127, 127)))
                painter.drawEllipse(
                    int(self.width()/2 + 30 * numpy.cos(2 * numpy.pi * i / 6.0) - 10),
                    int(self.height()/2 + 30 * numpy.sin(2 * numpy.pi * i / 6.0) - 10),
                    20, 20)

                time.sleep(self.__wait)

            painter.end()

        def showEvent(self, event):
            self.timer = self.startTimer(0)
            self.counter = 0
            self.position_index = 0
            if not self.target_method is None:
                t = threading.Thread(target=self.target_method)
                t.start()

        def hideEvent(self, QHideEvent):
            self.killTimer(self.timer)

        def timerEvent(self, event):
            self.counter += 1
            self.position_index += 1
            if self.position_index == 7: self.position_index = 1
            self.update()
except:
    pass



