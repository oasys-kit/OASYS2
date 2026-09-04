import io
import os

import numpy
import h5py

from AnyQt.QtCore import QRect
from AnyQt.QtWidgets import QApplication, QMessageBox

from orangewidget import gui
from orangewidget.settings import Setting

from oasys2.widget.widget import OWWidget
from oasys2.widget import gui as oasysgui
from oasys2.widget.util import congruence
from oasys2.canvas.util.canvas_util import add_widget_parameters_to_module

from silx.gui import qt
import silx.gui.hdf5
from silx.gui.data.DataViewerFrame import DataViewerFrame

class Hdf5TreeViewWidget(qt.QWidget):
    MAX_BYTES = 512 * 1024**2  # refuse to load in memory anything bigger

    def __init__(self, file_names=None):
        qt.QWidget.__init__(self)

        self.__files = {}  # abspath -> h5py.File backed by memory

        self.__treeview = silx.gui.hdf5.Hdf5TreeView(self)
        self.__text = qt.QTextEdit(self)
        self.__dataViewer = DataViewerFrame(self)

        vSplitter = qt.QSplitter(qt.Qt.Vertical)
        vSplitter.addWidget(self.__dataViewer)
        vSplitter.addWidget(self.__text)
        vSplitter.setSizes([10, 0])

        splitter = qt.QSplitter(self)
        splitter.addWidget(self.__treeview)
        splitter.addWidget(vSplitter)
        splitter.setStretchFactor(1, 1)

        layout = qt.QVBoxLayout()
        layout.addWidget(splitter)
        layout.setStretchFactor(splitter, 1)
        self.setLayout(layout)

        # append all files to the tree
        if not file_names is None:
            for file_name in file_names:
                self.load_file(file_name)

        self.__treeview.activated.connect(self.displayData)

    def displayData(self):
        """Called to update the dataviewer with the selected data.
        """
        selected = list(self.__treeview.selectedH5Nodes())
        if len(selected) == 1:
            # Update the viewer for a single selection
            data = selected[0]
            self.__dataViewer.setData(data)

    def load_file(self, filename):
        """Load the file into memory and insert it in the tree.

        The file on disk is closed as soon as this method returns: the tree
        stays fully navigable and the data viewable, but nothing keeps the
        file open (no lock, and it can be moved, deleted or written to).
        """
        filename = os.path.abspath(filename)

        if filename in self.__files: self.close_file(filename)

        size = os.path.getsize(filename)
        if size > self.MAX_BYTES: raise ValueError("File is %.0f MB: too big to be loaded in memory" % (size / 1024**2))

        with open(filename, "rb") as stream: buffer = io.BytesIO(stream.read()) # the file descriptor is released here
        h5_file = h5py.File(buffer, "r")                                        # "fileobj" driver: nothing left open on disk

        self.__files[filename] = h5_file

        # h5_file.filename is the repr of the BytesIO, hence the explicit label
        self.__treeview.findHdf5TreeModel().insertH5pyObject(h5_file, text=os.path.basename(filename))

        return h5_file

    def close_file(self, filename):
        h5_file = self.__files.pop(os.path.abspath(filename), None)

        if h5_file is None: return

        self.__dataViewer.setData(None)  # drop any dataset still displayed
        self.__treeview.findHdf5TreeModel().removeH5pyObject(h5_file)
        h5_file.close()                  # releases the memory buffer

    def close_all_files(self):
        for filename in list(self.__files.keys()): self.close_file(filename)

    def reload_file(self, filename):
        self.close_file(filename)

        return self.load_file(filename)

    def set_text(self, text):
        self.__text.setText(text)


class OWHDF5FileReader(OWWidget):
    name = "HDF5 File Reader"
    id = "hdf5_file_reader"
    description = "HDF5 File Reader"
    icon = "icons/hdf5.png"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 2
    category = ""
    keywords = ["hdf5_file_reader"]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 618

    hdf5_file_name = Setting('file.hdf5')

    def __init__(self):
        super().__init__()

        geom = QApplication.primaryScreen().geometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Load HDF5 file", callback=self.load_file)
        button.setFixedHeight(45)

        input_box_l = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="horizontal", height=self.TABS_AREA_HEIGHT)

        self.le_hdf5_file_name = oasysgui.lineEdit(input_box_l, self, "hdf5_file_name", "HDF5 File Name",
                                                        labelWidth=120, valueType=str, orientation="horizontal")

        gui.button(input_box_l, self, "...", callback=self.selectPlotXYFile)

        self.tree_view = Hdf5TreeViewWidget()

        self.mainArea.layout().addWidget(self.tree_view)

        gui.rubber(self.mainArea)


    def load_file(self):
        try:
            hdf5_file_name = congruence.checkDir(self.hdf5_file_name)

            self.tree_view.load_file(hdf5_file_name)
            self.tree_view.set_text("Loaded File: " + hdf5_file_name)

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def onDeleteWidget(self):
        self.tree_view.close_all_files()

        super().onDeleteWidget()

    def selectPlotXYFile(self):
        self.le_hdf5_file_name.setText(oasysgui.selectFileFromDialog(self, self.hdf5_file_name, "Select Input File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)"))


add_widget_parameters_to_module(__name__)