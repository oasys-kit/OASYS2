__author__ = 'labx'
__menu__="just for discovery"

SEPARATOR = "OMENU_SEPARATOR"
OPEN_CONTAINER = "OPEN_CONTAINER"
CLOSE_CONTAINER = "CLOSE_CONTAINER"


from AnyQt import QtWidgets
from orangecanvas.scheme.link import SchemeLink

class OMenu():

    def __init__(self, name="NewMenu"):
        self.name = name
        self.canvas_main_window=None
        self.sub_menu_names = []

    def setCanvasMainWindow(self, canvas_main_window):
        self.canvas_main_window = canvas_main_window

    def addSubMenu(self, name):
        self.sub_menu_names.append(name)

    def addSeparator(self):
        self.sub_menu_names.append(SEPARATOR)

    def openContainer(self):
        self.sub_menu_names.append(OPEN_CONTAINER)

    def closeContainer(self):
        self.sub_menu_names.append(CLOSE_CONTAINER)

    def addContainer(self, name):
        self.sub_menu_names.append(name)

    def isSeparator(self, name):
        return name == SEPARATOR

    def isOpenContainer(self, name):
        return name == OPEN_CONTAINER

    def isCloseContainer(self, name):
        return name == CLOSE_CONTAINER

    def getSubMenuNamesList(self):
        return self.sub_menu_names

    def showConfirmMessage(self, message, informative_text=None):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Question)
        msgBox.setText(message)
        msgBox.setInformativeText(message if informative_text is None else informative_text)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        msgBox.setDefaultButton(QtWidgets.QMessageBox.No)
        ret = msgBox.exec()
        return ret

    def showWarningMessage(self, message):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Warning)
        msgBox.setText(message)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgBox.exec()

    def showCriticalMessage(self, message):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QtWidgets.QMessageBox.Critical)
        msgBox.setText(message)
        msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
        msgBox.exec()

    def getWidgetFromNode(self, node):
        return self.canvas_main_window.current_document().scheme().widget_for_node(node)

    def createLinks(self, nodes, excluded_names=[], source_channel="In", sink_channel="Out"):
        previous_node = None
        for node in nodes:
            if not (isinstance(node, str) and node in excluded_names):
                if not previous_node is None :
                    if not (isinstance(previous_node, str) and previous_node in excluded_names):
                        link = SchemeLink(source_node=previous_node, source_channel=source_channel, sink_node=node, sink_channel=sink_channel)
                        self.canvas_main_window.current_document().addLink(link=link)
            previous_node = node

    def getWidgetDesc(self, widget_name, excluded_names=[]):
        if widget_name in excluded_names: return widget_name
        else: return self.canvas_main_window.widget_registry.widget(widget_name)

    def createNewNode(self, widget_desc):
        return self.canvas_main_window.current_document().createNewNode(widget_desc)


