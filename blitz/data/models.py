__author__ = 'mecharius'

from blitz.utilities import to_blitz_date
import json
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

# set up the base model
SQL_BASE = declarative_base()


class Reading(SQL_BASE):
    """
    A model class for database readings
    """
    __tablename__ = 'reading'

    id = Column(Integer, primary_key=True)
    sessionId = Column(Integer)
    timeLogged = Column(DateTime)
    categoryId = Column(Integer, ForeignKey('category.id'))
    value = Column(String)

    category = relationship("Category", backref=backref('readings', order_by=timeLogged))

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "sessionId": self.sessionId,
            "timeLogged": to_blitz_date(self.timeLogged),
            "categoryId": self.categoryId,
            "value": self.value
        }


class Session(SQL_BASE):
    """
    A model class for representing logging session
    """
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True)
    available = Column(Boolean, default=False)
    timeStarted = Column(DateTime)
    timeStopped = Column(DateTime)
    numberOfReadings = Column(Integer)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "available": self.available,
            "timeStarted": to_blitz_date(self.timeStarted),
            "timeStopped": to_blitz_date(self.timeStopped),
            "numberOfReadings": self.numberOfReadings
        }


class Config(SQL_BASE):
    """
    A model class for representing key:value settings for the application and client application
    """
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    value = Column(String)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value
        }


class Category(SQL_BASE):
    """
    A model class for representing categories (or variables) that have been logged in the database
    """
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    variableName = Column(String, unique=True)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "variableName": self.variableName
        }


class Cache(SQL_BASE):
    """
    A model which is derived from readings and is used for storing temporary (and incomplete)
    logging data whilst a session is in progress
    """
    __tablename__ = 'cache'

    id = Column(Integer, primary_key=True)
    timeLogged = Column(DateTime)
    categoryId = Column(Integer)
    value = Column(String)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "timeLogged": to_blitz_date(self.timeLogged),
            "categoryId": self.categoryId,
            "value": self.value
        }

