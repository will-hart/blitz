__author__ = 'Will Hart'

import logging
import sqlalchemy as sql
from sqlalchemy.orm import sessionmaker
import redis

from blitz.data.models import *
from blitz.data.fixtures import *
import blitz.communications.signals as sigs
from blitz.utilities import blitz_timestamp


class DatabaseClient(object):
    """
    Provides database operations for the client using SqlAlchemy
    """

    _database = None
    _baseClass = None
    logger = logging.getLogger(__name__)

    def __init__(self, verbose=False, path=":memory:"):
        """
        Instantiates a connection and creates an in memory database by default.

        :param verbose: if True, SqlAlchemy will emit verbose debug messages (default False)
        :param path: the path to the database file (default ":memory:")
        """

        # allow loading from memory for testing
        self._database = sql.create_engine('sqlite:///' + path, echo=verbose)
        self._session = sessionmaker(bind=self._database)
        self.logger.debug("DatabaseClient __init__")
        self.create_tables()
        self.logger.debug("DatabaseClient created tables")

        # connect up the session_list_update signal
        sigs.client_session_list_updated.connect(self.update_session_list)

    def create_tables(self, force_drop=False):
        """
        Uses the supplied engine and models to create the required table structure

        :param force_drop: forces the existing tables to be dropped and recreated if True (default False)
        :return: nothing
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

        :param items: A list of Model instances to be added
        :returns: The list of items that was added (should now be populated with IDs)
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

    def update_session_availability(self, session_id):
        """
        Updates a session information after a download to determine if it is available for viewing.

        :param session_id: the ref_id of the session being checked
        :returns: nothing
        """
        sess = self._session()
        session = self.get(Session, {"ref_id": session_id})
        count = self._session().query(sql.exists().where(Reading.sessionId == session_id)).scalar()

        # check all lines were received and set "available" accordingly
        session.available = count > 0
        sess.commit()

    def get_session_variables(self, session_id):
        """
        Gets the variables associated with a given session
        :param session_id: the ref_id of the session to get variables for.
        :returns: a list of Reading objects
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

        :returns: a list of Cache objects
        """
        res = set()
        qry = self._session().query(Category, Cache).filter(Category.id == Cache.categoryId).order_by(Cache.id).all()
        for c, r in qry:
            res.add(c)
        return list(res)

    def get_session_readings(self, session_id):
        """
        Gets a list of readings for a particular session

        :param session_id: the ref_id of the session to get variables for.
        :returns: a list of Reading objects for the session ID
        """
        sess = self._session()
        return sess.query(Reading).filter(Reading.sessionId == session_id).all()

    def get_cache(self, since=0):
        """
        Gets cached variables. If a "since" argument is applied, it only
        returns values that have been read since this time.  If no since
        value is applied then it returns the most recent.  All queries are
        limited to 50 values per variable

        :param since: a UNIX timestamp to retrieve values since
        :returns: A list (variable) of lists (values)
        """

        res = []
        sess = self._session()

        # get the categories in the cache
        cache_vars = sess.query(Cache).group_by(Cache.categoryId).all()

        # loop and build the variables
        for v in cache_vars:
            if since > 0:
                qry = sess.query(Cache).filter(Cache.categoryId == v.categoryId).filter(
                    Cache.timeLogged >= since).order_by(Cache.timeLogged.desc())
            else:
                qry = sess.query(Cache).filter(Cache.categoryId == v.categoryId).order_by(Cache.timeLogged.desc())

            res += qry[:50]

        return res

    def update_session_list(self, sessions_list):
        """
        Session list comes in [session_id, start_timestamp, end_timstamp] format
        This replaces the existing session list

        :param sessions_list: a list of lists containing session information [id, timeStarted, timeStopped, numberOfReadings]
        :returns: nothing
        """
        self.logger.debug("Updating session list")

        sess = self._session()
        sess.query(Session).delete()
        sess.commit()

        sessions = []

        for session in sessions_list:

            count = self._session().query(sql.exists().where(Reading.sessionId == session[0])).scalar()
            blitz_session = Session()
            blitz_session.ref_id = session[0]
            blitz_session.timeStarted = session[1]
            blitz_session.timeStopped = session[2]
            blitz_session.numberOfReadings = session[3]
            blitz_session.available = count > 0
            sessions.append(blitz_session)

        self.add_many(sessions)

    def load_fixtures(self, testing=False):
        """
        Loads fixtures from blitz.data.fixtures

        :param testing: if True all fixtures are added, otherwise just configuration
        :returns: nothing
        """
        for config in CONFIG_FIXTURES:
            self.set_config(config['key'], config['value'], False)

        if testing:
            self.add_many(generate_objects(Category, CATEGORY_FIXTURES))
            self.add_many(generate_objects(Cache, CACHE_FIXTURES))
            self.add_many(generate_objects(Reading, READING_FIXTURES))
            self.add_many(generate_objects(Session, SESSION_FIXTURES))

    def get_config(self, key):
        """
        Gets a config value from the database from the given key

        :param key: the config key to retrieve
        :returns: the Config item matching the given key
        """
        return self.get(Config, {"key": key})

    def set_config(self, key, value, do_update=True):
        """
        Sets a config value in the database, adding or updating as required

        :param key: the config key to set
        :param value: the config value to set for the given key
        :returns: nothing
        """
        config = self.get_config(key)

        if config is None:
            self.add(Config(key=key, value=value))
        elif do_update:
            config.value = value
            self._session().commit()

    def get_or_create_category(self, key):
        """
        Gets the id of a category, or if none is found, create it
        and return the ID of the created object

        :param key: the category name to get or create
        :returns: the id of the Category that was retrieved or added
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

        :param description: the description of the error
        :param severity: the severity of the error (defaults to 1)
        :returns: the Notification that was added
        """
        notification = Notification(
            timeLogged=blitz_timestamp(),
            severity=severity,
            description=description
        )

        self.add(notification)
        return notification

    def clear_errors(self):
        """
        Removes all errors from the database

        :returns: nothing
        """
        sess = self._session()
        sess.query(Notification).delete()
        sess.commit()

    def handle_error(self, err_id):
        """
        Removes a single error from the database

        :returns: nothing
        """
        sess = self._session()
        sess.query(Notification).filter(Notification.id == err_id).delete()
        sess.commit()

    def add_reading(self, session_id, time_logged, category_id, value):
        """
        Quick helper to add a reading record to the database

        :param session_id: the ID of the session to create the reading for
        :param time_logged: the timestamp the reading was logged
        :param category_id: the ID of the category this reading should be added to
        :param value: the value of the reading
        :returns: the Reading that was generated
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

        :param time_logged: the timestamp the reading was logged
        :param category_id: the ID of the category this reading should be added to
        :param value: the value of the reading
        :returns: the Reading that was generated
        """
        cache = Cache(
            timeLogged=time_logged,
            categoryId=category_id,
            value=value
        )
        self.add(cache)
        return cache

    def clear_cache(self):
        """
        Clears all variables from the cache

        :returns: the Reading that was generated
        """
        sess = self._session()
        sess.query(Cache).delete()
        sess.commit()

    def clear_session_data(self, session_id):
        """
        Clears historic session data for the given session (ref) id

        :param session_id: the id of the session to clear data for
        :returns: the Reading that was generated
        """
        sess = self._session()
        sess.query(Reading).filter(Reading.sessionId == session_id).delete()
        sess.commit()


class DatabaseServer(object):
    """
    The redis database server - retains several documents:

    - **session**  the id of the current session
    - **session_N_start**  the timestamp when the logging session N began
    - **session_N_end**  the timestamp when logging session N ended
    - **sessions**  a list of session in the database
    - **session_N**  a queue of raw session data for session_id N
    """

    __data = redis.StrictRedis()
    session_id = -1

    logger = logging.getLogger(__name__)

    def __init__(self):
        """
        Initialises a new instance of a DatabaseServer
        """
        self.logger.debug("DatabaseServer __init__")
        self.session_id = self.__get_session_id()

    def start_session(self):
        """
        Starts a new session, creating the required session_N variables

        :returns: the ID of the newly created session
        """
        self.__data.incr("session_id")
        self.session_id = self.__get_session_id()
        self.__data.lpush("sessions", self.session_id)
        self.__data.set("session_" + str(self.session_id) + "_start", blitz_timestamp())
        return self.__get_session_id()

    def stop_session(self):
        """
        Stops the current session

        :returns: nothing
        """
        self.__data.set("session_" + str(self.session_id) + "_end", blitz_timestamp())
        self.session_id = -1

    def __get_session_id(self):
        sess_id = self.__data.get("session_id")
        return int(sess_id) if sess_id is not None else -1

    def get_ten_from_session(self):
        """
        Gets the last ten readings from the logging session

        :returns: the list of raw serial messages
        """
        session_str = "session_" + str(self.session_id)
        result = self.__data.lrange(session_str, 0, 9)  # numbers are inclusive
        result.reverse()
        return result

    def queue(self, message):
        """
        Queues a new message against the current session. If no session is being run then it
        logs a warning and does nothing

        :param message: the message to push onto the session data
        """

         # only log against current session
        if self.session_id == -1:
            self.logger.warning("Attempted to save a logged variable with no session running: %s" % message)
            return
        session_str = "session_%s" % self.session_id
        self.__data.lpush(session_str, message)
        return message

    def get_all_from_session(self, session_id):
        """
        Gets all messages logged during the given session ID

        :param session_id: the ID of the session to return information for
        :returns: the readings from the session
        """
        session_str = "session_" + str(session_id)
        result = self.__data.lrange(session_str, 0, -1)
        result.reverse()
        return result

    def get_latest_from_session(self, session_id):
        """
        Gets the most recent logged variable from the database and returns it as
        a raw message string.

        :param session_id: The id of the session to return the top variable from

        :returns: A string containing the last raw serial message received from a board in this session
        """
        session_str = "session_" + str(session_id)
        result = self.__data.lrange(session_str, 0, 0)

        return "" if len(result) == 0 else result[0]

    def delete_session(self, session_id):
        """
        Deletes a session and all associated data from the database. The session number
        will not be reused

        :parma session_id: the session ID to delete
        :returns: nothing
        """
        session_str = "session_" + str(session_id)
        self.__data.lrem("sessions", 1, session_id)
        self.__data.delete(session_str + "_start")
        self.__data.delete(session_str + "_end")
        self.__data.delete(session_str)

    def available_sessions(self):
        """
        Gets all the available session from the database as a list

        :returns: a list of available sessions or an empty list if there are none
        """
        result = self.__data.lrange("sessions", 0, -1)
        return [] if result is None else result

    def flush(self):
        """
        Cleans out the database

        .. warning::
            USE WITH CAUTION - this will irrevocably destroy all logged session data

        :returns: nothing
        """
        self.__data.flushdb()

    def build_client_session_list(self):
        """
        Builds a list of session information in the format::

            [
                [ID, start timestamp, end timestamp, number of readings]
                ...
            ]

        :returns: the list of sessions
        """
        sessions = self.available_sessions()
        result = []
        for session in sessions:
            session_start = self.__data.get("session_" + str(session) + "_start")
            session_end = self.__data.get("session_" + str(session) + "_end")
            session_count = self.__data.llen("session_" + str(session))
            result.append("%s %s %s %s" % (session, session_start, session_end, session_count))

        return result
