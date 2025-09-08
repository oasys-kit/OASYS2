from oasys2.widget.widget import OWWidget
from oasys2.widget import gui as oasysgui
from oasys2.widget.gui import ConfirmDialog

from orangewidget import gui
from orangewidget.widget import Input, Output

from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWidgets import QMessageBox, QAction
from orangewidget.settings import Setting

from oasys2.widget.util.oasys_util import TriggerIn, TriggerOut

class LoopPoint(OWWidget):
    name = "Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    priority = 2
    keywords = "data", "file", "load", "read"

    class Inputs:
        trigger_in = Input("Trigger", TriggerIn, id="TriggerIn", default=True)

    class Outputs:
        trigger_out = Output("Trigger", TriggerOut, id="TriggerOut", default=True)

    want_main_area = 0

    number_of_new_objects = Setting(1)
    current_new_object = 0
    run_loop = True
    suspend_loop = False

    #################################
    process_last = True
    #################################

    def __init__(self):
        super(LoopPoint, self).__init__()

        self.runaction = QAction("Start", self)
        self.runaction.triggered.connect(self.startLoop)
        self.addAction(self.runaction)

        self.runaction = QAction("Stop", self)
        self.runaction.triggered.connect(self.stopLoop)
        self.addAction(self.runaction)

        self.runaction = QAction("Suspend", self)
        self.runaction.triggered.connect(self.suspendLoop)
        self.addAction(self.runaction)

        self.runaction = QAction("Restart", self)
        self.runaction.triggered.connect(self.restartLoop)
        self.addAction(self.runaction)

        self.setFixedWidth(400)
        self.setFixedHeight(220)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        self.start_button = gui.button(button_box, self, "Start", callback=self.startLoop)
        self.start_button.setFixedHeight(35)

        stop_button = gui.button(button_box, self, "Stop", callback=self.stopLoop)
        stop_button.setFixedHeight(35)
        font = QFont(stop_button.font())
        font.setBold(True)
        stop_button.setFont(font)
        palette = QPalette(stop_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('red'))
        stop_button.setPalette(palette) # assign new palette

        self.stop_button = stop_button

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        suspend_button = gui.button(button_box, self, "Suspend", callback=self.suspendLoop)
        suspend_button.setFixedHeight(35)
        font = QFont(suspend_button.font())
        font.setBold(True)
        suspend_button.setFont(font)
        palette = QPalette(suspend_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('orange'))
        suspend_button.setPalette(palette) # assign new palette

        self.re_start_button = gui.button(button_box, self, "Restart", callback=self.restartLoop)
        self.re_start_button.setFixedHeight(35)
        self.re_start_button.setEnabled(False)

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Loop Management", addSpace=True, orientation="vertical", width=380, height=100)

        oasysgui.lineEdit(left_box_1, self, "number_of_new_objects", "Number of new " + self.get_object_name() + "s", labelWidth=250, valueType=int, orientation="horizontal")

        self.le_current_new_object = oasysgui.lineEdit(left_box_1, self, "current_new_object", "Current New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        font = QFont(self.le_current_new_object.font())
        font.setBold(True)
        self.le_current_new_object.setFont(font)
        palette = QPalette(self.le_current_new_object.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_current_new_object.setPalette(palette)

        gui.rubber(self.controlArea)

    def startLoop(self):
        self.current_new_object = 1
        self.start_button.setEnabled(False)
        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
        self.Outputs.trigger_out.send(TriggerOut(new_object=True))

    def stopLoop(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Interruption of the Loop?"):
            self.run_loop = False
            self.setStatusMessage("Interrupted by user")

    def suspendLoop(self):
        try:
            if ConfirmDialog.confirmed(parent=self, message="Confirm Suspension of the Loop?"):
                self.run_loop = False
                self.suspend_loop = True
                self.stop_button.setEnabled(False)
                self.re_start_button.setEnabled(True)
                self.setStatusMessage("Suspended by user")
        except:
            pass

    def restartLoop(self):
        try:
            self.run_loop = True
            self.suspend_loop = False
            self.stop_button.setEnabled(True)
            self.re_start_button.setEnabled(False)
            self.passTrigger(TriggerIn(new_object=True))
        except:
            pass

    @Inputs.trigger_in
    def passTrigger(self, trigger):
        if self.run_loop:
            if trigger:
                if trigger.interrupt:
                    self.current_new_object = 0
                    self.start_button.setEnabled(True)
                    self.setStatusMessage("")
                    self.Outputs.trigger_out.send(TriggerOut(new_object=False))
                elif trigger.new_object:
                    if self.current_new_object == 0:
                        QMessageBox.critical(self, "Error", "Loop has to be started properly: press the button Start", QMessageBox.Ok)
                        return

                    if self.current_new_object < self.number_of_new_objects:
                        self.current_new_object += 1
                        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
                        self.start_button.setEnabled(False)
                        self.Outputs.trigger_out.send(TriggerOut(new_object=True))
                    else:
                        self.current_new_object = 0
                        self.start_button.setEnabled(True)
                        self.setStatusMessage("")
                        self.Outputs.trigger_out.send(TriggerOut(new_object=False))
        else:
            if not self.suspend_loop:
                self.current_new_object = 0
                self.start_button.setEnabled(True)

            self.Outputs.trigger_out.send(TriggerOut(new_object=False))
            self.setStatusMessage("")
            self.run_loop = True
            self.suspend_loop = False

    def get_object_name(self):
        return "Object"

WIDGET_CLASS = LoopPoint.__qualname__
NAME         = LoopPoint.name
DESCRIPTION  = LoopPoint.description
ICON         = LoopPoint.icon
PRIORITY     = LoopPoint.priority
INPUTS       = [LoopPoint.Inputs.trigger_in]
OUTPUTS      = [LoopPoint.Outputs.trigger_out]
