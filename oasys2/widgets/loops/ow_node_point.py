
from oasys2.widget.widget import OWLoopWidget, OWAction
from oasys2.widget import gui
from oasys2.widget.gui import ConfirmDialog, Styles

from orangewidget.widget import Input, Output

from AnyQt.QtWidgets import QMessageBox
from orangewidget.settings import Setting

from oasys2.widget.util.widget_objects import TriggerIn, TriggerOut
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

class LoopPoint(OWLoopWidget):
    name = "Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    priority = 2
    keywords = "data", "file", "load", "read"

    class Inputs:
        trigger_in = Input("Trigger", TriggerIn, id="TriggerIn", default=True, auto_summary=False)

    class Outputs:
        trigger_out = Output("Trigger", TriggerOut, id="TriggerOut", default=True, auto_summary=False)

    want_main_area = 0

    number_of_new_objects = Setting(1)
    current_new_object = 0
    run_loop = True
    suspend_loop = False

    def __init__(self):
        super(LoopPoint, self).__init__()

        self.runaction = OWAction("Start", self)
        self.runaction.triggered.connect(self.startLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Stop", self)
        self.runaction.triggered.connect(self.stopLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Suspend", self)
        self.runaction.triggered.connect(self.suspendLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Restart", self)
        self.runaction.triggered.connect(self.restartLoop)
        self.addAction(self.runaction)

        self.setFixedWidth(400)
        self.setFixedHeight(250)

        button_box = gui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        self.start_button = gui.button(button_box, self, "Start", callback=self.startLoop)
        self.start_button.setFixedHeight(35)

        stop_button = gui.button(button_box, self, "Stop", callback=self.stopLoop)
        stop_button.setStyleSheet("color: red; font-weight: bold; height: 35px;")

        self.stop_button = stop_button

        button_box = gui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        suspend_button = gui.button(button_box, self, "Suspend", callback=self.suspendLoop)
        suspend_button.setStyleSheet("color: orange; font-weight: bold; height: 35px;")

        self.re_start_button = gui.button(button_box, self, "Restart", callback=self.restartLoop)
        self.re_start_button.setFixedHeight(35)
        self.re_start_button.setEnabled(False)

        left_box_1 = gui.widgetBox(self.controlArea, "Loop Management", addSpace=True, orientation="vertical", width=380, height=100)

        gui.lineEdit(left_box_1, self, "number_of_new_objects", "Number of new " + self.get_object_name() + "s", labelWidth=250, valueType=int, orientation="horizontal")

        self.le_current_new_object = gui.lineEdit(left_box_1, self, "current_new_object", "Current New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        self.le_current_new_object.setStyleSheet(Styles.line_edit_read_only)

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

add_widget_parameters_to_module(__name__)
