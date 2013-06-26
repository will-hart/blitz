__author__ = 'mecharius'

import datetime
import sqlalchemy
import unittest

from blitz.io.database import DatabaseClient
from blitz.data.models import *


READING_FIXTURES = [
    {"sessionId": 1, "timeLogged": datetime.datetime.now() - datetime.timedelta(seconds=3), "category": 1, "value": 3.75},
    {"sessionId": 1, "timeLogged": datetime.datetime.now() - datetime.timedelta(seconds=2), "category": 1, "value": 9.12},
    {"sessionId": 1, "timeLogged": datetime.datetime.now() - datetime.timedelta(seconds=1), "category": 2, "value": 5.2},
    {"sessionId": 1, "timeLogged": datetime.datetime.now(), "category": 2, "value": 4.3}
]

CATEGORY_FIXTURES = [
    {"variableName": "Accelerator"},
    {"variableName": "Brake"}
]

SESSION_FIXTURES = [
    {"available": True,  "timeStarted": datetime.datetime.now() - datetime.timedelta(seconds=4), "timeStopped": datetime.datetime.now() - datetime.timedelta(seconds=2), "numberOfReadings": 2},
    {"available": False, "timeStarted": datetime.datetime.now() - datetime.timedelta(seconds=2), "timeStopped": datetime.datetime.now(), "numberOfReadings": 2}
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
        assert(set(SQL_BASE.metadata.tables.keys()) == {"reading","category", "config", "session"})


class TestDatabaseOperations(unittest.TestCase):
    """
    Test retrieve operations on the database
    """

    def setUp(self):

        # create a database
        self.db = DatabaseClient() # pass true to DatabaseClient() to get verbose logging from SQLAlchemy
        self.db.create_tables()

        # add the fixtures
        self.db.add(generate_objects(Category, CATEGORY_FIXTURES))
        self.db.add(generate_objects(Config, CONFIG_FIXTURES))
        self.db.add(generate_objects(Reading, READING_FIXTURES))
        self.db.add(generate_objects(Session, SESSION_FIXTURES))

    def test_find_all_readings(self):
        res = self.db.all(Reading)
        assert(len(res) == len(READING_FIXTURES))

    def test_find_one_reading(self):
        res = self.db.get(Reading, {"id": 1})
        assert(type(res) == Reading)
        assert(res.id == 1)

    def test_filter_readings(self):
        res = self.db.find(Reading, {"category": 2})
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
