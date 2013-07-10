__author__ = 'mecharius'

import json

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref

# set up the base model
SQL_BASE = declarative_base()


class Notification(SQL_BASE):
    """
    A model class for database notifications to send to the client
    """
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    timeLogged = Column(Integer)
    severity = Column(Integer)
    description = Column(String)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "timeLogged": float(self.timeLogged),
            "severity": self.severity,
            "description": self.description
        }

    def __str__(self):
        return json.dumps(self.to_dict())


class Reading(SQL_BASE):
    """
    A model class for database readings
    """
    __tablename__ = 'reading'

    id = Column(Integer, primary_key=True)
    sessionId = Column(Integer)
    timeLogged = Column(Integer)
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
            "timeLogged": float(self.timeLogged),
            "categoryId": self.categoryId,
            "value": self.value
        }

    def __str__(self):
        return json.dumps(self.to_dict())

class Session(SQL_BASE):
    """
    A model class for representing logging session
    """
    __tablename__ = 'session'

    id = Column(Integer, primary_key=True)
    available = Column(Boolean, default=False)
    timeStarted = Column(Integer)
    timeStopped = Column(Integer)
    numberOfReadings = Column(Integer)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "available": self.available,
            "timeStarted": float(self.timeStarted),
            "timeStopped": float(self.timeStopped),
            "numberOfReadings": self.numberOfReadings
        }

    def __str__(self):
        return json.dumps(self.to_dict())


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

    def __str__(self):
        return json.dumps(self.to_dict())


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

    def __str__(self):
        return json.dumps(self.to_dict())


class Cache(SQL_BASE):
    """
    A model which is derived from readings and is used for storing temporary (and incomplete)
    logging data whilst a session is in progress
    """
    __tablename__ = 'cache'

    id = Column(Integer, primary_key=True)
    timeLogged = Column(Integer)
    categoryId = Column(Integer)
    value = Column(String)

    def to_dict(self):
        """
        Returns the object in json format
        """
        return {
            "id": self.id,
            "timeLogged": float(self.timeLogged),
            "categoryId": self.categoryId,
            "value": self.value
        }

    def __str__(self):
        return json.dumps(self.to_dict())
