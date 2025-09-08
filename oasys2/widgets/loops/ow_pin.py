
from orangewidget import gui
from orangewidget.widget import Input, Output

from oasys2.widget.widget import OWWidget
from oasys2.widget.util.oasys_util import TriggerOut

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

WIDGET_CLASS = Pin.__qualname__
NAME         = Pin.name
DESCRIPTION  = Pin.description
ICON         = Pin.icon
PRIORITY     = Pin.priority
INPUTS       = [Pin.Inputs.trigger_in]
OUTPUTS      = [Pin.Outputs.trigger_out]

from orangewidget.utils.widgetpreview import WidgetPreview

if __name__ == "__main__":
    WidgetPreview(Pin).run(None)