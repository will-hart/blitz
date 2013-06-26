__author__ = 'Will Hart'

from blitz.data.models import *

import datetime
import sqlalchemy as sql
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

# create the models


class DatabaseClient(object):

    _database = None
    _baseClass = None

    def __init__(self, verbose=False):
        """
        Instantiates a connection and creates an in memory database
        """
        # TODO: load the database from the app.db file
        self._database = sql.create_engine('sqlite:///:memory:', echo=verbose)
        self._session = sessionmaker(bind=self._database)

    def create_tables(self):
        """
        Uses the supplied engine and models to create the required table structure
        """
        #SQL_BASE is defined in blitz.data.models
        SQL_BASE.metadata.drop_all(self._database)
        SQL_BASE.metadata.create_all(self._database)

    def add(self, item):
        """
        Adds a single item to the database

        :param item: The item to add to the database

        :returns: The item that was added
        """

        res = self.add_many([item])
        return res[0]

    def add_many(self, items):
        """
        Adds the given items to the database with the passed attributes

        :param items: A list of items to be added
        :return: The list of items that was added (should now be populated with IDs)
        """
        sess = self._session()
        for r in items:
            sess.add(r)
        sess.commit()
        return items

    def get(self, model, query):
        """
        Gets a single item from the database (the first that matches the query dict)

        :param model: the model to query
        :param query: the dict of "field: value" pairs to filter on

        :return: A single model matching the query string
        """
        if type(query) == int:
            # handle filtering by ID
            use_query = {"id": query}
        else:
            use_query = query
        return self.find(model, use_query).first()

    def all(self, model):
        """
        Returns all the records for a given model type

        :param model: The model to return all records for

        :return: A list of all records for a given model
        """

        sess = self._session()
        return sess.query(model).all()

    def find(self, model, query):
        """
        Returns ALL items which match the given query

        :param model: The model to query on
        :param query: the dictionary of "field: value" pairs to filter on

        :return: a list of all matching records
        """
        sess = self._session()
        return sess.query(model).filter_by(**query)

    def get_session_variables(self, session_id):
        """
        Gets the variables associated with a given session
        """
        res = set()
        qry = self._session().query(Category, Reading). \
            filter(Category.id == Reading.categoryId). \
            filter(Reading.sessionId == session_id). \
            all()
        for c, r in qry:
            res.add(c)

        return list(res)

    def get_session_readings(self, session_id):
        """
        Gets a list of readings for a particular session
        """
        sess = self._session()
        return sess.query(Reading).filter(Reading.sessionId == session_id).all()

    def get_cache(self, since=None):
        """
        Gets cached variables. If a "since" argument is applied, it only
        returns values that have been read since this time.  If no since
        value is applied then it returns the most recent.  All queries are
        limited to 50 values per variable

        :param since: a UNIX timestamp to retrieve values since

        :returns: A list (variable) of lists (values)
        """

        res = []
        dt = None
        sess = self._session()
        qry = None

        # get the categories in the cache
        cache_vars = sess.query(Cache).group_by(Cache.categoryId).all()

        # convert since to a datetime
        if since is not None:
            dt = datetime.datetime.fromtimestamp(since)

        # loop and build the variables
        for v in cache_vars:
            lst = []
            qry = sess.query(Cache).filter(Cache.categoryId == v.categoryId).order_by(Cache.timeLogged.desc())

            if since:
                qry.filter(Cache.timeLogged >= dt)

            res.append(qry[:50])

        return res

class DatabaseServer(object):
    pass
