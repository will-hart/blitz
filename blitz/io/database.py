__author__ = 'Will Hart'

from blitz.data.models import *

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

    def create_tables(self):
        """
        Uses the supplied engine and models to create the required table structure
        """
        #SQL_BASE is defined in blitz.data.models
        SQL_BASE.metadata.create_all(self._database)

    def add_reading(self, session_id, time_logged, variable_id, value):
        """
        Creates a new reading in the database with the passed attributes

        :param session_id: the ID of the session this variable belongs to
        :param time_logged: the DateTime that this value was logged
        :param variable_id: the integer ID of the category this variable corresponds to
        :param value: the value that was logged

        :return: returns the created reading object
        """

        new_reading = Reading(sessionId=session_id, timeLogged=time_logged, category=variable_id, value=value)
        sess = self._session()
        sess.add(new_reading)
        sess.commit()
        return new_reading


class DatabaseServer(object):
    pass
