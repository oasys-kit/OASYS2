
from orangewidget import gui
from orangewidget.widget import Input, Output

from oasys2.widget.widget import OWWidget

from oasys2.widget.util.widget_objects import TriggerOut
from oasys2.canvas.util.canvas_util import add_parameter_to_module


class Pin(OWWidget):
    name = "Pin"
    description = "Tools: Pin"
    icon = "icons/pin.png"
    priority = 3
    keywords = ["data", "file", "load", "read"]

    class Inputs:
        trigger_in = Input("Trigger", TriggerOut, id="TriggerOut", auto_summary=False)

    class Outputs:
        trigger_out = Output("Trigger", TriggerOut, id="TriggerOut", auto_summary=False)


    want_main_area = 0
    want_control_area = 1

    def __init__(self):
        super(Pin, self).__init__()

        self.setFixedWidth(300)
        self.setFixedHeight(100)

        gui.separator(self.controlArea, height=20)
        gui.label(self.controlArea, self, "         SIMPLE PASSAGE POINT", orientation="horizontal")
        gui.rubber(self.controlArea)

    @Inputs.trigger_in
    def passTrigger(self, trigger):
            self.Outputs.trigger_out.send(trigger)

add_parameter_to_module(__name__, Pin)
