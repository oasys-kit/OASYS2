
from orangewidget import gui
from orangewidget.widget import Input, Output

from oasys2.widget.widget import OWWidget
from oasys2.widget.util.widget_objects import TriggerIn
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

class TestReceiver(OWWidget):
    name = "Receiver (Test)"
    description = "Loops: Receiver"
    icon = "icons/loops.png"
    priority = 100000
    keywords = ["data", "file", "load", "read"]

    class Inputs:
        input = Input("Input", object, id="Input", default=True, auto_summary=False)

    class Outputs:
        trigger = Output("Trigger", TriggerIn, id="Trigger", default=True, auto_summary=False)


    want_main_area = 0
    want_control_area = 1

    def __init__(self):
        super(TestReceiver, self).__init__()

        self.setFixedWidth(300)
        self.setFixedHeight(100)

        gui.separator(self.controlArea, height=20)
        gui.label(self.controlArea, self, "         Receiver (Test)", orientation="horizontal")

        self.label = gui.label(self.controlArea, self, "", orientation="horizontal")

        gui.rubber(self.controlArea)

    @Inputs.input
    def send_trigger(self, input):
        self.label.setText(str(input))

        self.Outputs.trigger.send(TriggerIn(new_object=True))

add_widget_parameters_to_module(__name__)
