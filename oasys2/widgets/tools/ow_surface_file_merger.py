import numpy
from AnyQt.QtCore import QRect
from AnyQt.QtWidgets import QApplication, QMessageBox
from matplotlib import cm
from matplotlib.figure import Figure

from orangewidget import gui
from orangewidget.settings import Setting
from orangewidget.widget import MultiInput, Output

from oasys2.widget.gui import FigureCanvas3D
from oasys2.widget.widget import OWWidget, OWAction
from oasys2.widget import gui as oasysgui
from oasys2.widget.util.widget_objects import OasysPreProcessorData, OasysErrorProfileData, OasysSurfaceData
import oasys2.widget.util.widget_util as OU
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

class OWSurfaceFileReader(OWWidget):
    name = "Surface File Merger"
    id = "surface_file_merger"
    description = "Surface File Merger"
    icon = "icons/surface_merger.png"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 5
    category = ""
    keywords = ["surface_file_mberger"]

    class Inputs:
        surface_data = MultiInput("Surface Data", object, default=False, auto_summary=False)


    class Outputs:
        preprocessor_data = Output("PreProcessor Data", OasysPreProcessorData, default=True, auto_summary=False)
        surface_data      = Output("Surface Data", OasysSurfaceData, default=True, auto_summary=False)

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 618

    xx = []
    yy = []
    zz = []

    surface_file_name = Setting('merged_surface.hdf5')

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

        input_box_l = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="horizontal", height=self.TABS_AREA_HEIGHT)

        self.le_surface_file_name = oasysgui.lineEdit(input_box_l, self, "surface_file_name", "Surface File Name",
                                                        labelWidth=120, valueType=str, orientation="horizontal")

        gui.button(input_box_l, self, "...", callback=self.selectSurfaceFile)


        self.figure = Figure(figsize=(600, 600))
        self.figure.patch.set_facecolor('white')

        self.axis = self.figure.add_subplot(111, projection='3d')

        self.axis.set_zlabel("Z [m]")

        self.figure_canvas = FigureCanvas3D(ax=self.axis, fig=self.figure)

        self.mainArea.layout().addWidget(self.figure_canvas)

        gui.rubber(self.mainArea)


    @Inputs.surface_data
    def set_input(self, index, data):
        if not data is None:
            if isinstance(data, OasysPreProcessorData):
                self.xx[index] = data.error_profile_data.oasys_surface_data.xx
                self.yy[index] = data.error_profile_data.oasys_surface_data.yy
                self.zz[index] = data.error_profile_data.oasys_surface_data.zz
            elif isinstance(data, OasysSurfaceData):
                self.xx[index] = data.xx
                self.yy[index] = data.yy
                self.zz[index] = data.zz
            else:
                QMessageBox.critical(self, "Error",
                                     f"Data Type #{index+1} not recognized",
                                     QMessageBox.Ok)

    @Inputs.surface_data.insert
    def insert_data(self, index, data):
        if not data is None:
            if isinstance(data, OasysPreProcessorData):
                self.xx.insert(index, data.error_profile_data.oasys_surface_data.xx)
                self.yy.insert(index, data.error_profile_data.oasys_surface_data.yy)
                self.zz.insert(index, data.error_profile_data.oasys_surface_data.zz)
            elif isinstance(data, OasysSurfaceData):
                self.xx.insert(index, data.xx)
                self.yy.insert(index, data.yy)
                self.zz.insert(index, data.zz)
            else:
                QMessageBox.critical(self, "Error",
                                     f"Data Type #{index+1} not recognized",
                                     QMessageBox.Ok)
    @Inputs.surface_data.remove
    def remove_data(self, index):
        self.xx[index].pop(index)
        self.yy[index].pop(index)
        self.zz[index].pop(index)

    def compute(self, plot_data=False):
        if not self.xx is None or len(self.xx) < 2:
            try:
                xx      = None
                yy      = None
                zz      = None
                xx_prev = None
                yy_prev = None

                for xx_i, yy_i, zz_i in zip(self.xx, self.yy, self.zz):
                    if not xx_prev is None:
                        if not (len(xx_prev) == len(xx_i) and
                                len(yy_prev) == len(yy_i) and
                                round(xx_prev[0], 6) == round(xx_i[0], 6) and
                                round(xx_prev[-1], 6) == round(xx_i[-1], 6) and
                                round(yy_prev[0], 6) == round(yy_i[0], 6) and
                                round(yy_prev[-1], 6) == round(yy_i[-1], 6)):
                            raise ValueError("The two surfaces cannot be merged: dimensions or binning incompatible")

                    if xx is None: xx = xx_i
                    if yy is None: yy = yy_i
                    if zz is None: zz = zz_i
                    else:          zz += zz_i

                self.axis.clear()

                x_to_plot, y_to_plot = numpy.meshgrid(xx, yy)

                if plot_data:
                    self.axis.plot_surface(x_to_plot, y_to_plot, zz,
                                           rstride=1, cstride=1, cmap=cm.autumn, linewidth=0.5, antialiased=True)

                    self.axis.set_xlabel("X [m]")
                    self.axis.set_ylabel("Y [m]")
                    self.axis.set_zlabel("Z [m]")
                    self.axis.mouse_init()

                    self.figure_canvas.draw()

                if not (self.surface_file_name.endswith("hd5") or self.surface_file_name.endswith("hdf5") or self.surface_file_name.endswith("hdf")):
                    self.surface_file_name += ".hdf5"

                OU.write_surface_file(zz, xx, yy, self.surface_file_name)

                error_profile_x_dim = abs(xx[-1] - xx[0])
                error_profile_y_dim = abs(yy[-1] - yy[0])

                self.Outputs.preprocessor_data.send(OasysPreProcessorData(error_profile_data=OasysErrorProfileData(surface_data=OasysSurfaceData(xx=xx,
                                                                                                                   yy=yy,
                                                                                                                   zz=zz,
                                                                                                                   surface_data_file=self.surface_file_name),
                                                                          error_profile_x_dim=error_profile_x_dim,
                                                                          error_profile_y_dim=error_profile_y_dim)))
                self.Outputs.surface_data.send(OasysSurfaceData(xx=xx,
                                                                yy=yy,
                                                                zz=zz,
                                                                surface_data_file=self.surface_file_name))
            except Exception as exception:
                QMessageBox.critical(self, "Error",
                                     exception.args[0],
                                     QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception
        else:
            QMessageBox.critical(self, "Error", "Connect at least two surfaces to merge", QMessageBox.Ok)


    def read_surface(self):
        self.compute(plot_data=False)

    def render_surface(self):
        self.compute(plot_data=True)

    def selectSurfaceFile(self):
        self.le_surface_file_name.setText(oasysgui.selectFileFromDialog(self, self.surface_file_name, "Select Input File", file_extension_filter="HDF5 Files (*.hdf5)"))

add_widget_parameters_to_module(__name__)