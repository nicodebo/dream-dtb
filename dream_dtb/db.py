import logging
import os
import pathlib
import pandas as pd
import numpy as np

from collections import OrderedDict
from sqlalchemy import Column
from sqlalchemy import Text
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DATE
from sqlalchemy import ForeignKey
from sqlalchemy import UniqueConstraint
from sqlalchemy import Table
from sqlalchemy.orm import backref
from sqlalchemy.orm import relationship
from sqlalchemy_utils import create_database
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import Timestamp
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect

from dream_dtb.util import Singleton
from dream_dtb.util import session_scope
from dream_dtb import Base
from dream_dtb import Engine

logger = logging.getLogger('dream_logger')

def object_as_dict(obj):
    return {c.key: getattr(obj, c.key)
            for c in inspect(obj).mapper.column_attrs}


class InitDb(metaclass=Singleton):
    """ A singleton class that initialize the database """

    def __init__(self, engine, base):
        self.engine = engine
        self.base = base
        self.createDb()
        self.popDb()

    def createDb(self):
        """ Create database if does not exists """
        if not database_exists(self.engine.url):
            logger.info("database does not exists")
            pathlib.Path(os.path.dirname(self.engine.url.database)).mkdir(parents=True,
                                                                          exist_ok=True)
            create_database(self.engine.url)
        else:
            logger.info("database already exists")

    def popDb(self):
        """ Generate tables """
        self.base.metadata.create_all(self.engine)


class Tag(Base):

    label = Column(String, unique=True)

    def __repr__(self):
        return "<Label(tag='{}')>".format(self.label)


class DreamType(Base):

    label = Column(String, unique=True)

    def __repr__(self):
        return "<DreamType(dream_type='{}')>".format(self.label)


tags = Table('tags', Base.metadata,
             Column('dream_id', Integer, ForeignKey('dream.id')),
             Column('tag_id', Integer, ForeignKey('tag.id'))
             )

drtype = Table('drtype', Base.metadata,
               Column('dream_id', Integer, ForeignKey('dream.id')),
               Column('type_id', Integer, ForeignKey('dreamtype.id'))
               )


class Dream(Base, Timestamp):

    title = Column(String, nullable=False)
    recit = Column(Text)
    date = Column(DATE, nullable=False)
    tags = relationship('Tag', secondary=tags,
                        backref=backref('dreams', lazy='dynamic'))
    drtype = relationship('DreamType', secondary=drtype,
                          backref=backref('dreams', lazy='dynamic'))

    __table_args__ = (UniqueConstraint('title', 'date', name='_title_date_uc'),)

    def __repr__(self):

        # TODO: use self.get_tags and self.get_drtype
        if not self.tags:
            tags = "no tags defined !"
        elif len(self.tags) == 1:
            tags = self.tags[0].label
        else:
            tags = ', '.join([elem.label for elem in self.tags])

        if not self.drtype:
            drtype = "no type defined !"
        else:
            drtype = self.drtype[0].label

        return "Dream<(\n'{}:{}: {}'\n{}\ntype: {}\ntags: {}\n)>".format(self.title,
                                                                         self.id,
                                                                         self.date,
                                                                         self.recit,
                                                                         drtype,
                                                                         tags)

    def get_tags(self):
        """ return tags associated with self has a list of strings
        """
        tmp_tags = []
        for elem in self.tags:
            tmp_tags.append(elem.label)
        return tmp_tags

    def get_drtype(self):
        """ return the dreamtype associated with self as a string
        """
        tmp_drtype = []
        for elem in self.drtype:
            tmp_drtype.append(elem.label)

        if tmp_drtype:
            return tmp_drtype[0]
        else:
            return ""


class TagDAO:

    @classmethod
    def create(cls, tag):
        """
        Arguments:
                - tag (str)
        """

        record = Tag(label=tag)
        try:
            with session_scope() as session:
                session.add(record)
        except IntegrityError:
            logger.info(f'duplicate Tag: {tag}')

    @classmethod
    def find(cls, labels):
        """ Arguments:
            - labels: list(str): a list of strings
        """
        with session_scope() as session:
            obj = session.query(Tag).filter(Tag.label.in_(labels))
        return obj

    @classmethod
    def get_labels(cls):
        """ Return the list of defined labels
        """
        labels = []
        with session_scope() as session:
            for inst in session.query(Tag):
                labels.append(inst.label)
        return labels


class DreamTypeDAO:

    @classmethod
    def create(cls, drtype):
        record = DreamType(label=drtype)
        try:
            with session_scope() as session:
                session.add(record)
        except IntegrityError:
            logger.info(f'duplicate DreamType: {drtype}')

    @classmethod
    def find(cls, labels):
        """ Arguments:
            - labels: list(str): a list of strings
        """
        with session_scope() as session:
            obj = session.query(DreamType).filter(DreamType.label.in_(labels))
        return obj

    @classmethod
    def get_labels(cls):
        """ Return the list of defined labels
        """
        labels = []
        with session_scope() as session:
            for inst in session.query(DreamType):
                labels.append(inst.label)
        return labels


class DreamDAO:

    @classmethod
    def create(cls, instance):
        """ Arguments:
            - instance (dict): dictionnary containing row attributes and values
                - title (str): dream title
                - date (datetime): date of the dream
                - recit (str): the corpus of the dream
                - tags (list(str)): a list of tags
                - drtype (str): a dream type (normal, lucid, ...)
        """
        record = Dream(title=instance['title'],
                       recit=instance['recit'],
                       date=instance['date'])
        idnum = None
        try:
            with session_scope() as session:
                session.add(record)
                session.flush()
                idnum = record.id
        except IntegrityError:
            logger.info("duplicate Dream")

        if idnum is not None:
            cls._add_tags(idnum, instance['tags'])
            cls._add_drtype(idnum, instance['drtype'])

        return idnum

    @classmethod
    def update(cls, idnum, instance):
        # TODO: replace id --> idNum in every file because seems to be a keyword
        # TODO: update and create too much code duplication
        if instance['tags'] is None:
            instance['tags'] = []
        if instance['drtype'] is None:
            instance['drtype'] = ''

        if instance['tags']:
            for elem in instance['tags']:
                TagDAO.create(elem)

        if instance['drtype']:
            DreamTypeDAO.create(instance['drtype'])

        try:
            with session_scope() as session:
                record = session.query(Dream).filter_by(id=idnum).one()
                # # TODO: This is wrong, I need to check record.tags against
                # # instance['tags'] and remove/add the necessary tags.
                # if tags:
                #     tags_rec = session.query(Tag).filter(Tag.label.in_(tags))
                #     for elem in tags_rec:
                #         record.tags.append(elem)
                # # TODO: This is wrong, I need to check record.tags against
                # # instance['drtype'] and remove/add the necessary tags.
                # if drtype:
                #     drtype_rec = session.query(DreamType).filter(DreamType.label == drtype).first()
                #     record.drtype.append(drtype_rec)
                record.date = instance['date']
                record.title = instance['title']
                record.recit = instance['recit']
                session.add(record)
        except IntegrityError:
            logger.info("error bli")

    @classmethod
    def find_by_id(cls, idnum):
        """ Find a record by id
            Arguments:
            - idnum(int): identity field (primary key) of the table
            Return:
            obj: a query object
        """
        logger.info(f'find by id: {idnum}')
        try:
            with session_scope() as session:
                obj = session.query(Dream).filter(Dream.id == idnum).one()
                record = object_as_dict(obj)  # as a dict
                record['tags'] = obj.get_tags()
                record['drtype'] = obj.get_drtype()
        except:
            logger.info("find by id error")

        return record

    @classmethod
    def _add_tags(cls, idnum, tags=None):
        """ append tags to record whose id = idnum
        """

        if tags is None:
            tags = []
        # TODO: remove empty string or space tags from tags list '' ' '

        if tags:
            for elem in tags:
                TagDAO.create(elem)

            try:
                with session_scope() as session:
                    instance = session.query(Dream).filter(Dream.id==idnum).one()
                    tags_rec = session.query(Tag).filter(Tag.label.in_(tags))
                    for elem in tags_rec:
                        if tags_rec not in instance.tags:
                            instance.tags.append(elem)
            except:
                logger.info("append tags error")
                raise

    @classmethod
    def _add_drtype(cls, idnum, drtype=None):
        if drtype is None:
            drtype = ''

        if drtype:
            DreamTypeDAO.create(drtype)

            # TODO: either use .one() or .first() but not both.
            try:
                with session_scope() as session:
                    instance = session.query(Dream).filter(Dream.id == idnum).one()
                    drtype_rec = session.query(DreamType).filter(DreamType.label == drtype).first()
                    if drtype_rec not in instance.drtype:
                        instance.drtype.append(drtype_rec)
            except:
                logger.info("append drtype error")

    @classmethod
    def get_tree(cls):

        tree = OrderedDict()

        with session_scope() as session:
            instances = session.query(Dream).order_by(Dream.date, Dream.created)
            nbrows = instances.count()
            dftree = pd.DataFrame(index = np.arange(0, nbrows), columns=['year', 'month', 'day', 'id', 'title'])
            for i, inst in enumerate(instances):
                year = inst.date.strftime('%Y')
                month = inst.date.strftime('%m')
                day = inst.date.strftime('%d')
                dftree.loc[i] = [year, month, day, inst.id, inst.title]

        dftree.apply(cls.poptree, args=(tree,), axis=1)

        return(tree)

    @staticmethod
    def poptree(row, tree):
        """ A helper function to be used with an dataframe.apply function
        """
        if row['year'] not in tree:
            tree[row['year']] = OrderedDict()
        if row['month'] not in tree[row['year']]:
            tree[row['year']][row['month']] = OrderedDict()

        tree[row['year']][row['month']].setdefault(row['day'], []).append([row['title'], row['id']])


# initialize database
InitDb(Engine, Base)
# TODO: Move all DAO classes into its own file ?
# TODO: Singleton seems useless
