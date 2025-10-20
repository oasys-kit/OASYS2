"""
OASYS Widgets Scheme
====================

A Scheme for OASYS Orange Widgets Scheme.

.. autoclass:: OASYSWidgetsScheme
   :bases:

.. autoclass:: OASYSWidgetsSignalManager
   :bases:

"""
import os
import sys
import logging

try: import AnyQt.sip as sip
except Exception as e: print(e)

from AnyQt.QtCore import QSettings
from AnyQt.QtCore import pyqtSignal as Signal, pyqtProperty as Property

from orangecanvas.scheme import Scheme, readwrite

from orangewidget.workflow.widgetsscheme import WidgetsScheme, WidgetsSignalManager, WidgetManager

from oasys2.widget.widget import OWAction

log = logging.getLogger(__name__)

def check_working_directory(working_directory):
    if sys.platform == "win32": return working_directory.replace("/", "\\")  # weird bug since 12/2023
    else:                       return working_directory.replace("\\", "/")

class OASYSWidgetsScheme(WidgetsScheme):
    #: Signal emitted when the working directory changes.
    working_directory_changed = Signal(str)

    def __init__(self, parent=None, title=None, description=None, working_directory=None):
        self.__canvas_main_window = parent

        settings = QSettings()

        self.__working_directory = (working_directory or settings.value("output/default-working-directory", os.path.expanduser("~/Oasys2"), type=str))
        self.__working_directory = check_working_directory(self.__working_directory)
        if not os.path.exists(self.__working_directory): os.makedirs(self.__working_directory, exist_ok=True)

        super().__init__(parent, title=title, description=description)

        # Replace the signal manager from.
        self.signal_manager.setParent(None)
        self.signal_manager.deleteLater()
        sip.delete(self.signal_manager)
        sip.delete(self.widget_manager)

        self.set_loop_flags(Scheme.AllowLoops)
        self.signal_manager = OASYSSignalManager(self)
        self.widget_manager = OASYSWidgetManager()
        self.widget_manager.set_scheme(self)

        self.__is_older_oasys = False

    def set_working_directory(self, working_directory):
        """
        Set the scheme working_directory.
        """
        working_directory = check_working_directory(working_directory)

        if self.__working_directory != working_directory:
            self.__working_directory = working_directory
            self.working_directory_changed.emit(working_directory)

    def working_directory(self):
        """
        The working_directory of the scheme.
        """
        return self.__working_directory

    @property
    def is_older_oasys(self):
        return self.__is_older_oasys

    @is_older_oasys.setter
    def is_older_oasys(self, is_older_oasys):
        self.__is_older_oasys = is_older_oasys



    def canvas_main_window(self):
        return self.__canvas_main_window

    working_directory = Property(str,
                                 fget=working_directory,
                                 fset=set_working_directory)

    canvas_main_window = Property(object,
                                  fget=canvas_main_window)


    def save_to(self, stream, pretty=True, pickle_fallback=False):
        """
        Reimplemented from Scheme.save_to.
        """
        if isinstance(stream, str):
            stream = open(stream, "wb")

        self.sync_node_properties()

        tree = readwrite.scheme_to_etree(self, pickle_fallback=pickle_fallback)
        root = tree.getroot()
        root.set("working_directory", self.working_directory or "")

        if pretty: readwrite.indent(tree.getroot(), 0)

        tree.write(stream, encoding="utf-8", xml_declaration=True)


class OASYSWidgetManager(WidgetManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def actions_for_context_menu(self, node):
        if not node.property("ext-menu-actions") is None:
            return [action for action in node.property("ext-menu-actions")]
        else:
            widget = self.widget_for_node(node)
            owactions = [action for action in widget.actions() if isinstance(action, OWAction)]
            node.setProperty("ext-menu-actions", owactions)

            return owactions

    def delete_widget_for_node(self, node, widget):
        if not node.property("ext-menu-actions") is None: node.setProperty("ext-menu-actions", None)

        super(OASYSWidgetManager, self).delete_widget_for_node(node, widget)

    def set_scheme(self, scheme):
        super().set_scheme(scheme)
        scheme.working_directory_changed.connect(self.__working_directory_changed)

    def create_widget_instance(self, node):
        """
        Reimplemented from WidgetManager.create_widget_instance
        """
        widget = super().create_widget_instance(node)

        if hasattr(widget, "setWorkingDirectory"): widget.setWorkingDirectory(self.scheme().working_directory)
        if hasattr(widget, "setCanvasMainWindow"): widget.setCanvasMainWindow(self.scheme().canvas_main_window)
        if hasattr(widget, "createdFromNode"):     widget.createdFromNode(node)

        return widget

    def __working_directory_changed(self, workdir):
        for node in self.scheme().nodes:
            w = self.widget_for_node(node)
            if hasattr(w, "setWorkingDirectory"): w.setWorkingDirectory(workdir)

from functools import partial, reduce
from orangecanvas.scheme.signalmanager import strongly_connected_components, dependent_nodes

class OASYSSignalManager(WidgetsSignalManager):

    def __init__(self, scheme, **kwargs):
        super().__init__(scheme, **kwargs)

    def pending_nodes(self):
        """
        *** Restored from OASYS1, allows to indentify the loop points

        Reimplemented from SignalManager.pending_nodes.

        Enforce some custom ordering semantics in workflow cycles.
        """

        pending = super().pending_nodes()
        pending_new = [node for node in pending if not getattr(self.scheme().widget_for_node(node), "process_last", False)]
        if pending_new: pending = pending_new

        return pending

    def node_update_front(self):
        """
        *** Restored from OASYS1, the original method prevents the loops to work

        Return a list of nodes on the update front, i.e. nodes scheduled for
        an update that have no ancestor which is either itself scheduled
        for update or is in a blocking state)

        .. note::
            The node's ancestors are only computed over enabled links.

        """
        scheme = self.scheme()

        def expand(node):
            return [link.sink_node for
                link in scheme.find_links(source_node=node) if
                link.enabled]

        components = strongly_connected_components(scheme.nodes, expand)
        node_scc = {node: scc for scc in components for node in scc}

        def isincycle(node):
            return len(node_scc[node]) > 1

        # a list of all nodes currently active/executing a task.
        blocking_nodes = set(self.blocking_nodes())

        dependents = partial(dependent_nodes, scheme)

        blocked_nodes = reduce(set.union,
                               map(dependents, blocking_nodes),
                               set(blocking_nodes))
        pending = set(self.pending_nodes())

        pending_downstream = set()
        for n in pending:
            depend = set(dependents(n))
            if isincycle(n):
                # a pending node in a cycle would would have a circular
                # dependency on itself, preventing any progress being made
                # by the workflow execution.
                cc = node_scc[n]
                depend -= set(cc)
            pending_downstream.update(depend)

        log.debug("Pending nodes: %s", pending)
        log.debug("Blocking nodes: %s", blocking_nodes)

        return list(pending - pending_downstream - blocked_nodes)
