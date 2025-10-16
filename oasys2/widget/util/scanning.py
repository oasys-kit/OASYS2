import os, numpy

from AnyQt.QtWidgets import QWidget, QVBoxLayout

from oasys2.widget import gui as oasysgui
from orangewidget.gui import OWComponent

class HistogramData(object):
    scan_value = 0.0
    histogram = None
    bins = None
    offset = 0.0
    xrange = None
    fwhm = 0.0
    sigma = 0.0
    peak_intensity = 0.0
    integral_intensity = 0.0
    centroid = 0.0

    def __init__(self, histogram=None, bins=None, offset=0.0, xrange=None, fwhm=0.0, sigma=0.0, peak_intensity=0.0, integral_intensity=0.0, scan_value=0.0, centroid=0.0):
        self.histogram = histogram
        self.bins = bins
        self.offset = offset
        self.xrange = xrange
        self.fwhm = fwhm
        self.sigma = sigma
        self.peak_intensity = peak_intensity
        self.integral_intensity = integral_intensity
        self.scan_value = scan_value
        self.centroid = centroid

class HistogramDataCollection(object):

    data = None

    def __init__(self, histo_data=None):
        super().__init__()

        if not histo_data is None:
            self.add_reference_data(histo_data)

    def add_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data = self.data.flatten()
            self.data = numpy.insert(self.data, [0, int(len(self.data)/3), int(2*len(self.data)/3)], [[histo_data.scan_value]*len(histo_data.bins), histo_data.bins, histo_data.histogram])
            self.data = self.data.reshape(3, int(len(self.data)/3))

    def replace_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data[0, 0] = [histo_data.scan_value]*len(histo_data.bins)
            self.data[1, 0] = histo_data.bins
            self.data[2, 0] = histo_data.histogram

    def add_histogram_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data = numpy.append(self.data, numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]]), axis=1)

    def get_scan_values(self):
        return self.data[0, :][:, 0]

    def get_positions(self):
        return self.data[1, :]

    def get_intensities(self):
        return self.data[2, :]

    def get_histogram_data_number(self):
        return self.data.shape()[1]

    def get_scan_value(self, index):
        return self.data[0, index][0]

    def get_position(self, index):
        return self.data[1, index]

    def get_intensity(self, index):
        return self.data[2, index]

class StatisticalDataCollection(object):

    data = None

    def __init__(self, histo_data=None):
        super().__init__()

        if not histo_data is None:
            self.add_reference_data(histo_data)

    def add_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity], [histo_data.integral_intensity], [histo_data.centroid]])
        else:
            self.data = self.data.flatten()
            self.data = numpy.insert(self.data,
                                     [0, int(len(self.data)/6), int(2*len(self.data)/6), int(3*len(self.data)/6), int(4*len(self.data)/6), int(5*len(self.data)/6)],
                                     [histo_data.scan_value, histo_data.fwhm, histo_data.sigma, histo_data.peak_intensity, histo_data.integral_intensity, histo_data.centroid])
            self.data = self.data.reshape(6, int(len(self.data)/6))

    def replace_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity], [histo_data.integral_intensity], [histo_data.centroid]])
        else:
            self.data[0, 0] = histo_data.scan_value
            self.data[1, 0] = histo_data.fwhm
            self.data[2, 0] = histo_data.sigma
            self.data[3, 0] = histo_data.peak_intensity
            self.data[4, 0] = histo_data.integral_intensity
            self.data[5, 0] = histo_data.centroid

    def add_statistical_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity], [histo_data.integral_intensity], [histo_data.centroid]])
        else:
            self.data = numpy.append(self.data, numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity], [histo_data.integral_intensity], [histo_data.centroid]]), axis=1)

    def get_scan_values(self):
        return self.data[0, :]

    def get_fwhms(self):
        return self.data[1, :]

    def get_sigmas(self):
        return self.data[2, :]

    def get_centroids(self):
        return self.data[5, :]

    def get_absolute_peak_intensities(self):
        try:
            return self.data[3, :]
        except:
            return -1

    def get_absolute_integral_intensities(self):
        try:
            return self.data[4, :]
        except:
            return -1
        
    def get_relative_peak_intensities(self):
        try:
            return self.data[3, :]/self.data[3, 0]
        except:
            return -1

    def get_relative_integral_intensities(self):
        try:
            return self.data[4, :]/self.data[4, 0]
        except:
            return -1

    def get_stats_data_number(self):
        return self.data.shape()[1]

    def get_scan_value(self, index):
        return self.data[0, index]

    def get_fwhm(self, index):
        return self.data[1, index]

    def get_sigma(self, index):
        return self.data[2, index]

    def get_centroid(self, index):
        return self.data[5, index]

    def get_absolute_peak_intensity(self, index):
        return self.data[3, index]

    def get_absolute_integral_intensity(self, index):
        return self.data[4, index]

    def get_relative_peak_intensity(self, index):
        return self.data[3, index]/self.data[3, 0]

    def get_relative_integral_intensity(self, index):
        return self.data[4, index]/self.data[4, 0]

class DoublePlotWidget(QWidget, OWComponent):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)

        self.plot_canvas = oasysgui.plotWindow(roi=False, control=False, position=True, logScale=False, fit=True)
        self.plot_canvas.setFixedWidth(700)
        self.plot_canvas.setFixedHeight(520)

        self.plot_canvas.setDefaultPlotLines(True)
        self.plot_canvas.setDefaultPlotPoints(True)

        self.ax2 = self.plot_canvas._backend.ax.twinx()

        layout = QVBoxLayout()

        layout.addWidget(self.plot_canvas)

        self.setLayout(layout)

    def plotCurves(self, x, y1, y2, title, xlabel, ylabel1, ylabel2):
        self.plot_canvas._backend.ax.clear()
        self.ax2.clear()

        self.plot_canvas.addCurve(x, y1, replace=False, color="b", symbol=".", ylabel=ylabel1, linewidth=1.5)
        self.plot_canvas.setGraphXLabel(xlabel)
        self.plot_canvas.setGraphTitle(title)
        self.plot_canvas._backend.ax.set_ylabel(ylabel1, color="b")

        self.ax2.plot(x, y2, "r.-")
        self.ax2.set_ylabel(ylabel2, color="r")

import h5py

def write_histo_and_stats_file_hdf5(histo_data=HistogramDataCollection(),
                                    stats=StatisticalDataCollection(),
                                    suffix="",
                                    output_folder=""):
    file = h5py.File(os.path.join(output_folder, "variable_scan_histogram_and_statistics" + suffix + ".hdf5"), "w")

    if not histo_data is None:
        histos = file.create_group("variable_scan_histograms")

        for scan_value, positions, intensities in zip(histo_data.get_scan_values(), histo_data.get_positions(), histo_data.get_intensities()):
            histogram = histos.create_group("histogram_" + str(scan_value) + suffix)
            histogram.create_dataset("positions", data=positions)
            histogram.create_dataset("intensities", data=intensities)

    if not stats is None:
        statistics = file.create_group("statistics")

        statistics.create_dataset("scan_values", data=stats.get_scan_values())
        statistics.create_dataset("fhwm", data=stats.get_fwhms())
        statistics.create_dataset("sigma", data=stats.get_sigmas())
        statistics.create_dataset("centroid", data=stats.get_centroids())
        statistics.create_dataset("absolute_peak_intensity", data=stats.get_absolute_peak_intensities())
        statistics.create_dataset("relative_peak_intensity", data=stats.get_relative_peak_intensities())
        statistics.create_dataset("absolute_integral_intensity", data=stats.get_absolute_integral_intensities())
        statistics.create_dataset("relative_integral_intensity", data=stats.get_relative_integral_intensities())

    file.flush()
    file.close()

def write_histo_and_stats_file(histo_data=HistogramDataCollection(),
                               stats=StatisticalDataCollection(),
                               suffix="",
                               output_folder=""):
    if not histo_data is None:
        for scan_value, positions, intensities in zip(histo_data.get_scan_values(), histo_data.get_positions(), histo_data.get_intensities()):

            file = open(os.path.join(output_folder, "histogram_" + str(scan_value) + suffix + ".dat"), "w")

            for position, intensity in zip(positions, intensities):
                file.write(str(position) + "   " + str(intensity) + "\n")

            file.flush()
            file.close()

    if not stats is None:
        file_fwhm = open(os.path.join(output_folder, "fwhm" + suffix + ".dat"), "w")
        file_sigma = open(os.path.join(output_folder, "sigma" + suffix + ".dat"), "w")
        file_centroid = open(os.path.join(output_folder, "centroid" + suffix + ".dat"), "w")
        file_peak_intensity = open(os.path.join(output_folder, "intensity" + suffix + ".dat"), "w")

        file_fwhm.write("scan_value " + "   " + "fwhm" +  "\n")
        file_sigma.write("scan_value " + "   " + "sigma" +  "\n")
        file_centroid.write("scan_value " + "   " + "centroid" +  "\n")
        file_peak_intensity.write("scan_value " + "   " + "absolute_peak_intensity" + "   " + "relative_peak_intensity"
                                  + "   " + "absolute_integral_intensity" + "   " + "relative_integral_intensity" +  "\n")

        for scan_value, \
            fwhm, sigma, centroid, \
            absolute_peak_intensity, relative_peak_intensity, \
            absolute_integral_intensity, relative_integral_intensity  in zip(stats.get_scan_values(),
                                                                             stats.get_fwhms(),
                                                                             stats.get_sigmas(),
                                                                             stats.get_centroids(),
                                                                             stats.get_absolute_peak_intensities(),
                                                                             stats.get_relative_peak_intensities(),
                                                                             stats.get_absolute_integral_intensities(),
                                                                             stats.get_relative_integral_intensities()):
            file_fwhm.write(str(scan_value) + "   " + str(fwhm) + "\n")
            file_sigma.write(str(scan_value) + "   " + str(sigma) + "\n")
            file_centroid.write(str(scan_value) + "   " + str(centroid) + "\n")
            file_peak_intensity.write(str(scan_value) + "   " + str(absolute_peak_intensity) + "   " + str(relative_peak_intensity)
                                      + "   " + str(absolute_integral_intensity) + "   " + str(relative_integral_intensity) +  "\n")

        file_fwhm.flush()
        file_sigma.flush()
        file_centroid.flush()
        file_peak_intensity.flush()

        file_fwhm.close()
        file_sigma.close()
        file_centroid.close()
        file_peak_intensity.close()

