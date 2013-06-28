__author__ = 'mecharius'

import datetime
import sqlalchemy
import time
from tornado.testing import AsyncHTTPClient, AsyncHTTPTestCase
import unittest

from blitz.client import Application
from blitz.data.fixtures import *
from blitz.data.models import *
from blitz.io.database import DatabaseClient


class TestDatabaseClientSetup(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseClient()  # pass true to DatabaseClient() to get verbose logging from SQLAlchemy

    def test_variables_initialised(self):
        """
        Test that when we initialise the client a database connection is created
        """
        assert type(self.db._database) is sqlalchemy.engine.base.Engine
        assert type(self.db._session) is sqlalchemy.orm.session.sessionmaker

    def test_database_created(self):
        """
        Test that we can create a database using the built in models
        """

        # call the function which creates the table structure
        self.db.create_tables()

        # check we have the right number of tables and the correct table names
        assert(set(SQL_BASE.metadata.tables.keys()) == {"cache", "reading","category", "config", "session"})


class TestBasicDatabaseOperations(unittest.TestCase):
    """
    Test retrieve operations on the database
    """

    def setUp(self):

        # create a database
        self.db = DatabaseClient() # pass true to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables()

        # add the fixtures
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_add_one_record(self):
        c = Cache(timeLogged=datetime.datetime.now(), categoryId=1, value=3)
        res = self.db.add(c)

        assert type(res) == Cache
        assert res.id == 1

    def test_find_all_readings(self):
        res = self.db.all(Reading)
        assert(len(res) == len(READING_FIXTURES))
        for x in res:
            assert type(x) == Reading

    def test_find_one_reading(self):
        res = self.db.get(Reading, {"id": 1})
        assert(type(res) == Reading)
        assert(res.id == 1)

    def test_filter_readings(self):
        res = self.db.find(Reading, {"categoryId": 2})
        assert(res.count() == 2)
        assert(res[0].id in [3,4])
        assert(res[1].id in [3,4])
        for x in res:
            assert type(x) == Reading

    def test_find_all_categories(self):
        res = self.db.all(Category)
        assert len(res) == len(CATEGORY_FIXTURES)
        for x in res:
            assert type(x) == Category

    def test_find_one_category(self):
        res = self.db.get(Category, {"variableName": "Accelerator"})
        assert (type(res) == Category)
        assert (res.variableName == "Accelerator")

    def test_find_all_sessions(self):
        res = self.db.all(Session)
        assert len(res) == len(SESSION_FIXTURES)
        for x in res:
            assert type(x) == Session

    def test_find_one_session(self):
        res = self.db.get(Session, {"available": True})
        assert (type(res) == Session)
        assert (res.numberOfReadings == 2)

    def test_filter_sessions(self):
        res = self.db.find(Session, {"available": False})
        assert (res.count() == 1)
        assert (res[0].id == 2)
        for x in res:
            assert type(x) == Session

    def test_find_all_configs(self):
        res = self.db.all(Config)
        assert len(res) == len(CONFIG_FIXTURES)
        for x in res:
            assert type(x) == Config

    def test_find_one_config(self):
        res = self.db.get(Config, {"key": "loggerPort"})
        assert (type(res) == Config)
        assert (res.value == "8989")

    def test_get_session_by_id(self):
        res = self.db.get_by_id(Session, 2)
        assert(type(res) == Session)
        assert(res.id == 2)

    def test_empty_get_query_result(self):
        """Should return None"""
        res = self.db.get_by_id(Session, 100)
        assert res is None

        res = self.db.get(Session, {"id": 100})
        assert res is None

    def test_empty_find_query_result(self):
        res = self.db.find(Reading, {"sessionId": 4000})
        assert res.count() == 0


class TestDatabaseHelpers(unittest.TestCase):
    def setUp(self):
        # create a database
        self.db = DatabaseClient() # pass True to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables(True)

        # add the fixtures
        self.db.add_many(generate_objects(Cache, CACHE_FIXTURES))
        self.db.add_many(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add_many(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add_many(generate_objects(Reading, READING_FIXTURES))
        self.db.add_many(generate_objects(Session, SESSION_FIXTURES))

    def test_get_categories_for_session(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_session_variables(1)

        assert len(res) == 2
        assert res[0].variableName in ["Accelerator", "Brake"]
        assert res[1].variableName in ["Accelerator", "Brake"]
        assert res[0].variableName != res[1].variableName

    def test_get_categories_for_cache(self):
        """
        Test retrieving categories for a specific session
        """
        res = self.db.get_cache_variables()

        assert len(res) == 2
        assert res[0].variableName in ["Accelerator", "Brake"]
        assert res[1].variableName in ["Accelerator", "Brake"]
        assert res[0].variableName != res[1].variableName

    def test_get_readings_for_session(self):
        """
        Test retrieving readings for a given session ID
        """

        res1 = self.db.get_session_readings(2)
        assert len(res1) == 0

        res2 = self.db.get_session_readings(1)
        assert len(res2) == 4
        for x in res2:
            assert type(x) is Reading

    def test_get_cache_recent_50(self):
        """
        Test retrieving the most recent (max 50) cached variables
        """
        res = self.db.get_cache()

        # check the right number of records was returned
        assert len(res) == 4

        # check the right type of record was returned
        for x in res:
                assert type(x) == Cache

    def test_get_cache_since(self):
        """
        Test retrieving cached variables since a given time
        """
        print time2
        time2_timestamp = time.mktime(time2.timetuple()) + (float(time2.microsecond) / 1000000)
        res = self.db.get_cache(time2_timestamp)

        # check lengths
        assert len(res) == 3

        # check the types are correct
        # and double check all the dates are in range
        for x in res:
                assert type(x) == Cache
                assert x.timeLogged >= time2

    def test_config_get(self):
        res = self.db.get_config("loggerPort")
        assert res.value == "8989"

    def test_config_set(self):
        """
        Tests setting a new config item and ensure when an item
        is updated the length doesn't increase
        """
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES)

        self.db.set_config("a new key", "a val")
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES) + 1

        self.db.set_config("a new key", "another val")
        configs = self.db.all(Config)
        assert len(configs) == len(CONFIG_FIXTURES) + 1


class TestWebApi(unittest.TestCase):

    #def __init__(self, arg):
    #    """
    #     Set up the application
    #     """
    #
    #     # create an application and wait for it to start up
    #     self.app = Application()
    #     self.app.run()
    #     time.sleep(2)
    #
    #     # call the base class init
    #     super(TestWebApi, self).__init__(arg)
    #
    #def get_app(self):
    #    return self.app

    def test_get_sessions(self):
        assert False

    def test_get_session(self):
        assert False

    def test_get_config(self):
        assert False

    def test_post_config(self):
        assert False

    def test_download(self):
        assert False

    def test_cache(self):
        assert False

    def test_cache_since(self):
        assert False

