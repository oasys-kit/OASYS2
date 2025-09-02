import os, numpy

try:
    from PyQt5 import QtCore, QtWidgets, QtGui
except:
    pass

class TriggerOut:
    def __init__(self, new_object=False, additional_parameters={}):
        super().__init__()

        self.new_object = new_object

        self.__additional_parameters=additional_parameters

    def has_additional_parameter(self, name):
        return name in self.__additional_parameters.keys()

    def get_additional_parameter(self, name):
        return self.__additional_parameters[name]

class TriggerIn:
    def __init__(self, new_object=False, interrupt=False, additional_parameters={}):
        super().__init__()

        self.new_object = new_object
        self.interrupt = interrupt

        self.__additional_parameters=additional_parameters

    def has_additional_parameter(self, name):
        return name in self.__additional_parameters.keys()

    def get_additional_parameter(self, name):
        return self.__additional_parameters[name]

try:
    class EmittingStream(QtCore.QObject):
        textWritten = QtCore.pyqtSignal(str)

        def write(self, text):
            self.textWritten.emit(str(text))

        def flush(self):
            pass
except:
    pass

import time

try:
    class ShowTextDialog(QtWidgets.QDialog):

        def __init__(self, title, text, width=650, height=400, parent=None, label=False, button=True):
            QtWidgets.QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QtWidgets.QVBoxLayout(self)

            if label:
                text_area = QtWidgets.QLabel(text)
            else:
                text_edit = QtWidgets.QTextEdit("", self)
                text_edit.append(text)
                text_edit.setReadOnly(True)

                text_area = QtWidgets.QScrollArea(self)
                text_area.setWidget(text_edit)
                text_area.setWidgetResizable(False)
                text_area.setFixedHeight(height)
                text_area.setFixedWidth(width)

            layout.addWidget(text_area)

            if button:
                bbox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
                bbox.accepted.connect(self.accept)
                layout.addWidget(bbox)

        @classmethod
        def show_text(cls, title, text, width=650, height=400, parent=None, label=False, button=True):
            dialog = ShowTextDialog(title, text, width, height, parent, label, button)
            dialog.show()

    import sys, threading

    from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QLabel
    from PyQt5.QtGui import QPainter, QPalette, QBrush, QPen, QColor
    from PyQt5.QtCore import Qt

    class ShowWaitDialog(QDialog):
        def __init__(self, title, text, width=500, height=80, parent=None):
            QDialog.__init__(self, parent)
            self.setModal(True)
            self.setWindowTitle(title)
            layout = QVBoxLayout(self)
            self.setFixedWidth(width)
            self.setFixedHeight(height)
            label = QLabel()
            label.setFixedWidth(width*0.95)
            label.setText(text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: 14px")
            layout.addWidget(label)
            label = QLabel()
            label.setFixedWidth(width*0.95)
            label.setText("Please wait....")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font: bold italic 16px; color: rgb(232, 120, 32);")
            layout.addWidget(label)

    class Overlay(QWidget):

        def __init__(self, container_widget=None, target_method=None, wait=0.001):

            QWidget.__init__(self, container_widget)
            self.container_widget = container_widget
            self.target_method = target_method
            palette = QPalette(self.palette())
            palette.setColor(palette.Background, Qt.transparent)
            self.setPalette(palette)
            self.__wait = wait

        def paintEvent(self, event):
            painter = QPainter()
            painter.begin(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.fillRect(event.rect(), QBrush(QColor(255, 255, 255, 127)))
            painter.setPen(QPen(Qt.NoPen))

            for i in range(1, 7):
                if self.position_index == i:
                    painter.setBrush(QBrush(QColor(255, 165, 0)))
                else:
                    painter.setBrush(QBrush(QColor(127, 127, 127)))
                painter.drawEllipse(
                    self.width()/2 + 30 * numpy.cos(2 * numpy.pi * i / 6.0) - 10,
                    self.height()/2 + 30 * numpy.sin(2 * numpy.pi * i / 6.0) - 10,
                    20, 20)

                time.sleep(self.__wait)

            painter.end()

        def showEvent(self, event):
            self.timer = self.startTimer(0)
            self.counter = 0
            self.position_index = 0
            if not self.target_method is None:
                t = threading.Thread(target=self.target_method)
                t.start()

        def hideEvent(self, QHideEvent):
            self.killTimer(self.timer)

        def timerEvent(self, event):
            self.counter += 1
            self.position_index += 1
            if self.position_index == 7: self.position_index = 1
            self.update()
except:
    pass



