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
import json
import math
import pprint
import numbers
import base64
import numpy
import io
import pickle
import importlib

from orangecanvas.scheme.readwrite import (
    parse_ows_stream, global_registry, resolve_replaced, literal_eval,
    UnknownWidgetDefinition, SchemeNode, log, chain, SchemeLink, IncompatibleChannelTypeError,
    SchemeTextAnnotation, SchemeArrowAnnotation, Scheme, _link, InputSignal, OutputSignal, Optional, findf
)

from orangecanvas.resources import package_dirname

class Oasys1ToOasys2:
    def __init__(self):
        try:
            with open(os.path.join(package_dirname("oasys2.canvas.scheme"),
                                   "data",
                                   "oasys1-to-oasys2.json"), 'r') as file:
                self.__registry = json.load(file)
        except:
            print("oasys1-to-oasys2 registry not found, using default")
            self.__registry = {}

    @property
    def unsupported_widgtes(self) -> list:
        return self.__registry.get("unsupported_widgets", [])

    @property
    def supported_widgtes(self) -> dict:
        return self.__registry.get("supported_widgets", {})

    @property
    def supported_source_links(self) -> dict:
        return self.__registry.get("supported_source_links", {})

    @property
    def supported_sink_links(self) -> dict:
        return self.__registry.get("supported_sink_links", {})

    def oasys2_widget_name(self, oasys1_name):
        return self.supported_widgtes.get(oasys1_name, None)

    def oasys2_source_link_name(self, oasys1_name):
        return self.supported_source_links.get(oasys1_name, None)

    def oasys2_sink_link_name(self, oasys1_name):
        return self.supported_sink_links.get(oasys1_name, None)

oasys1_to_oasys2 = Oasys1ToOasys2()

class UnsupportedWidgetDefinition(Exception):
    pass

class Oasys1ToOasys2Unpickler(pickle.Unpickler):
    def __init__(self, file, replacements=None, default_factory=None):
        super().__init__(file)
        self.replacements = dict(replacements or {})
        self.default_factory = (lambda module, name: type(name, (object,), {"__module__": module}))

    def find_class(self, module, name):
        key = (module, name)

        if key in self.replacements: found_class = self.replacements[key]
        else:
            try:              found_class = super().find_class(module, name)
            except Exception: found_class = self.default_factory(module, name)

        return found_class

def _o1_to_o2_loads(data: bytes):
    replacements = {
        ("oasys.widgets.tools.ow_python_script", "Script") : getattr(importlib.import_module("oasys2.widgets.tools.ow_python_script"), "Script"),
        ("sip", "_unpickle_type"): _o1_sip_unpickle,
    }
    return Oasys1ToOasys2Unpickler(io.BytesIO(data), replacements=replacements).load()

def _o1_sip_unpickle(*args, **kwargs):
    if len(args) >= 2 and all(isinstance(a, str) for a in args[:2]): mod_name, type_name = args[:2]
    else:                                                            mod_name, type_name = "unknown", "Unknown"

    if mod_name == 'PyQt5.QtCore' and type_name == 'QByteArray': return args[2][0]
    else:                                                        return type(type_name, (object,), {"__module__": mod_name})

def _loads(string, format):
    if format == "literal":  return literal_eval(string)
    elif format == "json":   return json.loads(string)
    elif format == "pickle":
        try:                        return pickle.loads(base64.decodebytes(string.encode('ascii')))
        except ModuleNotFoundError: return _o1_to_o2_loads(base64.decodebytes(string.encode('ascii')))
    else: raise ValueError("Unknown format")

def _literal_dumps(obj, indent=None, relaxed_types=True):
    memo = {}

    builtins         = {int, float, bool, type(None), str, bytes}
    builtins_numpy_real = {numpy.float32, numpy.float64}
    builtins_numpy_int  = {numpy.int8, numpy.int16, numpy.int32, numpy.int64,
                           numpy.uint8, numpy.uint16, numpy.uint32, numpy.uint64}
    builtins_seq     = {list, tuple}
    builtins_mapping = {dict}

    def convert_numpy_obj(obj):
        if type(obj) in builtins_mapping:
            return { key : float(value) if type(value) in builtins_numpy_real else (int(value) if type(value) in builtins_numpy_int else value) for key, value in obj.items() }
        else:
            return obj

    def check(obj):
        if type(obj) == float and not math.isfinite(obj):
            raise TypeError("Non-finite values can not be serialized as a python literal")

        if type(obj) in builtins:       return True
        if id(obj) in memo: raise ValueError("{0} is a recursive structure".format(obj))

        memo[id(obj)] = obj

        if type(obj) in builtins_seq:       return all(map(check, obj))
        elif type(obj) in builtins_mapping: return all(map(check, chain(obj.keys(), obj.values())))
        else:
            raise TypeError("{0} can not be serialized as a python literal".format(type(obj)))

    def check_relaxed(obj):
        if isinstance(obj, numbers.Real) and not math.isfinite(obj):
            raise TypeError("Non-finite values can not be serialized as a python literal")

        if type(obj) in builtins: return True
        if id(obj) in memo: raise ValueError("{0} is a recursive structure".format(obj))

        memo[id(obj)] = obj

        if type(obj) in builtins_seq:        return all(map(check_relaxed, obj))
        elif type(obj) in builtins_mapping:  return all(map(check_relaxed, chain(obj.keys(), obj.values())))
        elif isinstance(obj, numbers.Integral):
            if repr(obj) == repr(int(obj)): return True
        elif isinstance(obj, numbers.Real):
            if repr(obj) == repr(float(obj)): return True

        raise TypeError("{0} can not be serialized as a python literal".format(type(obj)))

    obj = convert_numpy_obj(obj)

    if relaxed_types: check_relaxed(obj)
    else:             check(obj)

    if indent is not None: return pprint.pformat(obj, width=80 * 2, indent=indent, compact=True)
    else:                  return repr(obj)

import orangecanvas.scheme.readwrite as orange_readwrite

orange_readwrite.literal_dumps = _literal_dumps


def _find_source_channel_o1_to_o2(node: SchemeNode, link: _link) -> OutputSignal:
    source_channel: Optional[OutputSignal] = None
    if link.source_channel_id:
        source_channel = findf(
            node.output_channels(),
            lambda c: c.id == link.source_channel_id,
        )
    if source_channel is not None:
        return source_channel

    if link.source_channel in oasys1_to_oasys2.supported_source_links:
        source_channel_name = oasys1_to_oasys2.oasys2_source_link_name(link.source_channel)
    else:
        source_channel_name = link.source_channel

    source_channel = findf(
        node.output_channels(),
        lambda c: c.name == source_channel_name,
    )
    if source_channel is not None:
        return source_channel



    raise ValueError(
        f"{link.source_channel!r} is not a valid output channel "
        f"for {node.description.name!r}."
    )


def _find_sink_channel_o1_to_o2(node: SchemeNode, link: _link) -> InputSignal:
    sink_channel: Optional[InputSignal] = None
    if link.sink_channel_id:
        sink_channel = findf(
            node.input_channels(),
            lambda c: c.id == link.sink_channel_id,
        )

    if sink_channel is not None:
        return sink_channel

    if link.sink_channel in oasys1_to_oasys2.supported_sink_links:
        sink_channel_name = oasys1_to_oasys2.oasys2_sink_link_name(link.sink_channel)
    else:
        sink_channel_name = link.sink_channel

    sink_channel = findf(
        node.input_channels(),
        lambda c: c.name == sink_channel_name,
    )
    if sink_channel is not None:
        return sink_channel

    raise ValueError(
        f"{link.sink_channel!r} is not a valid input channel "
        f"for {node.description.name!r}."
    )



def scheme_load(scheme, stream, registry=None, error_handler=None):
    desc = parse_ows_stream(stream)  # type: _scheme

    if registry is None:
        registry = global_registry()

    if error_handler is None:
        def error_handler(exc):
            raise exc

    desc = resolve_replaced(desc, registry)
    nodes_not_found = []
    nodes = []
    nodes_by_id = {}
    links = []
    annotations = []

    scheme.title = desc.title
    scheme.description = desc.description

    is_older_oasys = False
    for node_d in desc.nodes:
        original_name = node_d.qualified_name

        if original_name in oasys1_to_oasys2.unsupported_widgtes:
            error_handler(UnsupportedWidgetDefinition(f"{original_name} is no more supported in Oasys2"))
            nodes_not_found.append(node_d.id)
            is_older_oasys = True
        else:
            try:
                o1_to_o2_name  = oasys1_to_oasys2.oasys2_widget_name(node_d.qualified_name)
                is_older_oasys = True if is_older_oasys else (o1_to_o2_name is not None)
                widget_name    = node_d.qualified_name if o1_to_o2_name is None else o1_to_o2_name
                w_desc         = registry.widget(widget_name)
            except KeyError as ex:
                error_handler(UnknownWidgetDefinition(*ex.args))
                nodes_not_found.append(node_d.id)
            else:
                node = SchemeNode(w_desc, title=node_d.title, position=node_d.position)
                data = node_d.data

                if data:
                    try:
                        properties = _loads(data.data, data.format)
                    except Exception:
                        log.error("Could not load properties for %r.", node.title, exc_info=True)
                    else:
                        node.properties = properties

                nodes.append(node)
                nodes_by_id[node_d.id] = node

    scheme.is_older_oasys = is_older_oasys

    for link_d in desc.links:
        source_id = link_d.source_node_id
        sink_id   = link_d.sink_node_id

        if source_id in nodes_not_found or sink_id in nodes_not_found:
            continue

        source = nodes_by_id[source_id]
        sink   = nodes_by_id[sink_id]
        try:
            source_channel = _find_source_channel_o1_to_o2(source, link_d)
            sink_channel   = _find_sink_channel_o1_to_o2(sink, link_d)

            link = SchemeLink(source, source_channel,
                              sink, sink_channel,
                              enabled=link_d.enabled)
        except (ValueError, IncompatibleChannelTypeError) as ex:
            if isinstance(ex, ValueError): print(str(ex))

            error_handler(ex)
        else:
            links.append(link)

    for annot_d in desc.annotations:
        params = annot_d.params
        if annot_d.type == "text":
            annot = SchemeTextAnnotation(
                params.geometry, params.text, params.content_type,
                params.font
            )
        elif annot_d.type == "arrow":
            start, end = params.geometry
            annot = SchemeArrowAnnotation(start, end, params.color)

        else:
            log.warning("Ignoring unknown annotation type: %r", annot_d.type)
            continue
        annotations.append(annot)

    for node in nodes:
        scheme.add_node(node)

    for link in links:
        scheme.add_link(link)

    for annot in annotations:
        scheme.add_annotation(annot)

    if desc.session_state.groups:
        groups = []
        for g in desc.session_state.groups:  # type: _window_group
            # resolve node_id -> node
            state = [(nodes_by_id[node_id], data)
                     for node_id, data in g.state if node_id in nodes_by_id]

            groups.append(Scheme.WindowGroup(g.name, g.default, state))
        scheme.set_window_group_presets(groups)

    return scheme