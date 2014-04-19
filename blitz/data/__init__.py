import sys

__author__ = 'Will Hart'

from collections import OrderedDict


class DataContainer(object):
    """
    A class for saving and managing data that can be used in the interface.  It
    also provides an interface for adding DataTransform objects which can be used
    to apply filters (i.e. moving average, multiplication, etc) to the data

    :param persistent: Indicates if all data is kept, (True) or only 200 values for each series (False, default)
    """

    MAX_VALUES = 50

    def __init__(self, persistent=False):
        self.__series = OrderedDict()
        self.__series_names = {}
        self.number_of_series = 0
        self.x = []
        self.y = []
        self.__transforms = []
        self.x_transformed = []
        self.y_transformed = []
        self.__persistent = persistent

    def clear_data(self):
        """
        Clears all data from the data DataContainer
        :returns: Nothing
        """
        self.__series = OrderedDict()
        self.x = []
        self.y = []
        self.__series_names = {}
        self.number_of_series = 0
        self.__transforms = []

        self.x_transformed = []
        self.y_transformed = []

    def push(self, series_id, series_name, x, y):
        """
        Adds the passed X and Y values to the given series.  If the series has not been
        registered with the DataContainer it registers it

        :param series_id: The ID of the series
        :param series_name: The human readable name of the series
        :param x: the list of x-values to add
        :param y: the list of y-values to add

        :throws ValueError: if the x and y lists are of different lengths
        :returns bool: True if the series was created, false if data was appended
        """

        if len(x) != len(y):
            raise ValueError("X and Y lists must have the same number of elements")

        created = False

        # force the series ID to string
        series_id = str(series_id)

        if series_id not in self.__series.keys():
            self.__series[series_id] = self.number_of_series
            self.__series_names[series_id] = series_name
            self.x.append([])
            self.y.append([])
            self.number_of_series += 1
            created = True

        idx = self.__series[str(series_id)]
        self.x[idx] += x
        self.y[idx] += y

        if not self.__persistent:
            self.x[idx] = self.x[idx][-self.MAX_VALUES:]
            self.y[idx] = self.y[idx][-self.MAX_VALUES:]

        return created

    def get_name(self, series_id):
        """
        Returns the name of a series in the DataContainer with the given series ID

        :param series_id: the series name to return

        :returns: The name of the series if it is in the Container, otherwise the series ID
        """
        return self.__series_names[series_id].replace("_", " ").title() \
            if series_id in self.__series_names.keys() else series_id

    def all_series(self):
        """
        A generator which yields the series x, y values
        :returns: generated [x, y] value lists
        """
        for key in self.__series.keys():
            idx = self.__series[key]
            yield [key, self.x[idx], self.y[idx]]

    def get_latest(self, named=False):
        """
        Gets the latest readings for each variable type and returns them in a pair of variable name / value pairs

        :param named: If False (default), the variables will be indexed by variable name, otherwise by series name
        :returns: A list of tuples.  Each tuple is in the form `(variable_name, value)`
        """
        result = []
        for k in self.__series.keys():
            val = self.y[self.__series[k]][-1]
            if named:
                k = self.get_name(k)

            result.append((k, val))

        return result

    def get_x(self, series_id):
        """
        Gets a list of x-values for a specified series_name

        :param series_id: the string name of the series to retrieve
        :returns: a list of x values if the key is found, an empty list otherwise
        """
        try:
            idx = self.__series[str(series_id)]
        except KeyError:
            return []

        return self.x[idx]

    def get_y(self, series_id):
        """
        Gets a list of y-values for a specified series_name

        :param series_id: the string name of the series to retrieve
        :returns: a list of y values if the key is found, an empty list otherwise
        """
        try:
            idx = self.__series[str(series_id)]
        except KeyError:
            return []

        return self.y[idx]

    def get_series(self, series_id):
        """
        Gets a single series and returns a list of [x,y] values

        :param series_id: The name of the series to return
        :returns: A list of [x,y] values for the given series, or empty lists if the series doesn't exist
        """

        if series_id not in self.__series.keys():
            return [[], []]
        else:
            idx = self.__series[series_id]
            return [self.x[idx], self.y[idx]]

    def get_transformed_series(self, series_id):
        """
        Gets a single series and returns a list of [x,y] values from the transformed data

        :param series_id: The name of the series to return
        :returns: A list of [x,y] values for the given series, or empty lists if the series doesn't exist
        """
        if series_id not in self.__series.keys() or not self.x_transformed:
            return [[], []]
        else:
            idx = self.__series[series_id]
            return [self.x_transformed[idx], self.y_transformed[idx]]

    def get_series_index(self, series_id):
        """
        Gets the index for a given series, or returns None if the series is not found

        :param series_id: The name of the series to find the index for
        :returns: An integer representing the 0 based index of this series name in the series dictionary
        """
        try:
            return self.__series[series_id]
        except KeyError:
            return None

    def has_series(self, series_id):
        """
        Checks is the given series name is registered in the DataContainer

        :param series_id: The name of the series to check (will be converted to string)
        :returns: True if the series exists, false otherwise
        """
        return str(series_id) in self.__series.keys()

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
        self.x_transformed = [data[:] for data in self.x]
        self.y_transformed = [data[:] for data in self.y]

        for transform in self.__transforms:
            transform.apply(self)

    def get_transforms(self):
        """
        Gets all the current transforms applied

        :returns: A list of BaseDataTransform classes
        """
        return self.__transforms

    def empty(self):
        """
        Checks if a DataContainer is empty.  An empty data container has no
        data series.  A container with data series but no data values is NOT empty

        :returns: True if there are no data series, False otherwise
        """
        return len(self.__series.keys()) == 0


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
