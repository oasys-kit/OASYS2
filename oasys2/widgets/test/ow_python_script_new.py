import sys
import os
import unicodedata

from AnyQt import QtGui, QtWidgets

from AnyQt.QtWidgets import (
    QListView, QSizePolicy, QAction,
    QMenu, QSplitter, QToolButton,
    QFileDialog
)

from AnyQt.QtGui import (
     QFont, QKeySequence
)


from AnyQt.QtCore import Qt, QByteArray
from orangewidget.widget import Output, MultiInput
from oasys2.widget.widget import OWWidget, OWAction
from oasys2.widget import gui as oasysgui
from oasys2.widget.util.script import itemmodels
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

from orangewidget import gui
from orangewidget.settings import Setting

__all__ = ["OWPythonScriptNew"]

from oasys2.widgets.tools.ow_python_script import PythonConsole, PythonScriptEditor, PythonSyntaxHighlighter, Script, ScriptItemDelegate, select_row

class OWPythonScriptNew(OWWidget):
    name = "Python Script New"
    description = "Executes a Python script."
    icon = "icons/python_script.png"
    priority = 1.1

    class Inputs:
        object = MultiInput("In Object", object, default=False, auto_summary=False)

    class Outputs:
        object = Output("Out Object", object, auto_summary=False)

    library_list_source  = Setting([Script("Hello world", "print('Hello world')\n")])
    current_script_index = Setting(0)
    splitter_state       = Setting(None)
    auto_execute         = Setting(False)

    fonts = ["8", "9", "10", "11", "12", "14", "16", "20", "24"]
    font_size = Setting(4)

    in_object  = []

    def __init__(self):
        super().__init__()

        self.runaction = OWAction("Execute", self)
        self.runaction.triggered.connect(self.execute)
        self.addAction(self.runaction)

        for s in self.library_list_source: s.flags = 0

        self._cached_documents = {}

        self.infoBox = gui.widgetBox(self.controlArea, 'Info')
        gui.label(self.infoBox, self,
                  "<p>Execute python script.</p><p>Input variables:<ul><li> " + \
                  "<li>".join(["in_object[0]", ".", ".", ".", "in_object[n]"]) + \
                  "</ul></p><p>Output variable:<ul><li>" + \
                  "<li>out_object</ul></p>"
                  )

        self.optionBox = oasysgui.widgetBox(self.controlArea, 'Options')

        gui.comboBox(self.optionBox, self, "font_size", label="Font Size", labelWidth=120,
                     items=self.fonts,
                     sendSelectedValue=False, orientation="horizontal", callback=self.changeFont)

        self.libraryList = itemmodels.PyListModel(
            [], self,
            flags=Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

        self.libraryList.wrap(self.library_list_source)

        self.controlBox = gui.widgetBox(self.controlArea, 'Library')
        self.controlBox.layout().setSpacing(1)

        self.libraryView = QListView(
            editTriggers=QListView.DoubleClicked |
                         QListView.EditKeyPressed,
            sizePolicy=QSizePolicy(QSizePolicy.Ignored,
                                   QSizePolicy.Preferred)
        )
        self.libraryView.setItemDelegate(ScriptItemDelegate(self))
        self.libraryView.setModel(self.libraryList)

        self.libraryView.selectionModel().selectionChanged.connect(
            self.onSelectedScriptChanged
        )
        self.controlBox.layout().addWidget(self.libraryView)

        w = itemmodels.ModelActionsWidget()

        self.addNewScriptAction = action = QAction("+", self)
        action.setToolTip("Add a new script to the library")
        action.triggered.connect(self.onAddScript)
        w.addAction(action)

        action = QAction(unicodedata.lookup("MINUS SIGN"), self)
        action.setToolTip("Remove script from library")
        action.triggered.connect(self.onRemoveScript)
        w.addAction(action)

        action = QAction("Update", self)
        action.setToolTip("Save changes in the editor to library")
        action.setShortcut(QKeySequence(QKeySequence.Save))
        action.triggered.connect(self.commitChangesToLibrary)
        w.addAction(action)

        action = QAction("More", self, toolTip="More actions")

        new_from_file = QAction("Import a script from a file", self)
        save_to_file = QAction("Save selected script to a file", self)
        save_to_file.setShortcut(QKeySequence(QKeySequence.SaveAs))

        new_from_file.triggered.connect(self.onAddScriptFromFile)
        save_to_file.triggered.connect(self.saveScript)

        menu = QMenu(w)
        menu.addAction(new_from_file)
        menu.addAction(save_to_file)
        action.setMenu(menu)
        button = w.addAction(action)
        button.setPopupMode(QToolButton.InstantPopup)

        w.layout().setSpacing(1)

        self.controlBox.layout().addWidget(w)

        self.runBox = gui.widgetBox(self.controlArea, 'Run')
        gui.button(self.runBox, self, "Execute", callback=self.execute)
        gui.checkBox(self.runBox, self, "auto_execute", "Auto execute",
                       tooltip="Run the script automatically whenever " +
                               "the inputs to the widget change.")

        self.splitCanvas = QSplitter(Qt.Vertical, self.mainArea)
        self.mainArea.layout().addWidget(self.splitCanvas)

        self.defaultFont = defaultFont = \
            "Monaco" if sys.platform == "darwin" else "Courier"

        self.textBox = gui.widgetBox(self, 'Python script')
        self.splitCanvas.addWidget(self.textBox)
        self.text = PythonScriptEditor(self)
        self.textBox.layout().addWidget(self.text)

        self.textBox.setAlignment(Qt.AlignVCenter)
        self.text.setTabStopWidth(4)

        self.text.modificationChanged[bool].connect(self.onModificationChanged)

        self.saveAction = action = QAction("&Save", self.text)
        action.setToolTip("Save script to file")
        action.setShortcut(QKeySequence(QKeySequence.Save))
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action.triggered.connect(self.saveScript)

        self.consoleBox = gui.widgetBox(self, 'Console')
        self.splitCanvas.addWidget(self.consoleBox)
        self.console = PythonConsole(self.__dict__, self)
        self.consoleBox.layout().addWidget(self.console)
        self.console.document().setDefaultFont(QFont(defaultFont))
        self.consoleBox.setAlignment(Qt.AlignBottom)
        self.console.setTabStopWidth(4)

        select_row(self.libraryView, self.current_script_index)

        self.splitCanvas.setSizes([2, 1])
        if self.splitter_state is not None:
            self.splitCanvas.restoreState(QByteArray(bytearray(self.splitter_state, "ascii")))

        self.splitCanvas.splitterMoved[int, int].connect(self.onSpliterMoved)
        self.controlArea.layout().addStretch(1)
        self.resize(800, 600)

        self.changeFont()

    @Inputs.object
    def set_object(self, index, object):
        self.in_object[index] = object

    @Inputs.object.insert
    def insert_object(self, index, object):
        self.in_object.insert(index, object)

    @Inputs.object.remove
    def remove_object(self, index):
        self.in_object.pop(index)

    def handleNewSignals(self):
        if self.auto_execute:
            self.execute()

    def selectedScriptIndex(self):
        rows = self.libraryView.selectionModel().selectedRows()
        if rows:
            return  [i.row() for i in rows][0]
        else:
            return None

    def setSelectedScript(self, index):
        select_row(self.libraryView, index)

    def onAddScript(self, *args):
        self.libraryList.append(Script("New script", "", 0))
        self.setSelectedScript(len(self.libraryList) - 1)

    def onAddScriptFromFile(self, *args):
        filename = QFileDialog.getOpenFileName(
            self, 'Open Python Script',
            os.path.expanduser("~/"),
            'Python files (*.py)\nAll files(*.*)'
        )[0]

        filename = str(filename)
        if filename:
            name = os.path.basename(filename)
            contents = open(filename, "rb").read().decode("utf-8", errors="ignore")
            self.libraryList.append(Script(name, contents, 0, filename))
            self.setSelectedScript(len(self.libraryList) - 1)

    def onRemoveScript(self, *args):
        index = self.selectedScriptIndex()
        if index is not None:
            del self.libraryList[index]
            select_row(self.libraryView, max(index - 1, 0))

    def onSaveScriptToFile(self, *args):
        index = self.selectedScriptIndex()
        if index is not None:
            self.saveScript()

    def onSelectedScriptChanged(self, selected, deselected):
        index = [i.row() for i in selected.indexes()]
        if index:
            current = index[0]
            if current >= len(self.libraryList):
                self.addNewScriptAction.trigger()
                return

            self.text.setDocument(self.documentForScript(current))
            self.current_script_index = current

    def documentForScript(self, script=0):
        if type(script) != Script:
            script = self.libraryList[script]

        if script not in self._cached_documents:
            doc = QtGui.QTextDocument(self)
            doc.setDocumentLayout(QtWidgets.QPlainTextDocumentLayout(doc))
            doc.setPlainText(script.script)
            doc.setDefaultFont(QFont(self.defaultFont))
            doc.highlighter = PythonSyntaxHighlighter(doc)
            doc.modificationChanged[bool].connect(self.onModificationChanged)
            doc.setModified(False)
            self._cached_documents[script] = doc
        return self._cached_documents[script]

    def commitChangesToLibrary(self, *args):
        index = self.selectedScriptIndex()
        if index is not None:
            self.libraryList[index].script = self.text.toPlainText()
            self.text.document().setModified(False)
            self.libraryList.emitDataChanged(index)

    def onModificationChanged(self, modified):
        index = self.selectedScriptIndex()
        if index is not None:
            self.libraryList[index].flags = Script.Modified if modified else 0
            self.libraryList.emitDataChanged(index)

    def onSpliterMoved(self, pos, ind):
        self.splitter_state = str(self.splitCanvas.saveState())

    def updateSelecetdScriptState(self):
        index = self.selectedScriptIndex()
        if index is not None:
            script = self.libraryList[index]
            self.libraryList[index] = Script(script.name,
                                             self.text.toPlainText(),
                                             0)

    def saveScript(self):
        index = self.selectedScriptIndex()
        if index is not None:
            script = self.libraryList[index]
            filename = script.filename
        else:
            filename = os.path.expanduser("~/")

        filename = QFileDialog.getSaveFileName(
            self, 'Save Python Script',
            filename,
            'Python files (*.py)\nAll files(*.*)'
        )[0]

        if filename:
            fn = ""
            head, tail = os.path.splitext(filename)
            if not tail:
                fn = head + ".py"
            else:
                fn = filename

            f = open(fn, 'w')
            f.write(self.text.toPlainText())
            f.close()

    def initial_locals_state(self):
        d = {"in_object", self.in_object}

    def execute(self):
        self._script = str(self.text.toPlainText())
        self.console.locals["in_object"] = self.in_object
        self.console.write("\nRunning script:\n")
        self.console.push("exec(_script)")
        self.console.new_prompt(sys.ps1)

        out_object  = self.console.locals.get("out_object")
        if not out_object is None: self.Outputs.object.send(out_object)

    def changeFont(self):
        font = QFont(self.defaultFont)
        font.setPixelSize(int(self.fonts[self.font_size]))
        self.text.setFont(font)
        self.console.setFont(font)

add_widget_parameters_to_module(__name__)
