"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Models of the database.
"""

import logging
import os.path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Test(Base):
    __tablename__ = 'test'
    id = Column(Integer, primary_key=True)
    image_id = Column(String(250), nullable=False)  # Docker image ID
    number_of_containers = Column(Integer)  # Number of containers to create in the test
    repetitions = Column(Integer)  # Times the test will be repeated
    runs = relationship('Run', backref="test")

class Run(Base):
    __tablename__ = 'run'
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey('test.id'))
    started = Column(DateTime, default=datetime.now)
    ended = Column(DateTime)
    containers = relationship('Container', backref='run')
    disk = relationship('DiskRequired', uselist=False, backref='run')

class Container(Base):
    __tablename__ = 'container'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('run.id'))
    docker_id = Column(String(250))  # Docker ID
    cpu = relationship('CpuRequired', uselist=False, backref='container')  # One to one
    memory = relationship('MemoryRequired', uselist=False, backref='container')  # One to one
    creation_time = relationship('CreationTime', uselist=False, backref='container')  # One to one

class DiskRequired(Base):
    __tablename__ = 'disk'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('run.id'))
    size = Column(Integer)  # In MB?

class MemoryRequired(Base):
    __tablename__ = 'memory'
    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('container.id'))
    size = Column(Integer)  # In MB?

class CreationTime(Base):
    __tablename__ = 'creation'
    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('container.id'))
    startup_time = Column(Integer)  # In ms?

class CpuRequired(Base):
    __tablename__ = 'cpu'
    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey('container.id'))
    total_cpu = Column(Integer)  # nanoseconds?
    percentual_cpu = Column(Float)


class PerformanceTestDAO(object):
    def __init__(self, database_path):
        database_url = 'sqlite:///' + database_path
        engine = create_engine(database_url)
        self._create_database_if_not_exist(database_path, engine)
        Base.metadata.bind = engine
        self.session_maker = sessionmaker(bind=engine)


    def _create_database_if_not_exist(self, database_path, engine):
        if not os.path.isfile(database_path):
            logging.info('Creating database "%s"...' % database_path)
            # Create all tables in the engine. This is equivalent to "Create Table"
            # statements in raw SQL.
            Base.metadata.create_all(engine)

    def create_session(self):
        return self.session_maker()
