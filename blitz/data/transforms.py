__author__ = 'Will Hart'

import numpy as np

from blitz.data import BaseDataTransform


class MultiplierDataTransform(BaseDataTransform):
    """
    Applies a simple multiplier which takes a value and multiplies
    each y-value by this amount
    """
    def __init__(self, multiplier=1):
        """
        Creates a new multiplier class with the given multiplier

        :param multiplier: the value to multiply y-values by (default 1)
        """
        self.multiplier = multiplier

    def apply(self, container):
        """
        Multiplies each y value in the container by the multiplier set in __init__

        :param container: the data container to operate over
        """
        for y in container.y_transformed:
            for i in range(len(y)):
                y[i] = y[i] * self.multiplier


class MovingAverageDataTransform(BaseDataTransform):
    """
    Calculates an n-period moving average over the y data set
    """

    def __init__(self, periods):
        """
        Configures the moving average transform with a set number of average periods.
        The first n-1 numbers will be removed from the dataset

        :param periods: the number of periods to perform the moving average over
        """
        self.periods = periods

    def apply(self, container):
        """
        Applies a moving average filters using numpy
        """

        new_y_transformed = []

        for y in container.y_transformed:
            y_array = np.array(y)

            sums = np.cumsum(y_array)
            lags = np.roll(sums, self.periods)
            lags[0:self.periods] = 0
            avgs = (sums - lags) / self.periods

            new_y_transformed.append(avgs.tolist())

        # finally overwrite the existing y_transformed with new data
        container.y_transformed = new_y_transformed
