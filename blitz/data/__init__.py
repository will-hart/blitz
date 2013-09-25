import sys

__author__ = 'Will Hart'

from collections import OrderedDict


class DataContainer(object):
    """
    A class for saving and managing data that can be used in the interface.  It
    also provides an interface for adding DataTransform objects which can be used
    to apply filters (i.e. moving average, multiplication, etc) to the data
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

        self.y_min = sys.maxint
        self.y_max = - sys.maxint - 1
        self.x_min = sys.maxint
        self.x_max = - sys.maxint - 1

    def push(self, series, x, y):
        """
        Adds the passed X and Y values to the given series.  If the series has not been
        registered with the DataContainer it registers it

        :param series: The name of the series
        :param x: the list of x-values to add
        :param y: the list of y-values to add

        :throws ValueError: if the x and y lists are of different lengths
        :returns bool: True if the series was created, false if data was appended
        """

        if len(x) != len(y):
            raise ValueError("X and Y lists must have the same number of elements")

        created = False

        if str(series) not in self.__series.keys():
            self.__series[str(series)] = self.number_of_series
            self.x.append([])
            self.y.append([])
            self.number_of_series += 1
            created = True

        idx = self.__series[str(series)]
        self.x[idx] += x
        self.y[idx] += y

        self.x_min = min(min(x), self.x_min)
        self.x_max = max(max(x), self.x_max)

        self.y_min = min(min(y), self.y_min)
        self.y_max = max(max(y), self.y_max)

        return created

    def all_series(self):
        """
        A generator which yields the series x, y values
        :returns: generated [x, y] value lists
        """
        for key in self.__series.keys():
            idx = self.__series[key]
            yield [key, self.x[idx], self.y[idx]]

    def get_x(self, series_name):
        """
        Gets a list of x-values for a specified series_name

        :param series_name: the string name of the series to retrieve
        :returns: a list of x values if the key is found, an empty list otherwise
        """
        try:
            idx = self.__series[str(series_name)]
        except KeyError:
            return []

        return self.x[idx]

    def get_y(self, series_name):
        """
        Gets a list of y-values for a specified series_name

        :param series_name: the string name of the series to retrieve
        :returns: a list of y values if the key is found, an empty list otherwise
        """
        try:
            idx = self.__series[str(series_name)]
        except KeyError:
            return []

        return self.y[idx]

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

    def get_series_index(self, series_name):
        """
        Gets the index for a given series, or returns None if the series is not found

        :param series_name: The name of the series to find the index for
        :returns: An integer representing the 0 based index of this series name in the series dictionary
        """
        try:
            return self.__series[series_name]
        except KeyError:
            return None

    def has_series(self, series_name):
        """
        Checks is the given series name is registered in the DataContainer

        :param series_name: The name of the series to check (will be converted to string)
        :returns: True if the series exists, false otherwise
        """
        return str(series_name) in self.__series.keys()

    def get_series_names(self):
        """
        Returns a list of series names that are registered in this DataContainer

        :returns: A list of string series names registered to this DataContainer
        """
        return self.__series.keys()

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
        """
        Takes a DataContainer object and applies a transformation to the X and Y data in the
        DataContainer.  This is a base class which should be inherited from.

        .. warning::
            If no `apply` method is provided on the derived class then a `NotImplementedError` will be thrown

        :raises: NotImplementedError
        """
        raise NotImplementedError("BaseDataTransform.apply should be overridden by derived instances")

