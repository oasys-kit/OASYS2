import os

from AnyQt.QtWidgets import QScrollArea, QAction
from AnyQt.QtCore import Qt
from AnyQt.QtGui import QIcon
from PyQt6.QtWidgets import QDialog

from orangewidget.widget import OWBaseWidget

def layout_insert(layout, widget, before):
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is before:
            break
    else:
        raise ValueError("{} is not in layout".format(widget))
    layout.insertWidget(i, widget, )

class OWWidget(OWBaseWidget, openclass=True):

    IS_DEVELOP = False if not "OASYSDEVELOP" in os.environ.keys() else str(os.environ.get('OASYSDEVELOP')) == "1"

    _node = None
    _node_item = None

    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint)

    # ---------------------------------------------------------
    # Runtime management of the Node (Icons, etc..) - from OASYS1
    # ---------------------------------------------------------

    def get_scheme(self):
        return self.canvas_main_window.current_document().scheme()

    def get_scene(self):
        return self.canvas_main_window.current_document().scene()

    def widgetNodeAdded(self, node_item):
        if self._node_item is None: self._node_item = node_item

    def createdFromNode(self, node):
        if self._node is None: self._node = node

    def getNode(self):
        if self._node is None: self._node = self.get_scheme().node_for_widget(self)
        return self._node

    def getNodeItem(self):
        if self._node_item is None: self._node_item = self.get_scene().item_for_node(self.getNode())
        return self._node_item

    def getNodeLinks(self):
        return self.get_scene().node_links(self.getNodeItem())

    def changeNodeIcon(self, icon):
       node_item = self.getNodeItem()
       if not node_item is None:
           node_item.icon_item.hide()
           if isinstance(icon, QIcon): node_item.setIcon(icon)
           else:                       node_item.setIcon(QIcon(icon))
           node_item.update()

    def changeNodeTitle(self, title):
        node_item = self.getNodeItem()
        if not node_item is None:
            node_item.setTitle(title)
            node_item.update()

    # ---------------------------------------------------------
    # ---------------------------------------------------------
    # ---------------------------------------------------------

    def insertLayout(self):
        """
        Reimplemented from OWWidget.insertLayout.

        Pull the OWWidget created controlArea and mainArea widgets into
        QScrollArea's.

        """
        super().insertLayout()

        self.setStyleSheet("background-color: #EBEBEB;")

        cls = type(self)

        if cls.want_basic_layout and cls.want_control_area:
            layout = self.leftWidgetPart.layout()
            area = QScrollArea()
            layout_insert(layout, area, before=self.controlArea)
            layout.takeAt(layout.indexOf(self.controlArea))
            area.setWidget(self.controlArea)
            area.setWidgetResizable(True)

        if cls.want_basic_layout and cls.want_main_area:
            layout = self.topWidgetPart.layout()
            area = QScrollArea()
            layout_insert(layout, area, before=self.mainArea)
            layout.takeAt(layout.indexOf(self.mainArea))
            area.setWidget(self.mainArea)
            area.setWidgetResizable(True)

    def setCanvasMainWindow(self, canvas_main_window):
        self.canvas_main_window = canvas_main_window

    def setWorkingDirectory(self, directory):
        self.working_directory = directory

        self.after_change_working_directory()

    def after_change_working_directory(self):
        pass

    def __setattr__(self, name, value):
        super().__setattr__(name, value)

        for shower in getattr(self, "showers", []):
            if name in shower.expression:
                shower()

    def show_at(self, expression, what):
        class ShowerClass:
            def __init__(shower):
                shower.what = what
                shower.expression = expression

            def __call__(shower):
                x = self # to force self into the closure, because we need it in the expression
                to_show = eval(expression)
                if shower.what.isHidden() == to_show:
                    if to_show:
                        shower.what.show()
                    else:
                        shower.what.hide()

        shower = ShowerClass()
        if not hasattr(self, "showers"):
            self.showers = []
        self.showers.append(shower)

    def process_showers(self):
        for shower in getattr(self, "showers", []):
            shower()

from typing import Final

class OWDialog(QDialog):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent, **kwargs)

    def connect_control(self, name, func): # prevents error when used in combination with orangewidget.gui methods
        pass

class OWLoopWidget(OWWidget, openclass=True):
    #################################
    process_last: Final[bool] = True
    #################################

    def __init__(self):
        super().__init__()

class OWAction(QAction):
    """
    An action to be inserted into canvas right click context menu.

    Actions defined and added this way are pulled from the widget and
    inserted into canvas GUI's right context menu. The actions must
    be defined in the OWWidget's `__init__` method and added to the
    widget with `QWidget.addAction`.

    """
    pass

from orangewidget import gui
from orangewidget.settings import Setting

from AnyQt.QtWidgets import QApplication
from AnyQt.QtCore import QRect

class OWAutomaticWidget(OWWidget, openclass=True):

    is_automatic_execution = Setting(True)

    CONTROL_AREA_WIDTH = 405

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    def __init__(self, is_automatic=True):
        super().__init__()

        geom = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(round(geom.width()*0.05),
                               round(geom.height()*0.05),
                               round(min(geom.width()*0.98, self.MAX_WIDTH)),
                               round(min(geom.height()*0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        if is_automatic:
            self.general_options_box = gui.widgetBox(self.controlArea, "General Options", addSpace=True, orientation="horizontal")

            gui.checkBox(self.general_options_box, self, 'is_automatic_execution', 'Automatic Execution')
        else:
            self.is_automatic_execution=False
