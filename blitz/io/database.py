__author__ = 'Will Hart'

from blitz.data.models import *
from blitz.data.fixtures import *

import datetime
import sqlalchemy as sql
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

    def create_tables(self, force_drop=False):
        """
        Uses the supplied engine and models to create the required table structure
        """
        #SQL_BASE is defined in blitz.data.models
        if force_drop:
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
        return self.find(model, query).first()

    def get_by_id(self, model, model_id):
        """
        Gets an object by ID
        """
        return self.get(model, {"id": model_id})

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
            order_by(Reading.id). \
            all()
        for c, r in qry:
            res.add(c)

        return list(res)

    def get_cache_variables(self):
        """
        Gets the variables associated with the cache
        """
        res = set()
        qry = self._session().query(Category, Cache).filter(Category.id == Cache.categoryId).order_by(Cache.id).all()
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
            if since:
                qry = sess.query(Cache).filter(Cache.categoryId == v.categoryId).filter(
                    Cache.timeLogged >= dt).order_by(Cache.timeLogged.desc())
            else:
                qry = sess.query(Cache).filter(Cache.categoryId == v.categoryId).order_by(Cache.timeLogged.desc())

            res += qry[:50]

        return res

    def load_fixtures(self):
        """
        Loads fixtures from blitz.data.fixtures
        """
        self.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.add_many(generate_objects(Cache, CACHE_FIXTURES))
        self.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.add_many(generate_objects(Reading, READING_FIXTURES))
        self.add_many(generate_objects(Session, SESSION_FIXTURES))


class DatabaseServer(object):
    pass
