__author__ = 'mecharius'

import datetime
import sqlalchemy
import unittest

from blitz.io.database import DatabaseClient
from blitz.data.models import *

class TestDatabaseClient(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseClient(True)

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
        print SQL_BASE.metadata.tables.keys()
        assert(set(SQL_BASE.metadata.tables.keys()) == {"reading","category", "config", "session"})

    def test_add_reading(self):
        """
        Test that we can add a reading to the database
        """

        self.db.create_tables()
        rdg = self.db.add_reading(1, datetime.datetime.now(), 1, 12)
        q_sess = self.db._session()
        q_rdg = q_sess.query(Reading).filter_by(id=rdg.id).first()

        assert(q_rdg.id == rdg.id)
        assert(q_rdg.sessionId == rdg.sessionId)
        assert(q_rdg.timeLogged == rdg.timeLogged)
        assert(q_rdg.category == rdg.category)
        assert(q_rdg.value == rdg.value)
