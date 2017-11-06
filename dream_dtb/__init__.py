import os
import logging
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.declarative import declarative_base
from dream_dtb import config

logger = logging.getLogger('dream_logger')

def init_xdg_dir(filepaths):
    """ Create necessary directories
    Arguments:
        -filepaths(list(str)): list of absolute file paths
    """
    for path in filepaths:
        os.makedirs(os.path.dirname(path), exist_ok=True)


logger.info("init xdg dir")
init_xdg_dir([config.DB_PATH, config.IPC_PATH, config.LOG_PATH])


class BaseMixin():
    """ Mixin that define the table name as the lower case class name and add
    an index
    """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True)


Base = declarative_base(cls=BaseMixin)
db_uri = 'sqlite:///{}'.format(config.DB_PATH)
# Engine = create_engine(db_uri, echo=True)  # debug mode
Engine = create_engine(db_uri)
Session = sessionmaker(bind=Engine)
