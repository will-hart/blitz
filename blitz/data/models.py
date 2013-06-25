__author__ = 'mecharius'

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, DateTime, Boolean

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
    category = Column(Integer)
    value = Column(String)


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


class Config(SQL_BASE):
    """
    A model class for representing key:value settings for the application and client application
    """
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True)
    key = Column(String)
    value = Column(String)


class Category(SQL_BASE):
    """
    A model class for representing categories (or variables) that have been logged in the database
    """
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    variableName = Column(String, unique=True)
