import os, sys

import numpy
from AnyQt.QtCore import QRect
from AnyQt.QtWidgets import QApplication, QMessageBox

from matplotlib import cm
from matplotlib.figure import Figure

from orangewidget import gui
from orangewidget.settings import Setting
from orangewidget.widget import Output

from oasys2.widget.gui import FigureCanvas3D

from oasys2.widget.widget import OWWidget, OWAction
from oasys2.widget import gui as oasysgui
from oasys2.widget.util import congruence

from oasys2.widget.util.widget_objects import OasysSurfaceData
import oasys2.widget.util.widget_util as OU
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

class OWSurfaceFileReader(OWWidget):
    name = "Surface File Reader"
    id = "surface_file_reader"
    description = "Surface File Reader"
    icon = "icons/surface_reader.png"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 3
    category = ""
    keywords = ["surface_file_reader"]

    class Outputs:
        surface_data = Output("Surface Data", OasysSurfaceData, default=True, auto_summary=False)

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 618

    xx = None
    yy = None
    zz = None

    surface_file_name = Setting('surface.hdf5')

    negate = Setting(0)

    def __init__(self):
        super().__init__()

        self.readaction = OWAction("Read Surface", self)
        self.readaction.triggered.connect(self.read_surface)
        self.addAction(self.readaction)

        self.renderaction = OWAction("Render Surface", self)
        self.renderaction.triggered.connect(self.render_surface)
        self.addAction(self.renderaction)

        geom = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Read Surface", callback=self.read_surface)
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Render Surface", callback=self.render_surface)
        button.setFixedHeight(45)

        input_box_l = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="vertical", height=self.TABS_AREA_HEIGHT)

        box = oasysgui.widgetBox(input_box_l, "", addSpace=False, orientation="horizontal")

        self.le_surface_file_name = oasysgui.lineEdit(box, self, "surface_file_name", "Surface File Name",
                                                        labelWidth=120, valueType=str, orientation="horizontal")

        gui.button(box, self, "...", callback=self.selectSurfaceFile)

        gui.comboBox(input_box_l, self, "negate", label="Invert Surface", labelWidth=350,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        self.figure = Figure(figsize=(600, 600))
        self.figure.patch.set_facecolor('white')

        self.axis = self.figure.add_subplot(111, projection='3d')

        self.axis.set_zlabel("Z [m]")

        self.figure_canvas = FigureCanvas3D(ax=self.axis, fig=self.figure)

        self.mainArea.layout().addWidget(self.figure_canvas)

        gui.rubber(self.mainArea)

    def read_surface(self):
        try:
            self.surface_file_name = congruence.checkDir(self.surface_file_name)

            xx, yy, zz = OU.read_surface_file(self.surface_file_name)
            zz = zz if self.negate==0 else -1.0*zz

            self.xx = xx
            self.yy = yy
            self.zz = zz

            self.Outputs.surface_data.send(OasysSurfaceData(xx=self.xx, yy=self.yy, zz=self.zz, surface_data_file=self.surface_file_name))
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def render_surface(self):
        try:
            self.surface_file_name = congruence.checkDir(self.surface_file_name)

            xx, yy, zz = OU.read_surface_file(self.surface_file_name)
            zz = zz if self.negate==0 else -1.0*zz

            self.xx = xx
            self.yy = yy
            self.zz = zz

            self.axis.clear()

            x_to_plot, y_to_plot = numpy.meshgrid(self.xx, self.yy)

            self.axis.plot_surface(x_to_plot, y_to_plot, zz,
                                   rstride=1, cstride=1, cmap=cm.autumn, linewidth=0.5, antialiased=True)

            self.axis.set_xlabel("X [m]")
            self.axis.set_ylabel("Y [m]")
            self.axis.set_zlabel("Z [m]")
            self.axis.mouse_init()

            self.figure_canvas.draw()

            self.Outputs.surface_data.send(OasysSurfaceData(xx=self.xx, yy=self.yy, zz=self.zz, surface_data_file=self.surface_file_name))

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def selectSurfaceFile(self):
        self.le_surface_file_name.setText(oasysgui.selectFileFromDialog(self, self.surface_file_name, "Select Input File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)"))

add_widget_parameters_to_module(__name__)
