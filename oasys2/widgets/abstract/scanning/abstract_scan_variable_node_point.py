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

from AnyQt.QtGui import QFont, QPalette, QColor
from orangewidget.settings import Setting

from oasys2.widget import gui
from oasys2.widgets.abstract.scanning.abstract_scan_node_point import AbstractScanLoopPoint

class AbstractScanVariableLoopPoint(AbstractScanLoopPoint):

    variable_value_from = Setting(0.0)
    variable_value_to = Setting(0.0)
    variable_value_step = Setting(0.0)

    list_of_values = Setting([""])
    kind_of_loop = Setting(0)

    def create_specific_loop_box(self, box):
        gui.separator(box)

        gui.comboBox(box, self, "kind_of_loop", label="Kind of Loop", labelWidth=350,
                     items=["From Range", "From List"],
                     callback=self.set_KindOfLoop, sendSelectedValue=False, orientation="horizontal")

        self.box_1 = gui.widgetBox(box, "", addSpace=False, orientation="vertical", width=360, height=160)
        self.box_2 = gui.widgetBox(box, "", addSpace=False, orientation="vertical", width=360, height=160)

        gui.lineEdit(self.box_1, self, "variable_value_from", "Value From", labelWidth=250, valueType=float, orientation="horizontal", callback=self.calculate_step)
        gui.lineEdit(self.box_1, self, "variable_value_to", "Value to", labelWidth=250, valueType=float, orientation="horizontal", callback=self.calculate_step)
        gui.lineEdit(self.box_1, self, "number_of_new_objects", "Number of Steps", labelWidth=250, valueType=int, orientation="horizontal", callback=self.calculate_step)

        self.list_of_values_ta = gui.textArea(height=150, width=360, readOnly=False)
        self.list_of_values_ta.textChanged.connect(self.list_of_values_ta_changed)

        text = ""
        for value in self.list_of_values:
            text += value + "\n"

        self.list_of_values_ta.setText(text[:-1])
        self.box_2.layout().addWidget(self.list_of_values_ta)

        self.le_variable_value_step = gui.lineEdit(self.box_1, self, "variable_value_step", "Step Value", labelWidth=250, valueType=float, orientation="horizontal")
        self.le_variable_value_step.setReadOnly(True)
        font = QFont(self.le_variable_value_step.font())
        font.setBold(True)
        self.le_variable_value_step.setFont(font)
        palette = QPalette(self.le_variable_value_step.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_variable_value_step.setPalette(palette)

        self.set_KindOfLoop()
        self.calculate_step()

        gui.separator(box)

    def list_of_values_ta_changed(self):
        self.list_of_values = []

        values = self.list_of_values_ta.toPlainText().split("\n")
        for value in values:
            if not value.strip() == "": self.list_of_values.append(value)

        if self.kind_of_loop==1: self.number_of_new_objects = len(self.list_of_values)

        if len(self.list_of_values) == 0: self.list_of_values.append("")

    def set_KindOfLoop(self):
        self.box_1.setVisible(self.kind_of_loop == 0)
        self.box_2.setVisible(self.kind_of_loop == 1)

    def calculate_step(self):
        try:    self.variable_value_step = round((self.variable_value_to - self.variable_value_from) / self.number_of_new_objects, 8)
        except: self.variable_value_step = 0.0

    def get_current_value_type(self): return float

    def initialize_start_loop(self):
        do_loop = True

        if self.kind_of_loop == 0:
            self.current_variable_value = round(self.variable_value_from, 8)
            self.calculate_step()
        elif len(self.list_of_values) > 0:
            self.current_variable_value = self.list_of_values[self.current_new_object - 1]
        else:
            do_loop = False

        return do_loop

    def keep_looping(self):
        if (self.current_new_object < self.number_of_new_objects) or (self.current_new_object == self.number_of_new_objects and self.kind_of_loop==0):
            if self.is_current_variable_value_empty():
                self.current_new_object = 1

                if self.kind_of_loop == 0:
                    self.current_variable_value = round(self.variable_value_from, 8)
                    self.calculate_step()
                elif len(self.list_of_values) > 0:
                    self.current_variable_value = self.list_of_values[self.current_new_object - 1]
            else:
                self.current_new_object += 1
                if self.kind_of_loop == 0:
                    self.current_variable_value = round(self.current_variable_value + self.variable_value_step, 8)
                elif len(self.list_of_values) > 0:
                    self.current_variable_value = self.list_of_values[self.current_new_object - 1]
            return True
        else:
            return False
