import datetime
from typing import List

from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from database import BaseObject
from models.helper import create_id_column
from models.objects.take import Take


class Leg(BaseObject.Base):
    __tablename__ = 'legs'
    id = create_id_column('leg')
    start_time = Column(DateTime)
    set_id = Column(Integer, ForeignKey('sets.id', ondelete='CASCADE'), nullable=False)
    beginner_id = Column(Integer, ForeignKey('players.id'))
    winner_id = Column(Integer, ForeignKey('players.id'))
    set = relationship('Set', back_populates='legs', single_parent=True,
                       lazy='joined')  # IF PROBLEMS ARISE RE-ADD passive_deletes='all' !!
    takes = relationship('Take', order_by=Take.start_time,
                         back_populates='leg', passive_deletes='all', lazy='joined')  # type: List[Take]
    beginner = relationship('Player', foreign_keys=[beginner_id])
    winner = relationship('Player', foreign_keys=[winner_id])

    def __init__(self, set: "Set", beginner: "Player", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.now()
        self.set = set
        self.beginner = beginner
