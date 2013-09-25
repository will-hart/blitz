__author__ = 'Will Hart'

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
        for y in container.y:
            for i in range(len(y)):
                y[i] = y[i] * self.multiplier
