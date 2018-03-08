from kivy.uix.image import Image
from kivy.properties import NumericProperty
from kivy.clock import Clock
import cv2
from cv2 import cv
import numpy as np
from kivy.logger import Logger
from kivy.garden.graph import Graph, MeshLinePlot, MeshStemPlot

# import matplotlib
# matplotlib.use('module://kivy.garden.matplotlib.backend_kivy')
# from matplotlib import pyplot as plt
# from matplotlib.figure import Figure
# from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
import sys


class Histogram(Graph):
    """Implementation of a histogram kivy component for image exposure calculation.
        Based on opencv and kivy-garden graph libraries
    """

    def __init__(self, **kwargs):
        kwargs['xlabel'] = ''
        kwargs['ylabel'] = ''
        kwargs['x_ticks_minor'] = 2
        kwargs['y_ticks_minor'] = 0
        kwargs['x_ticks_major'] = 64
        kwargs['y_ticks_major'] = 0

        kwargs['x_grid_label'] = True
        kwargs['y_grid_label'] = False
        kwargs['x_grid'] = False
        kwargs['y_grid'] = False
        kwargs['xmin'] = 0
        kwargs['xmax'] = 255
        kwargs['ymin'] = 0
        kwargs['ymax'] = 1
        kwargs['padding'] = '5'

        super(Histogram, self).__init__(**kwargs)

        self.fbind('bins', self._on_bins_changed)

        self._hist_plot = MeshStemPlot()
        self.add_plot(self._hist_plot)

        self._centroid_plot = MeshStemPlot(color=[1,0,0,1])
        self.add_plot(self._centroid_plot)

    bins = NumericProperty(256)
    '''Number of bins in the histogram (8-bit / 0-255 by default)
    '''

    centroid = NumericProperty(256)
    '''Which bin is the centroid
    '''

    def calc_centroid(self, hist):
        half_hist_sum = sum(hist) / 2
        psum = 0
        for idx,val in enumerate(hist):
            psum += val
            if psum > half_hist_sum:
                return idx

    def set_data(self, image):
        # generate a histogram from a PIL image
        try:
            npImage = np.array(image)
            hist_full = cv2.calcHist([npImage], [0], None, [256], [0, 256]).ravel()
            hist_max = max(hist_full)
            self._hist_plot.points = [(x, hist_full[x] / hist_max) for x in range(0, 255)]

            centroid_bin = self.calc_centroid(hist_full)
            self.centroid = centroid_bin
            self._centroid_plot.points = [(x, hist_max if x == centroid_bin else 0) for x in range(0, 255)]


        except:
            e = sys.exc_info()[0]
            Logger.exception('Exception! %s', e)
            return None

    def _on_bins_changed(self, *largs):
        self.xmax = self.bins - 1
