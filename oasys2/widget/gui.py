import os
import numbers
import numpy

from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import (
    QFileDialog, QMessageBox, QLabel, QTextEdit, QListWidget, QListWidgetItem,
    QTreeView, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QApplication)
from AnyQt.QtCore import pyqtSignal, QSize

from orangewidget.gui import (miscellanea, lineEdit as orange_lineEdit, widgetBox as orange_widgetBox,
                              tabWidget as orange_tabWidget, createTabPage as orange_createTabPage,
                              comboBox, button, IndicatorItemDelegate, OWComponent,
                              separator, checkBox, rubber, label, getdeepattr, connectControl, ControlledCallFront)

current_canvas_window = None

# ----------------------------------
# Default fonts
def widgetLabel(widget, label="", labelWidth=None, **misc):
    lbl = QLabel(label, widget)
    if labelWidth:
        lbl.setFixedSize(labelWidth, lbl.sizeHint().height())
    miscellanea(lbl, None, widget, **misc)

    return lbl

def lineEdit(widget, master, value, label=None, labelWidth=None,
         orientation='vertical', box=None, callback=None,
         valueType=str, validator=None, controlWidth=None,
         callbackOnType=False, focusInCallback=None,
         **misc):

    ledit = orange_lineEdit(widget, master, value, label, labelWidth, orientation, box, callback, valueType, validator, controlWidth, callbackOnType, focusInCallback, **misc)

    if value:
        if (valueType != str):
            ledit.setAlignment(Qt.AlignRight)

    ledit.setStyleSheet("background-color: white;")

    return ledit

def widgetBox(widget, box=None, orientation='vertical', margin=None, spacing=4, height=None, width=None, **misc):

    box = orange_widgetBox(widget, box, orientation, margin, spacing, **misc)
    box.layout().setAlignment(Qt.AlignTop)

    if not height is None: box.setFixedHeight(height)
    if not width is None: box.setFixedWidth(width)

    return box

def tabWidget(widget, height=None, width=None):
    tabWidget = orange_tabWidget(widget)

    if not height is None:
        tabWidget.setFixedHeight(height)
    if not width is None:
        tabWidget.setFixedWidth(width)

    tabWidget.setStyleSheet('QTabBar::tab::selected {background-color: #a6a6a6;}')

    return tabWidget

def createTabPage(tabWidget, name, widgetToAdd=None, canScroll=False, height=None, width=None, isImage=False):
    tab = orange_createTabPage(tabWidget, name, widgetToAdd, canScroll)
    tab.layout().setAlignment(Qt.AlignTop)

    if not height is None:
        tab.setFixedHeight(height)
    if not width is None:
        tab.setFixedWidth(width)

    if isImage: tab.setStyleSheet("background-color: #FFFFFF;")

    return tab

def selectSaveFileFromDialog(widget, message="Save File", default_file_name="", file_extension_filter="*.*"):
    file_path = QFileDialog.getSaveFileName(widget, message, default_file_name, file_extension_filter)[0]
    if not file_path is None and not file_path.strip() == "": return file_path
    else: return None

def selectFileFromDialog(widget, previous_file_path="", message="Select File", start_directory=os.curdir, file_extension_filter="*.*"):
    file_path = QFileDialog.getOpenFileName(widget, message, start_directory, file_extension_filter)[0]
    if not file_path is None and not file_path.strip() == "": return file_path
    else: return previous_file_path

def selectDirectoryFromDialog(widget, previous_directory_path="", message="Select Directory", start_directory=os.curdir):
    directory_path = QFileDialog.getExistingDirectory(widget, message, start_directory)
    if not directory_path is None and not directory_path.strip() == "": return directory_path
    else: return previous_directory_path

def textArea(height=None, width=None, readOnly=True, noWrap=None):
        area = QTextEdit()
        area.setReadOnly(readOnly)
        area.setStyleSheet("background-color: white;")
        if noWrap is not None:
            area.setLineWrapMode(QTextEdit.NoWrap)

        if not height is None: area.setFixedHeight(height)
        if not width is None: area.setFixedWidth(width)
    
        return area



class OasysListBox(QListWidget):
    """
    List box with drag and drop functionality. Function :obj:`listBox`
    constructs instances of this class; do not use the class directly.
    """
    def __init__(self, master, enableDragDrop=False, dragDropCallback=None,
                 dataValidityCallback=None, sizeHint=None, *args):
        """
        :param master: the master widget
        :type master: OWWidget or OWComponent
        :param enableDragDrop: flag telling whether drag and drop is enabled
        :type enableDragDrop: bool
        :param dragDropCallback: callback for the end of drop event
        :type dragDropCallback: function
        :param dataValidityCallback: callback that accepts or ignores dragEnter
            and dragMove events
        :type dataValidityCallback: function with one argument (event)
        :param sizeHint: size hint
        :type sizeHint: PyQt5.QtWidgets.QSize
        :param args: optional arguments for the inherited constructor
        """
        self.master = master
        super().__init__(*args)
        self.drop_callback = dragDropCallback
        self.valid_data_callback = dataValidityCallback
        if not sizeHint:
            self.size_hint = QSize(150, 100)
        else:
            self.size_hint = sizeHint
        if enableDragDrop:
            self.setDragEnabled(True)
            self.setAcceptDrops(True)
            self.setDropIndicatorShown(True)

    def sizeHint(self):
        return self.size_hint

    def dragEnterEvent(self, ev):
        super().dragEnterEvent(ev)
        if self.valid_data_callback:
            self.valid_data_callback(ev)
        elif isinstance(ev.source(), OasysListBox):
            ev.setDropAction(Qt.MoveAction)
            ev.accept()
        else:
            ev.ignore()

    def dropEvent(self, ev):
        ev.setDropAction(Qt.MoveAction)
        super().dropEvent(ev)

        items = self.update_master()
        if ev.source() is not self:
            ev.source().update_master(exclude=items)

        if self.drop_callback:
            self.drop_callback()

    def update_master(self, exclude=()):
        control_list = [self.item(i).data(Qt.UserRole)
                        for i in range(self.count())
                        if self.item(i).data(Qt.UserRole) not in exclude]
        if self.ogLabels:
            master_list = getattr(self.master, self.ogLabels)

            if master_list != control_list:
                setattr(self.master, self.ogLabels, control_list)
        return control_list

    def updateGeometries(self):
        # A workaround for a bug in Qt
        # (see: http://bugreports.qt.nokia.com/browse/QTBUG-14412)
        if getattr(self, "_updatingGeometriesNow", False):
            return
        self._updatingGeometriesNow = True
        try:
            return super().updateGeometries()
        finally:
            self._updatingGeometriesNow = False

CONTROLLED_ATTRIBUTES = "controlledAttributes"

class ControlledList(list):
    """
    A class derived from a list that is connected to a
    :obj:`PyQt5.QtWidgets.QListBox`: the list contains indices of items that are
    selected in the list box. Changing the list content changes the
    selection in the list box.
    """
    def __init__(self, content, listBox=None):
        super().__init__(content)
        self.listBox = listBox

    def __reduce__(self):
        # cannot pickle self.listBox, but can't discard it
        # (ControlledList may live on)
        import copyreg
        return copyreg._reconstructor, (list, list, ()), None, self.__iter__()

    # TODO ControllgedList.item2name is probably never used
    def item2name(self, item):
        item = self.listBox.labels[item]
        if type(item) is tuple:
            return item[1]
        else:
            return item

    def __setitem__(self, index, item):
        if isinstance(index, int):
            self.listBox.item(self[index]).setSelected(0)
            item.setSelected(1)
        else:
            for i in self[index]:
                self.listBox.item(i).setSelected(0)
            for i in item:
                self.listBox.item(i).setSelected(1)
        super().__setitem__(index, item)

    def __delitem__(self, index):
        if isinstance(index, int):
            self.listBox.item(self[index]).setSelected(0)
        else:
            for i in self[index]:
                self.listBox.item(i).setSelected(0)
        super().__delitem__(index)

    def append(self, item):
        super().append(item)
        item.setSelected(1)

    def extend(self, items):
        super().extend(items)
        for i in items:
            self.listBox.item(i).setSelected(1)

    def insert(self, index, item):
        item.setSelected(1)
        super().insert(index, item)

    def pop(self, index=-1):
        i = super().pop(index)
        self.listBox.item(i).setSelected(0)

    def remove(self, item):
        item.setSelected(0)
        super().remove(item)

class CallFrontListBox(ControlledCallFront):
    def action(self, value):
        if value is not None:
            if not isinstance(value, ControlledList):
                setattr(self.control.ogMaster, self.control.ogValue,
                        ControlledList(value, self.control))
            for i in range(self.control.count()):
                shouldBe = i in value
                if shouldBe != self.control.item(i).isSelected():
                    self.control.item(i).setSelected(shouldBe)

class CallFrontListBoxLabels(ControlledCallFront):
    unknownType = None

    def action(self, values):
        self.control.clear()
        if values:
            for value in values:
                if isinstance(value, tuple):
                    text, icon = value
                    item = QListWidgetItem(icon, text)
                else:
                    item = QListWidgetItem(value)

                item.setData(Qt.UserRole, value)
                self.control.addItem(item)

class CallBackListBox:
    def __init__(self, control, widget):
        self.control = control
        self.widget = widget
        self.disabled = 0

    def __call__(self, *_):  # triggered by selectionChange()
        if not self.disabled and self.control.ogValue is not None:
            clist = getdeepattr(self.widget, self.control.ogValue)
            # skip the overloaded method to avoid a cycle
            list.__delitem__(clist, slice(0, len(clist)))
            control = self.control
            for i in range(control.count()):
                if control.item(i).isSelected():
                    list.append(clist, i)
            self.widget.__setattr__(self.control.ogValue, clist)

def listBox(widget, master, value=None, labels=None, box=None, callback=None,
            selectionMode=QListWidget.SingleSelection,
            enableDragDrop=False, dragDropCallback=None,
            dataValidityCallback=None, sizeHint=None, **misc):
    """
    Insert a list box.

    The value with which the box's value synchronizes (`master.<value>`)
    is a list of indices of selected items.

    :param widget: the widget into which the box is inserted
    :type widget: PyQt5.QtWidgets.QWidget or None
    :param master: master widget
    :type master: OWWidget or OWComponent
    :param value: the name of the master's attribute with which the value is
        synchronized (list of ints - indices of selected items)
    :type value: str
    :param labels: the name of the master's attribute with the list of items
        (as strings or tuples with icon and string)
    :type labels: str
    :param box: tells whether the widget has a border, and its label
    :type box: int or str or None
    :param callback: a function that is called when the selection state is
        changed
    :type callback: function
    :param selectionMode: selection mode - single, multiple etc
    :type selectionMode: PyQt5.QtWidgets.QAbstractItemView.SelectionMode
    :param enableDragDrop: flag telling whether drag and drop is available
    :type enableDragDrop: bool
    :param dragDropCallback: callback function on drop event
    :type dragDropCallback: function
    :param dataValidityCallback: function that check the validity on enter
        and move event; it should return either `ev.accept()` or `ev.ignore()`.
    :type dataValidityCallback: function
    :param sizeHint: size hint
    :type sizeHint: PyQt5.QtWidgets.QSize
    :rtype: OrangeListBox
    """
    if box:
        bg = widgetBox(widget, box,
                       orientation="horizontal", addToLayout=False)
    else:
        bg = widget
    lb = OasysListBox(master, enableDragDrop, dragDropCallback, dataValidityCallback, sizeHint, bg)
    lb.setSelectionMode(selectionMode)
    lb.ogValue = value
    lb.ogLabels = labels
    lb.ogMaster = master

    if value is not None:
        clist = getdeepattr(master, value)
        if not isinstance(clist, ControlledList):
            clist = ControlledList(clist, lb)
            master.__setattr__(value, clist)
    if labels is not None:
        setattr(master, labels, getdeepattr(master, labels))
        if hasattr(master, CONTROLLED_ATTRIBUTES):
            getattr(master, CONTROLLED_ATTRIBUTES)[labels] = CallFrontListBoxLabels(lb)
    if value is not None:
        setattr(master, value, getdeepattr(master, value))
    connectControl(master, value, callback, lb.itemSelectionChanged,
                   CallFrontListBox(lb), CallBackListBox(lb, master))

    misc.setdefault('addSpace', True)
    miscellanea(lb, bg, widget, **misc)
    return lb


# ------------------------------------
# UTILITY CLASS
# ------------------------------------


def _set_size(dialog, width, height):
    stylesheet_string = "QLabel{"
    if not width is None:  stylesheet_string += "min-width: " + str(width) + "px;"
    if not height is None: stylesheet_string += "min-height: " + str(height) + "px;"
    stylesheet_string += "}"
    if not (width is None and height is None): dialog.setStyleSheet(stylesheet_string)

class MessageDialog(QMessageBox):
    def __init__(self, parent, message, title=None, type="information", width=None, height=None):
        super(MessageDialog, self).__init__(parent)

        self.setStandardButtons(QMessageBox.Ok)
        if type == "information": self.setIcon(QMessageBox.Information)
        elif type == "warning":   self.setIcon(QMessageBox.Warning)
        elif type == "critical":  self.setIcon(QMessageBox.Critical)
        self.setText(message)
        if title is None: self.setWindowTitle(str(type[0]).upper() + type[1:])
        else:             self.setWindowTitle(title)
        _set_size(self, width, height)

    @classmethod
    def message(cls, parent=None, message="Message", title=None, type="information", width=None, height=None):
        MessageDialog(parent, message, title, type, width, height).exec()

class ConfirmDialog(QMessageBox):
    def __init__(self, parent, message, title, width=None, height=None):
        super(ConfirmDialog, self).__init__(parent)

        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.setIcon(QMessageBox.Question)
        self.setText(message)
        self.setWindowTitle(title)
        _set_size(self, width, height)

    @classmethod
    def confirmed(cls, parent=None, message="Confirm Action?", title="Confirm Action", width=None, height=None):
        return ConfirmDialog(parent, message, title, width, height).exec() == QMessageBox.Ok

class OptionDialog(QMessageBox):
    def __init__(self, parent, message, title, options, default, width=None, height=None):
        super(OptionDialog, self).__init__(parent)

        self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.setIcon(QMessageBox.Question)
        self.setText(message)
        self.setWindowTitle(title)
        _set_size(self, width, height)

        self.selection = default

        comboBox(widgetBox(self, "", height=40), self, label="Select Option", items=options, callback=self.set_selection, orientation="horizontal")

    def set_selection(self, index):
        self.selection = index

    @classmethod
    def get_option(cls, parent=None, message="Select Option", title="Select Option", option=["No", "Yes"], default=0, width=None, height=None):
        dlg = OptionDialog(parent, message, title, option, default, width, height)
        if dlg.exec() == QMessageBox.Ok: return dlg.selection
        else: return None

class ValueDialog(QMessageBox):
    def __init__(self, parent, message, title, default, width=None, height=None):
        super(ValueDialog, self).__init__(parent)

        self.setStandardButtons(QMessageBox.Ok)
        self.setIcon(QMessageBox.Question)
        self.setText(message)
        self.setWindowTitle(title)
        _set_size(self, width, height)

        self.value = default

        lineEdit(widgetBox(self, "", height=40), self, "value", "", orientation="horizontal")

    @classmethod
    def get_value(cls, parent=None, message="Input Value", title="Input Option", default=0, width=None, height=None):
        dlg = ValueDialog(parent, message, title, default, width, height)
        if dlg.exec() == QMessageBox.Ok: return dlg.value
        else: return None


from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import art3d

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class FigureCanvas3D(FigureCanvas):

    def __init__(self, fig, ax, show_legend=True, show_buttons=True):
        super().__init__(fig)

        if show_buttons:
            box = widgetBox(self, "", orientation="vertical")
            button(box, self, "Default View", width=100, height=35, callback=self.__default_view)
            button(box, self, "Top View",     width=100, height=35, callback=self.__top_view)
            button(box, self, "Lateral View", width=100, height=35, callback=self.__lateral_view)

        self.ax = ax
        self.size_x, self.size_y = fig.get_size_inches() * fig.dpi
        self.x_c = int(self.size_x / 2)
        self.y_c = int(self.size_y / 2)

        self.last_pos_x = self.x_c
        self.last_pos_y = self.y_c

        self.__show_legend = show_legend
        self.__add_legend()

        self.mark_default_view()

    def mark_default_view(self):
        self.__initial_azim = self.ax.azim
        self.__initial_elev = self.ax.elev

    def __default_view(self):
        self.ax.view_init(azim=self.__initial_azim, elev=self.__initial_elev)
        self.draw()

    def __top_view(self):
        self.ax.view_init(azim=0.0, elev=90.0)
        self.draw()

    def __lateral_view(self):
        self.ax.view_init(azim=0.0, elev=0.0)
        self.draw()

    def __add_legend(self):
        if self.__show_legend:
            self.ax.text2D(0.05, 0.95,
                           "Mouse Left Button -> Click and Hold: Rotate\n" +  #, Double Click: Recenter\n" + \
                           "Mouse Right Button -> Click and Hold: Zoom\n" +
                           "Mouse Left & Right Buttons or Central Button -> Click and Hold: Shift",
                           transform=self.ax.transAxes,
                           color='blue')

    def __pan(self, dx, dy):
        # convert dx dy -> dxx dyy dzz
        minx, maxx, miny, maxy, minz, maxz = self.ax.get_w_lims()
        elev, azim = numpy.deg2rad(self.ax.elev), numpy.deg2rad(self.ax.azim)
        dxe = (dy / self.size_y) * numpy.sin(elev)
        dye = - (dx / self.size_x)
        dze = - (dy / self.size_y) * numpy.cos(elev)
        dxx = (maxx - minx) * (dxe * numpy.cos(azim) - dye * numpy.sin(azim))
        dyy = (maxy - miny) * (dye * numpy.cos(azim) + dxe * numpy.sin(azim))
        dzz = (maxz - minz) * (dze)
        # pan
        self.ax.set_xlim3d(minx + dxx, maxx + dxx)
        self.ax.set_ylim3d(miny + dyy, maxy + dyy)
        self.ax.set_zlim3d(minz + dzz, maxz + dzz)
        self.ax.get_proj()

    def __zoom(self, dy):
        minx, maxx, miny, maxy, minz, maxz = self.ax.get_w_lims()
        df = 1 - ((self.size_y - dy) / self.size_y)
        dx = (maxx - minx) * df
        dy = (maxy - miny) * df
        dz = (maxz - minz) * df
        self.ax.set_xlim3d(minx - dx, maxx + dx)
        self.ax.set_ylim3d(miny - dy, maxy + dy)
        self.ax.set_zlim3d(minz - dz, maxz + dz)
        self.ax.get_proj()

    def __rotate(self, dx, dy):
        self.ax.view_init(azim=art3d._norm_angle(self.ax.azim - (dx / self.size_x) * 180),
                          elev=art3d._norm_angle(self.ax.elev - (dy / self.size_y) * 180))

    def mouseMoveEvent(self, event):
        pos_x = event.pos().x() - self.x_c
        pos_y = -(event.pos().y() - self.y_c)

        dx = pos_x - self.last_pos_x
        dy = pos_y - self.last_pos_y

        if dx == 0 and dy == 0: return

        if   event.buttons() == Qt.MouseButton.LeftButton: self.__rotate(dx, dy) # left button
        elif event.buttons() == Qt.MouseButton.RightButton:        self.__zoom(dy) # right button
        elif event.buttons() == Qt.MouseButton.MiddleButton or\
             event.buttons() == (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self.__pan(dx, dy) #central button/wheel or left and right together

        self.last_pos_x = pos_x
        self.last_pos_y = pos_y

        self.draw()

    def clear_axis(self):
        self.ax.clear()
        self.__add_legend()

class UniformHeightDelegate(QStyledItemDelegate):
    """
    Item delegate that always includes the icon size in the size hint.
    """
    def sizeHint(self, option, index):
        # type: (QStyleOptionViewItem, QModelIndex) -> QSize
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        opt.features |= QStyleOptionViewItem.HasDecoration
        widget = option.widget
        style = widget.style() if widget is not None else QApplication.style()
        sh = style.sizeFromContents(QStyle.CT_ItemViewItem, opt, QSize(), widget)
        return sh

class NumericalDelegate(UniformHeightDelegate):
    def initStyleOption(self, option, index):
        # type: (QStyleOptionViewItem, QModelIndex) -> None
        super().initStyleOption(option, index)
        data = index.data(Qt.DisplayRole)
        align = index.data(Qt.TextAlignmentRole)
        if align is None and isinstance(data, numbers.Number):
            option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter

class UniformHeightIndicatorDelegate(UniformHeightDelegate, IndicatorItemDelegate):
    pass

class TreeView(QTreeView, OWComponent):
    pass

class TreeViewWithReturn(QTreeView, OWComponent):
    returnPressed = pyqtSignal()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Return: self.returnPressed.emit()
        else:                        super().keyPressEvent(e)

#######################################################################
#######################################################################
#######################################################################
# FIXING BUG ON MATPLOTLIB 2.0.0
#######################################################################
#######################################################################
#######################################################################

from silx.gui.plot.PlotWindow import PlotWindow
'''
from silx.gui.plot.backends.BackendMatplotlib import BackendMatplotlibQt
class OasysBackendMatplotlibQt(BackendMatplotlibQt):

    def __init__(self, plot, parent=None):
        super().__init__(plot, parent)

    def _onMouseMove(self, event):
        try:
            super(OasysBackendMatplotlibQt, self)._onMouseMove(event)
        except ValueError as exception:
            if "Data has no positive values, and therefore can not be log-scaled" in str(exception):
                pass
            else:
                raise exception
'''

def plotWindow(parent=None, backend=None,
               resetzoom=True, autoScale=True, logScale=True, grid=True,
               curveStyle=True, colormap=True,
               aspectRatio=True, yInverted=True,
               copy=True, save=True, print_=True,
               control=False, position=False,
               roi=True, mask=True, fit=False):
    #if backend is None:
    #    backend = OasysBackendMatplotlibQt

    plot_window = PlotWindow(parent=parent, backend=backend,
                      resetzoom=resetzoom, autoScale=autoScale, logScale=logScale, grid=grid,
                      curveStyle=curveStyle, colormap=colormap,
                      aspectRatio=aspectRatio, yInverted=yInverted,
                      copy=copy, save=save, print_=print_,
                      control=control, position=position,
                      roi=roi, mask=mask, fit=fit)

    plot_window._backend.ax.ticklabel_format(axis='y', style='sci')

    return plot_window

from silx.gui.plot import ImageView, PlotToolButtons
import silx.gui.qt as qt

def imageWiew(parent=None):
    image_view = ImageView(parent=parent)
    image_view._toolbar.setVisible(False)

    image_view.removeToolBar(image_view.profile)

    def _createToolBar(image_view, title, parent):
        image_view.keepDataAspectRatioButton = PlotToolButtons.AspectToolButton(parent=image_view, plot=image_view)
        image_view.keepDataAspectRatioButton.setVisible(True)

        image_view.yAxisInvertedButton = PlotToolButtons.YAxisOriginToolButton(parent=image_view, plot=image_view)
        image_view.yAxisInvertedButton.setVisible(True)

        toolbar = qt.QToolBar(title, parent)

        objects = image_view.group.actions()
        index = objects.index(image_view.colormapAction)
        objects.insert(index + 1, image_view.keepDataAspectRatioButton)
        objects.insert(index + 2, image_view.yAxisInvertedButton)

        for obj in objects:
            if isinstance(obj, qt.QAction):
                toolbar.addAction(obj)
            else:
                if obj is image_view.keepDataAspectRatioButton:
                    image_view.keepDataAspectRatioAction = toolbar.addWidget(obj)
                elif obj is image_view.yAxisInvertedButton:
                    image_view.yAxisInvertedAction = toolbar.addWidget(obj)
                else:
                    raise RuntimeError()

        return toolbar

    image_view._toolbar = _createToolBar(image_view, title='Plot', parent=image_view)
    image_view.insertToolBar(image_view._interactiveModeToolBar, image_view._toolbar)

    image_view.addToolBar(image_view.profile)
    image_view.getProfileToolBar().setVisible(True)

    return image_view


class Styles:
    button_blue         = "color: darkblue; font-weight: bold; height: 45px;"
    button_red          = "color: darkred; font-weight: bold; font-style: italic; height: 45px;"
    line_edit_read_only = "color: darkblue; background-color: rgb(243, 240, 160); font-weight: bold;"
