import sys
import os
import code
import keyword
import itertools
import unicodedata

from AnyQt import QtGui, QtWidgets

from AnyQt.QtWidgets import (
    QListView, QSizePolicy, QAction,
    QMenu, QSplitter, QToolButton,
    QFileDialog
)

from AnyQt.QtGui import (
    QTextCursor, QFont, QColor, QPalette, QKeySequence
)


from AnyQt.QtCore import Qt, QRegularExpression, QByteArray, QItemSelectionModel

from orangewidget.widget import Output, Input
from oasys2.widget.widget import OWWidget, OWAction
from oasys2.widget import gui as oasysgui
from oasys2.widget.util.script import itemmodels
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module
from orangewidget import gui
from orangewidget.settings import Setting

__all__ = ["OWPythonScript"]

def text_format(foreground=Qt.black, weight=QFont.Normal):
    fmt = QtGui.QTextCharFormat()
    fmt.setForeground(QtGui.QBrush(foreground))
    fmt.setFontWeight(weight)
    return fmt


class PythonSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent=None):

        self.keywordFormat = text_format(Qt.blue, QFont.Bold)
        self.stringFormat = text_format(Qt.darkGreen)
        self.defFormat = text_format(Qt.black, QFont.Bold)
        self.commentFormat = text_format(Qt.lightGray)
        self.decoratorFormat = text_format(Qt.darkGray)

        self.keywords = list(keyword.kwlist)

        self.rules = [(QRegularExpression(r"\b%s\b" % kwd), self.keywordFormat)
                      for kwd in self.keywords] + \
                     [(QRegularExpression(r"\bdef\s+([A-Za-z_]+[A-Za-z0-9_]+)\s*\("),
                       self.defFormat),
                      (QRegularExpression(r"\bclass\s+([A-Za-z_]+[A-Za-z0-9_]+)\s*\("),
                       self.defFormat),
                      (QRegularExpression(r"'.*'"), self.stringFormat),
                      (QRegularExpression(r'".*"'), self.stringFormat),
                      (QRegularExpression(r"#.*"), self.commentFormat),
                      (QRegularExpression(r"@[A-Za-z_]+[A-Za-z0-9_]+"),
                       self.decoratorFormat)]

        self.multilineStart = QRegularExpression(r"(''')|" + r'(""")')
        self.multilineEnd = QRegularExpression(r"(''')|" + r'(""")')

        super().__init__(parent)

    def highlightBlock(self, text):
        for pattern, format in self.rules:
            exp = QRegularExpression(pattern)
            it  = exp.globalMatch(text)
            while it.hasNext():
                match = it.next()
                group  = 1 if (exp.captureCount() > 0 and match.capturedStart(1) != -1) else 0
                start  = match.capturedStart(group)
                length = match.capturedLength(group)
                self.setFormat(start, length, format)

        # Multi line strings
        start = self.multilineStart
        end   = self.multilineEnd
        self.setCurrentBlockState(0)

        def find_index(rx: QRegularExpression, s: str, pos: int = 0) -> int:
            m = rx.match(s, pos)
            return m.capturedStart(0) if m.hasMatch() else -1

        startIndex, skip = 0, 0
        if self.previousBlockState() != 1:
            startIndex, skip = find_index(start, text), 3
        while startIndex >= 0:
            endIndex = find_index(end, text, startIndex + skip)
            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLen = len(text) - startIndex
            else:
                commentLen = endIndex - startIndex + 3
            self.setFormat(startIndex, commentLen, self.stringFormat)
            startIndex, skip = find_index(start, text, startIndex + commentLen + 3), 3

class PythonScriptEditor(QtWidgets.QPlainTextEdit):
    INDENT = 4

    def __init__(self, parent=None):
        QtWidgets.QPlainTextEdit.__init__(self, parent)
        self.setStyleSheet("background-color: white;")

    def lastLine(self):
        text = str(self.toPlainText())
        pos = self.textCursor().position()
        index = text.rfind("\n", 0, pos)
        text = text[index: pos].lstrip("\n")
        return text

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            text = self.lastLine()
            indent = len(text) - len(text.lstrip())
            if text.strip() == "pass" or text.strip().startswith("return "):
                indent = max(0, indent - self.INDENT)
            elif text.strip().endswith(":"):
                indent += self.INDENT
            super().keyPressEvent(event)
            self.insertPlainText(" " * indent)
        elif event.key() == Qt.Key_Tab:
            self.insertPlainText(" " * self.INDENT)
        elif event.key() == Qt.Key_Backspace:
            text = self.lastLine()
            if text and not text.strip():
                cursor = self.textCursor()
                for i in range(min(self.INDENT, len(text))):
                    cursor.deletePreviousChar()
            else:
                super().keyPressEvent(event)

        else:
            super().keyPressEvent(event)


class PythonConsole(QtWidgets.QPlainTextEdit, code.InteractiveConsole):
    def __init__(self, locals=None, parent=None):
        QtWidgets.QPlainTextEdit.__init__(self, parent)
        code.InteractiveConsole.__init__(self, locals)
        self.setStyleSheet("background-color: white;")

        self.history, self.historyInd = [""], 0
        self.loop = self.interact()
        next(self.loop)

    def setLocals(self, locals):
        self.locals = locals

    def interact(self, banner=None):
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = ('Type "help", "copyright", "credits" or "license" '
                'for more information.')
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" %
                       (sys.version, sys.platform, cprt,
                        self.__class__.__name__))
        else:
            self.write("%s\n" % str(banner))
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                self.new_prompt(prompt)
                yield
                try:
                    line = self.raw_input(prompt)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0

    def raw_input(self, prompt):
        input = str(self.document().lastBlock().previous().text())
        return input[len(prompt):]

    def new_prompt(self, prompt):
        self.write(prompt)
        self.newPromptPos = self.textCursor().position()

    def write(self, data):
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        cursor.insertText(data)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def push(self, line):
        if self.history[0] != line:
            self.history.insert(0, line)
        self.historyInd = 0

        saved = sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = self, self
            return code.InteractiveConsole.push(self, line)
        finally:
            sys.stdout, sys.stderr = saved

    def setLine(self, line):
        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.End)
        cursor.setPosition(self.newPromptPos, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertText(line)
        self.setTextCursor(cursor)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return:
            self.write("\n")
            next(self.loop)
        elif event.key() == Qt.Key_Up:
            self.historyUp()
        elif event.key() == Qt.Key_Down:
            self.historyDown()
        elif event.key() == Qt.Key_Tab:
            self.complete()
        elif event.key() in [Qt.Key_Left, Qt.Key_Backspace]:
            if self.textCursor().position() > self.newPromptPos:
                QtWidgets.QPlainTextEdit.keyPressEvent(self, event)
        else:
            QtWidgets.QPlainTextEdit.keyPressEvent(self, event)

    def historyUp(self):
        self.setLine(self.history[self.historyInd])
        self.historyInd = min(self.historyInd + 1, len(self.history) - 1)

    def historyDown(self):
        self.setLine(self.history[self.historyInd])
        self.historyInd = max(self.historyInd - 1, 0)

    def complete(self):
        pass

    def flush(self):
        pass

    def _moveCursorToInputLine(self):
        """
        Move the cursor to the input line if not already there. If the cursor
        if already in the input line (at position greater or equal to
        `newPromptPos`) it is left unchanged, otherwise it is moved at the
        end.

        """
        cursor = self.textCursor()
        pos = cursor.position()
        if pos < self.newPromptPos:
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)

    def pasteCode(self, source):
        """
        Paste source code into the console.
        """
        self._moveCursorToInputLine()

        for line in interleave(source.splitlines(), itertools.repeat("\n")):
            if line != "\n":
                self.insertPlainText(line)
            else:
                self.write("\n")
                next(self.loop)

    def insertFromMimeData(self, source):
        """
        Reimplemented from QPlainTextEdit.insertFromMimeData.
        """
        if source.hasText():
            self.pasteCode(str(source.text()))
            return


def interleave(seq1, seq2):
    """
    Interleave elements of `seq2` between consecutive elements of `seq1`.

        >>> list(interleave([1, 3, 5], [2, 4]))
        [1, 2, 3, 4, 5]

    """
    iterator1, iterator2 = iter(seq1), iter(seq2)
    leading = next(iterator1)
    for element in iterator1:
        yield leading
        yield next(iterator2)
        leading = element

    yield leading


class Script(object):
    Modified = 1
    MissingFromFilesystem = 2

    def __init__(self, name, script, flags=0, filename=None):
        self.name = name
        self.script = script
        self.flags = flags
        self.filename = filename


class ScriptItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        super().__init__(parent)

    def displayText(self, script, locale):
        if script.flags & Script.Modified:
            return "*" + script.name
        else:
            return script.name

    def paint(self, painter, option, index):
        script = index.data(Qt.DisplayRole)

        if script.flags & Script.Modified:
            option = QtWidgets.QStyleOptionViewItem(option)
            option.palette.setColor(QPalette.Text, QColor(Qt.red))
            option.palette.setColor(QPalette.Highlight, QColor(Qt.darkRed))
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        return QtWidgets.QLineEdit(parent)

    def setEditorData(self, editor, index):
        script = index.data(Qt.DisplayRole)
        editor.setText(script.name)

    def setModelData(self, editor, model, index):
        model[index.row()].name = str(editor.text())


def select_row(view, row):
    """
    Select a `row` in an item view
    """
    selmodel = view.selectionModel()
    selmodel.select(view.model().index(row, 0),
                    QItemSelectionModel.ClearAndSelect)

class OWPythonScript(OWWidget):
    name = "Python Script"
    description = "Executes a Python script."
    icon = "icons/python_script.png"
    priority = 1

    class Inputs:
        object_1  = Input("In Object #1", object, default=False, auto_summary=False)
        object_2  = Input("In Object #2", object, default=False, auto_summary=False)
        object_3  = Input("In Object #3", object, default=False, auto_summary=False)
        object_4  = Input("In Object #4", object, default=False, auto_summary=False)
        object_5  = Input("In Object #5", object, default=False, auto_summary=False)
        object_6  = Input("In Object #6", object, default=False, auto_summary=False)
        object_7  = Input("In Object #7", object, default=False, auto_summary=False)
        object_8  = Input("In Object #8", object, default=False, auto_summary=False)
        object_9  = Input("In Object #9", object, default=False, auto_summary=False)
        object_10 = Input("In Object #10", object, default=False, auto_summary=False)

    class Outputs:
        object = Output("Out Object", object, auto_summary=False)

    libraryListSource  = Setting([Script("Hello world", "print('Hello world')\n")])
    currentScriptIndex = Setting(0)
    splitterState = Setting(None)
    auto_execute = Setting(False)

    fonts = ["8", "9", "10", "11", "12", "14", "16", "20", "24"]
    font_size = Setting(4)

    def __init__(self):
        super().__init__()

        self.runaction = OWAction("Execute", self)
        self.runaction.triggered.connect(self.execute)
        self.addAction(self.runaction)

        self.in_data = None
        self.in_distance = None
        self.in_learner = None
        self.in_classifier = None
        self.in_object_1  = None
        self.in_object_2  = None
        self.in_object_3  = None
        self.in_object_4  = None
        self.in_object_5  = None
        self.in_object_6  = None
        self.in_object_7  = None
        self.in_object_8  = None
        self.in_object_9  = None
        self.in_object_10 = None

        for s in self.libraryListSource: s.flags = 0

        self._cachedDocuments = {}

        self.infoBox = gui.widgetBox(self.controlArea, 'Info')
        gui.label(
            self.infoBox, self,
            "<p>Execute python script.</p><p>Input variables:<ul><li> " + \
            "<li>".join(["in_object_1", ".",".",".", "in_object_10"]) + \
            "</ul></p><p>Output variables:<ul><li>" + \
            "<li>out_object</ul></p>"
        )

        self.optionBox = oasysgui.widgetBox(self.controlArea, 'Options')

        gui.comboBox(self.optionBox, self, "font_size", label="Font Size", labelWidth=120,
                     items=self.fonts,
                     sendSelectedValue=False, orientation="horizontal", callback=self.changeFont)

        self.libraryList = itemmodels.PyListModel(
            [], self,
            flags=Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)

        self.libraryList.wrap(self.libraryListSource)

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
        self.text.setTabStopDistance(4)

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
        self.console.setTabStopDistance(4)

        select_row(self.libraryView, self.currentScriptIndex)

        self.splitCanvas.setSizes([2, 1])
        if self.splitterState is not None:
            self.splitCanvas.restoreState(QByteArray(bytearray(self.splitterState, "ascii")))

        self.splitCanvas.splitterMoved[int, int].connect(self.onSpliterMoved)
        self.controlArea.layout().addStretch(1)
        self.resize(800, 600)

        self.changeFont()

    def setExampleTable(self, et):
        self.in_data = et

    def setDistanceMatrix(self, dm):
        self.in_distance = dm

    def setLearner(self, learner):
        self.in_learner = learner

    def setClassifier(self, classifier):
        self.in_classifier = classifier

    @Inputs.object_1
    def setObject1(self, obj):
        self.in_object_1 = obj

    @Inputs.object_2
    def setObject2(self, obj):
        self.in_object_2 = obj

    @Inputs.object_3
    def setObject3(self, obj):
        self.in_object_3 = obj

    @Inputs.object_4
    def setObject4(self, obj):
        self.in_object_4 = obj

    @Inputs.object_5
    def setObject5(self, obj):
        self.in_object_5 = obj

    @Inputs.object_6
    def setObject6(self, obj):
        self.in_object_6 = obj

    @Inputs.object_7
    def setObject7(self, obj):
        self.in_object_7 = obj

    @Inputs.object_8
    def setObject8(self, obj):
        self.in_object_8 = obj

    @Inputs.object_9
    def setObject9(self, obj):
        self.in_object_9 = obj

    @Inputs.object_10
    def setObject10(self, obj):
        self.in_object_10 = obj

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
            self.currentScriptIndex = current

    def documentForScript(self, script=0):
        if type(script) != Script:
            script = self.libraryList[script]

        if script not in self._cachedDocuments:
            doc = QtGui.QTextDocument(self)
            doc.setDocumentLayout(QtWidgets.QPlainTextDocumentLayout(doc))
            doc.setPlainText(script.script)
            doc.setDefaultFont(QFont(self.defaultFont))
            doc.highlighter = PythonSyntaxHighlighter(doc)
            doc.modificationChanged[bool].connect(self.onModificationChanged)
            doc.setModified(False)
            self._cachedDocuments[script] = doc
        return self._cachedDocuments[script]

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
        self.splitterState = str(self.splitCanvas.saveState())

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

    def execute(self):
        self._script = str(self.text.toPlainText())

        self.console.locals["in_object_1"]  = self.in_object_1
        self.console.locals["in_object_2"]  = self.in_object_2
        self.console.locals["in_object_3"]  = self.in_object_3
        self.console.locals["in_object_4"]  = self.in_object_4
        self.console.locals["in_object_5"]  = self.in_object_5
        self.console.locals["in_object_6"]  = self.in_object_6
        self.console.locals["in_object_7"]  = self.in_object_7
        self.console.locals["in_object_8"]  = self.in_object_8
        self.console.locals["in_object_9"]  = self.in_object_9
        self.console.locals["in_object_10"] = self.in_object_10

        self.console.write("\nRunning script:\n")
        self.console.push("exec(_script)")
        self.console.new_prompt(sys.ps1)

        out_object = self.console.locals.get("out_object")

        if not out_object is None: self.Outputs.object.send(out_object)

    def changeFont(self):
        font = QFont(self.defaultFont)
        font.setPixelSize(int(self.fonts[self.font_size]))
        self.text.setFont(font)
        self.console.setFont(font)

add_widget_parameters_to_module(__name__)