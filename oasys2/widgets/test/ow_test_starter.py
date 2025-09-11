
from orangewidget import gui
from orangewidget.widget import Input, Output

from oasys2.widget.widget import OWWidget

from oasys2.widget.util.widget_objects import TriggerOut
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module


class TestStarter(OWWidget):
    name = "Starter (Test)"
    description = "Loops: Starter"
    icon = "icons/loops.png"
    priority = 1000
    keywords = ["data", "file", "load", "read"]

    class Inputs:
        trigger = Input("Trigger", TriggerOut, id="Trigger", default=True, auto_summary=False)

    class Outputs:
        output = Output("Output", object, id="Output", default=True, auto_summary=False)

    want_main_area = 0
    want_control_area = 1

    counter = 0

    def __init__(self):
        super(TestStarter, self).__init__()

        self.setFixedWidth(300)
        self.setFixedHeight(100)

        gui.separator(self.controlArea, height=20)
        gui.label(self.controlArea, self, "         Test Starter", orientation="horizontal")
        gui.rubber(self.controlArea)

    @Inputs.trigger
    def start(self, trigger):
        if trigger:
            if trigger.new_object == True:
                self.counter += 1
                self.Outputs.output.send(f"Iteration nr {self.counter}")
            else:
                self.counter = 0

add_widget_parameters_to_module(__name__)
