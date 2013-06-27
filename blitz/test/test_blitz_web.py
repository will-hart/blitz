__author__ = 'Will Hart'

from blitz.io.database import DatabaseClient
from blitz.data.fixtures import *
from blitz.data.models import *
from blitz.test.test_blitz_io import generate_objects

import json

from tornado.testing import AsyncTestCase, AsyncHTTPClient, gen_test

class ApiTestCases(AsyncTestCase):
    """
    Tests the REST API to ensure the correct JSON is returned based on the fixtures
    """

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

    def test_categories_handler(self):
        """
        Test that the categories handler returns the correct JSON
        """
        client = AsyncHTTPClient(self.io_loop)
        client.fetch("http://localhost:8989/categories", self.stop)
        response = self.wait()
        print response.body

        assert False
