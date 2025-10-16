import sys
import inspect

from AnyQt.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QTextEdit, QScrollArea
from AnyQt.QtCore import Qt

def add_widget_parameters_to_module(module_name):
    module             = sys.modules[module_name]
    oasys_widget_class = getattr(sys.modules["oasys2.widget.widget"], "OWWidget")
    widget_class       = None

    for _, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module_name:
            if issubclass(obj, oasys_widget_class):
                widget_class = obj
                break

    if not widget_class is None:
        setattr(module, "WIDGET_CLASS", widget_class.__qualname__)
        try: setattr(module, "NAME", widget_class.name)
        except: print(f"no NAME for {module_name}.{widget_class}")
        try: setattr(module, "DESCRIPTION", widget_class.description)
        except: print(f"no DESCRIPTION for {module_name}.{widget_class}")
        try: setattr(module, "ICON", widget_class.icon)
        except: print(f"no ICON for {module_name}.{widget_class}")
        try: setattr(module, "PRIORITY", widget_class.priority)
        except: print(f"no PRIORITY for {module_name}.{widget_class}")
        try: setattr(module, "INPUTS", [getattr(widget_class.Inputs, input) for input in widget_class.Inputs.__dict__ if not input.startswith("__")])
        except: print(f"no INPUTS for {module_name}.{widget_class}")
        try: setattr(module, "OUTPUTS", [getattr(widget_class.Outputs, output) for output in widget_class.Outputs.__dict__ if not output.startswith("__")])
        except: print(f"no OUTPUTS for {module_name}.{widget_class}")



try:
    class ShowTextDialog(QDialog):

        def __init__(self, title, text, width=650, height=400, parent=None, label=False, button=True):
            QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QVBoxLayout(self)

            if label:
                text_area = QLabel(text)
            else:
                text_edit = QTextEdit("", self)
                text_edit.append(text)
                text_edit.setReadOnly(True)

                text_area = QScrollArea(self)
                text_area.setWidget(text_edit)
                text_area.setWidgetResizable(False)
                text_area.setFixedHeight(height)
                text_area.setFixedWidth(width)

            layout.addWidget(text_area)

            if button:
                bbox = QDialogButtonBox(QDialogButtonBox.Ok)
                bbox.accepted.connect(self.accept)
                layout.addWidget(bbox)

        @classmethod
        def show_text(cls, title, text, width=650, height=400, parent=None, label=False, button=True):
            dialog = ShowTextDialog(title, text, width, height, parent, label, button)
            dialog.show()

    class ShowWaitDialog(QDialog):
        def __init__(self, title, text, width=500, height=80, parent=None):
            QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QVBoxLayout(self)
            self.setFixedWidth(width)
            self.setFixedHeight(height)
            label = QLabel()
            label.setFixedWidth(int(width*0.95))
            label.setText(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: 14px")
            layout.addWidget(label)
            label = QLabel()
            label.setFixedWidth(int(width*0.95))
            label.setText("Please wait....")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: bold italic 16px; color: rgb(232, 120, 32);")
            layout.addWidget(label)
except:
    pass