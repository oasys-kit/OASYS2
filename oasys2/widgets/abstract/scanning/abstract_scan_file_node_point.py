#!/usr/bin/env python
# -*- coding: utf-8 -*-
# #########################################################################
# Copyright (c) 2020, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2020. UChicago Argonne, LLC. This software was produced       #
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
# #########################################################################

from AnyQt.QtWidgets import QFileDialog

from orangewidget.settings import Setting
from orangewidget.widget import Input

from oasys2.widget import gui
from oasys2.widgets.abstract.scanning.abstract_scan_node_point import AbstractScanLoopPoint

class AbstractScanFileLoopPoint(AbstractScanLoopPoint):
    class Inputs:
        trigger_in = AbstractScanLoopPoint.Inputs.trigger_in
        files      = Input("Files", list, id="Files", default=True, auto_summary=False)

    files_area = None
    variable_files = Setting([""])

    def create_specific_loop_box(self, box):
        box_files = gui.widgetBox(box, "", addSpace=False, orientation="vertical", height=270)

        gui.button(box_files, self, "Select Height Error Profile Data Files", callback=self.select_files)

        self.files_area = gui.textArea(height=200, width=360)

        self.refresh_files_text_area()

        box_files.layout().addWidget(self.files_area)

        gui.separator(box)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "Select Height Error Profiles", "", "Data Files (*.dat)")
        if files:
            self.variable_files = files

            self.refresh_files_text_area()

    @Inputs.files
    def setFiles(self, files_data):
        if not files_data is None:
            if isinstance(files_data, str):
                self.variable_files.append(files_data)
            elif isinstance(files_data, list):
                self.variable_files = files_data
            else:
                raise ValueError("Error Profile Data File: format not recognized")

            self.refresh_files_text_area()

    def refresh_files_text_area(self):
        text = ""
        for file in self.variable_files:
            text += file + "\n"
        self.files_area.setText(text)

        self.number_of_new_objects = len(self.variable_files)

    def has_variable_um(self): return False

    def get_current_value_type(self): return str

    def initialize_start_loop(self):
        self.current_variable_value = self.variable_files[0]
        self.number_of_new_objects = len(self.variable_files)

        self.start_button.setEnabled(False)

        return True

    def keep_looping(self):
        if self.current_new_object < self.number_of_new_objects:
            if self.is_current_variable_value_empty(): self.current_new_object = 1
            else:                                      self.current_new_object += 1

            self.current_variable_value = self.variable_files[self.current_new_object - 1]

            return True
        else:
            return False



