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

class OasysSurfaceData(object):
    def __init__(self,
                 xx=None,
                 yy=None,
                 zz=None,
                 surface_data_file=None):
        self.xx = xx
        self.yy = yy
        self.zz = zz
        self.surface_data_file=surface_data_file

class OasysErrorProfileData(object):

    def __init__(self,
                 surface_data=None,
                 error_profile_x_dim=0.0,
                 error_profile_y_dim=0.0):
        self.surface_data = surface_data
        self.error_profile_x_dim = error_profile_x_dim
        self.error_profile_y_dim = error_profile_y_dim

class OasysPreProcessorData(object):

    def __init__(self, error_profile_data=None, reflectivity_data=None):
        super().__init__()

        self.error_profile_data = error_profile_data
        self.reflectivity_data = reflectivity_data
        self.additional_data = None

    def set_additional_data(self, key, value):
        if self._additional_data is None:
            self._additional_data = {key : value}
        else:
            self._additional_data[key] = value

    def get_additional_data(self, key):
        return self._additional_data[key]

    def has_additional_data(self, key):
        return key in self._additional_data

class OasysThicknessErrorsData(object):
    def __init__(self, thickness_error_profile_data_files=[]):
        self.thickness_error_profile_data_files = thickness_error_profile_data_files

class TriggerOut:
    def __init__(self, new_object=False, additional_parameters={}):
        super().__init__()

        self.new_object = new_object

        self.__additional_parameters=additional_parameters

    def has_additional_parameter(self, name):
        return name in self.__additional_parameters.keys()

    def get_additional_parameter(self, name):
        return self.__additional_parameters[name]

class TriggerIn:
    def __init__(self, new_object=False, interrupt=False, additional_parameters={}):
        super().__init__()

        self.new_object = new_object
        self.interrupt = interrupt

        self.__additional_parameters=additional_parameters

    def has_additional_parameter(self, name):
        return name in self.__additional_parameters.keys()

    def get_additional_parameter(self, name):
        return self.__additional_parameters[name]
