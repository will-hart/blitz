__author__ = 'Will Hart'

import numpy as np

from blitz.data import BaseDataTransform


class MultiplierDataTransform(BaseDataTransform):
    """
    Applies a simple multiplier which takes a value and multiplies
    each y-value by this amount

    :param multiplier: the value to multiply y-values by (default 1)
    """
    def __init__(self, multiplier=1):
        self.multiplier = multiplier

    def apply(self, container):
        """
        Multiplies each y value in the container by the multiplier set in `__init__`

        :param container: the data container to operate over
        """

        new_y_transformed = []

        for y in container.y_transformed:
            y_array = np.array(y)
            y_array *= self.multiplier

            new_y_transformed.append(y_array.tolist())

        # finally overwrite the existing y_transformed with new data
        container.y_transformed = new_y_transformed


class MovingAverageDataTransform(BaseDataTransform):
    """
    Calculates an n-period moving average transform over the y-axis data.

    :param periods: the number of periods to perform the moving average over
    """
    def __init__(self, periods):
        self.periods = periods

    def apply(self, container):
        """
        Applies a moving average filters using numpy

        :param container: the data container to operate over
        """

        new_y_transformed = []

        for y in container.y_transformed:
            y_array = np.array(y)
            ones = np.ones(self.periods) / self.periods
            avgs = np.convolve(y_array, ones, mode='same').tolist()

            new_y_transformed.append(avgs)

        # finally overwrite the existing y_transformed with new data
        container.y_transformed = new_y_transformed


class TranslateDataTransform(BaseDataTransform):
    """
    Translates data on the y-axis based on the amount provided in `shift_amount`

    :param shift_amount: the amount to shift data by on the y-axis
    :param shift_axis: the axis to translate on (defaults to `y`, can also supply `x`)

    .. warning::
        If `shift_axis` is neither `x` nor `y`, then the translation will apply to the 'y' axis
    """

    def __init__(self, shift_amount=0, shift_axis='y'):
        self.shift_amount = shift_amount
        self.shift_axis = 'x' if shift_axis == 'x' else 'y'

    def apply(self, container):
        """
        Applies an axis translation to the data.

        :param container: the data container to operate over
        """

        new_transformed = []
        target = container.x_transformed if self.shift_axis == 'x' else container.y_transformed

        for dataset in target:
            output = np.array(dataset)
            output -= self.shift_amount
            new_transformed.append(output.tolist())

        # finally overwrite the existing y_transformed with new data
        container.y_transformed = new_transformed
