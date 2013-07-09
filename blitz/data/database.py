__author__ = 'Will Hart'

import datetime
import logging

import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker
import redis

from blitz.data.models import *
from blitz.data.fixtures import *


class DatabaseClient(object):

    _database = None
    _baseClass = None
    logger = logging.getLogger(__name__)

    def __init__(self, verbose=False, path=":memory:"):
        """
        Instantiates a connection and creates an in memory database
        """

        # allow loading from memory for testing
        self._database = sql.create_engine('sqlite:///' + path, echo=verbose)
        self._session = sessionmaker(bind=self._database)
        self.logger.debug("DatabaseClient __init__")
        self.create_tables()
        self.logger.debug("DatabaseClient created tables")

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

    def get_config(self, key):
        """
        Gets a config value from the database from the given key
        """
        return self.get(Config, {"key": key})

    def set_config(self, key, value):
        """
        Sets a config value in the database, adding or
        """

        config = self.get_config(key)

        if config is None:
            self.add(Config(key=key, value=value))
        else:
            config.value = value
            self._session().commit()

    def get_or_create_category(self, key):
        """
        Gets the id of a category, or if none is found, create it
        and return the ID of the created object
        """
        category = self.get(Category, {"variableName": key})
        if category:
            return category.id
        else:
            new_category = Category(variableName=key)
            self.add(new_category)
        return new_category.id

    def log_error(self, description, severity=1):
        """
        Log an error to the database - this will be sent to the client
        """
        notification = Notification(
            timeLogged=datetime.datetime.now(),
            severity=severity,
            description=description
        )

        self.add(notification)
        return notification

    def clear_errors(self):
        """Removes all errors from the database"""
        self._session().query(Notification).delete()

    def handle_error(self, err_id):
        """Removes a single error from the database"""
        sess = self._session()
        sess.query(Notification).filter({"id": err_id}).delete()

    def add_reading(self, session_id, time_logged, category_id, value):
        """
        Quick helper to add a reading record to the database
        """
        reading = Reading(
            sessionId=session_id,
            timeLogged=time_logged,
            categoryId=category_id,
            value=value
        )
        self.add(reading)
        return reading

    def add_cache(self, time_logged, category_id, value):
        """
        Quick helper to add a cache record to the database
        """
        cache = Cache(
            timeLogged=time_logged,
            categoryId=category_id,
            value=value
        )
        self.add(cache)
        return cache


class DatabaseServer(object):
    """
    The redis database server - retains several documents:

    "session" - the id of the current session
    "session_start" - the timestamp when the current logging session began
    "sessions" - a list of session in the database
    "data-N" - a queue of raw session data for session_id N
    """

    __data = redis.StrictRedis()
    session_id = -1

    logger = logging.getLogger(__name__)

    def __init__(self):
        self.logger.debug("DatabaseServer __init__")
        self.session_id = self.__get_session_id()

    def start_session(self):
        self.__data.incr("session_id")
        self.session_id = self.__get_session_id()
        self.__data.lpush("sessions", self.session_id)
        self.__data.set("session_" + str(self.session_id) + "_start", datetime.datetime.now())
        return self.__get_session_id()

    def stop_session(self):
        self.__data.set("session_" + str(self.session_id) + "_end", datetime.datetime.now())
        self.session_id = -1

    def __get_session_id(self):
        sess_id = self.__data.get("session_id")
        return int(sess_id) if sess_id is not None else -1

    def get_ten_from_session(self):
        session_str = "session_" + str(self.session_id)
        result = self.__data.lrange(session_str, 0, 9)  # numbers are inclusive
        result.reverse()
        return result

    def queue(self, message):
         # only log against current session
        if self.session_id == -1:
            self.logger.warning("Attempted to save a logged variable with no session running: %s" % message)
            return
        session_str = "session_%s" % self.session_id
        self.__data.lpush(session_str, message)
        return message

    def get_all_from_session(self, session_id):
        session_str = "session_" + str(session_id)
        result = self.__data.lrange(session_str, 0, -1)
        result.reverse()
        return result

    def delete_session(self, session_id):
        session_str = "session_" + str(session_id)
        self.__data.lrem("sessions", 1, session_id)
        self.__data.delete(session_str + "_start")
        self.__data.delete(session_str + "_end")
        return self.__data.delete(session_str)

    def available_sessions(self):
        result = self.__data.lrange("sessions", 0, -1)
        return [] if result is None else result

    def flush(self):
        """Cleans out the database - no save or undo, USE WITH CAUTION"""
        self.__data.flushdb()
