__author__ = 'mecharius'

import datetime
import sqlalchemy
import time
import unittest

from blitz.io.database import DatabaseClient
from blitz.data.models import *

time0 = datetime.datetime.now()
time1 = datetime.datetime.now() - datetime.timedelta(seconds=1)
time2 = datetime.datetime.now() - datetime.timedelta(seconds=2)
time3 = datetime.datetime.now() - datetime.timedelta(seconds=3)
time4 = datetime.datetime.now() - datetime.timedelta(seconds=4)

READING_FIXTURES = [
    {"sessionId": 1, "timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"sessionId": 1, "timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"sessionId": 1, "timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"sessionId": 1, "timeLogged": time0, "categoryId": 2, "value": 4.3}
]

CACHE_FIXTURES = [
    {"timeLogged": time3, "categoryId": 1, "value": 3.75},
    {"timeLogged": time2, "categoryId": 1, "value": 9.12},
    {"timeLogged": time1, "categoryId": 2, "value": 5.2},
    {"timeLogged": time0, "categoryId": 2, "value": 4.3}
]

CATEGORY_FIXTURES = [
    {"variableName": "Accelerator"},
    {"variableName": "Brake"},
    {"variableName": "Third"}
]

SESSION_FIXTURES = [
    {"available": True,  "timeStarted": time4, "timeStopped": time2, "numberOfReadings": 2},
    {"available": False, "timeStarted": time2, "timeStopped": time0, "numberOfReadings": 2}
]

CONFIG_FIXTURES = [
    {"key": "loggerPort", "value": "8989"},
    {"key": "loggerIp",   "value": "192.168.1.79"},
    {"key": "clientPort", "value": "8988"},
    {"key": "clientIp",   "value": "192.168.1.79"}
]


def generate_objects(model, fixtures):
    """
    Generate a list of objects of the provided model type with the data
    given in the fixtures list of dictionaries
    """
    res = []
    for f in fixtures:
        res.append(model(**f))
    return res


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

    def test_find_one_reading(self):
        res = self.db.get(Reading, {"id": 1})
        assert(type(res) == Reading)
        assert(res.id == 1)

    def test_filter_readings(self):
        res = self.db.find(Reading, {"categoryId": 2})
        assert(res.count() == 2)
        assert(res[0].id in [3,4])
        assert(res[1].id in [3,4])

    def test_find_all_categories(self):
        res = self.db.all(Category)
        assert len(res) == len(CATEGORY_FIXTURES)

    def test_find_one_category(self):
        res = self.db.get(Category, {"variableName": "Accelerator"})
        assert (type(res) == Category)
        assert (res.variableName == "Accelerator")

    def test_find_all_sessions(self):
        res = self.db.all(Session)
        assert len(res) == len(SESSION_FIXTURES)

    def test_find_one_session(self):
        res = self.db.get(Session, {"available": True})
        assert (type(res) == Session)
        assert (res.numberOfReadings == 2)

    def test_filter_sessions(self):
        res = self.db.find(Session, {"available": False})
        assert (res.count() == 1)
        assert (res[0].id == 2)

    def test_find_all_configs(self):
        res = self.db.all(Config)
        assert len(res) == len(CONFIG_FIXTURES)

    def test_find_one_config(self):
        res = self.db.get(Config, {"key": "loggerPort"})
        assert (type(res) == Config)
        assert (res.value == "8989")

    def test_get_session_by_id(self):
        res = self.db.get(Session, 2)
        assert(type(res) == Session)
        assert(res.id == 2)


class TestDatabaseHelpers(unittest.TestCase):
    def setUp(self):
        # create a database
        self.db = DatabaseClient() # pass true to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables()

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

        assert len(res) == 4
        for x in res:
            assert type(x) == Cache

    def test_get_cache_since(self):
        """
        Test retrieving cached variables since a given time
        """
        res = self.db.get_cache(time.mktime(time2.timetuple()) + time2.microsecond / 1000000)

        assert len(res) == 3
        for x in res:
            assert type(x) == Cache
