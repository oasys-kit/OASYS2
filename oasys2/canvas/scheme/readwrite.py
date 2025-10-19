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

from orangecanvas.scheme.readwrite import (
    parse_ows_stream, global_registry, resolve_replaced,
    UnknownWidgetDefinition, SchemeNode, loads, log,
    _find_source_channel, _find_sink_channel, SchemeLink, IncompatibleChannelTypeError,
    SchemeTextAnnotation, SchemeArrowAnnotation, Scheme
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

    def oasys2_name(self, oasys1_name):
        return self.supported_widgtes.get(oasys1_name, None)

oasys1_to_oasys2 = Oasys1ToOasys2()

class UnsupportedWidgetDefinition(Exception):
    pass

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
                o1_to_o2_name  = oasys1_to_oasys2.oasys2_name(node_d.qualified_name)
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
                        properties = loads(data.data, data.format)
                    except Exception:
                        log.error("Could not load properties for %r.", node.title,
                                  exc_info=True)
                    else:
                        node.properties = properties

                nodes.append(node)
                nodes_by_id[node_d.id] = node

    scheme.is_older_oasys = is_older_oasys

    for link_d in desc.links:
        source_id = link_d.source_node_id
        sink_id = link_d.sink_node_id

        if source_id in nodes_not_found or sink_id in nodes_not_found:
            continue

        source = nodes_by_id[source_id]
        sink = nodes_by_id[sink_id]
        try:
            source_channel = _find_source_channel(source, link_d)
            sink_channel = _find_sink_channel(sink, link_d)
            link = SchemeLink(source, source_channel,
                              sink, sink_channel,
                              enabled=link_d.enabled)
        except (ValueError, IncompatibleChannelTypeError) as ex:
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