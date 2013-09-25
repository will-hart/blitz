__author__ = 'Will Hart'

from collections import OrderedDict


class DataContainer(object):
    """
`   A class for saving and managing data
    """

    def __init__(self):
        self.clear_data()

    def clear_data(self):
        """
        Clears all data from the data DataContainer
        :returns: Nothing
        """
        self.__series = OrderedDict()
        self.x = []
        self.y = []
        self.number_of_series = 0
        self.__transforms = []

    def push(self, series, x, y):
        """
        Adds the passed X and Y values to the given series.  If the series has not been
        registered with the DataContainer it registers it

        :param series: The name of the series
        :param x: the list of x-values to add
        :param y: the list of y-values to add

        :throws ValueError: if the x and y lists are of different lengths
        :returns: nothing
        """

        if len(x) != len(y):
            raise ValueError("X and Y lists must have the same number of elements")

        if str(series) not in self.__series.keys():
            self.__series[str(series)] = self.number_of_series
            self.x.append([])
            self.y.append([])
            self.number_of_series += 1

        idx = self.__series[str(series)]
        self.x[idx] += x
        self.y[idx] += y

    def all_series(self):
        """
        A generator which yields the series x, y values
        :returns: generated [x, y] value lists
        """
        for key in self.__series.keys():
            idx = self.__series[key]
            yield [key, self.x[idx], self.y[idx]]

    def get_series(self, series_name):
        """
        Gets a single series and returns a list of [x,y] values

        :param series_name: The name of the series to return
        :returns: A list of [x,y] values for the given series, or empty lists if the series doesn't exist
        """

        if series_name not in self.__series.keys():
            return [[], []]
        else:
            idx = self.__series[series_name]
            return [self.x[idx], self.y[idx]]

    def add_transform(self, transform):
        """
        Adds a data transform to the DataContainer
        """
        if not isinstance(transform, BaseDataTransform):
            raise ValueError("Attempted to add a data transformation class which doesn't derive from BaseDataTransform")

        self.__transforms.append(transform)

    def apply_transforms(self):
        """
        Applies the transformation chain
        """
        for transform in self.__transforms:
            transform.apply(self)

    def get_transforms(self):
        """
        Gets all the current transforms applied

        :returns: A list of BaseDataTransform classes
        """
        return self.__transforms


class BaseDataTransform(object):
    """
    A base class which must be inherited by DataTransform classes.
    """

    def apply(self, container):
        raise NotImplementedError("BaseDataTransform.apply should be overridden by derived instances")

