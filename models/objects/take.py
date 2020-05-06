import datetime
from typing import List

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from database import BaseObject
from database.types import TakeResult
from models.helper import create_id_column
from models.objects.dart import Dart


class Take(BaseObject.Base):
    __tablename__ = 'takes'
    id = create_id_column('take')
    leg_id = Column(Integer, ForeignKey('legs.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(Integer, ForeignKey('players.id'))
    start_time = Column(DateTime)
    result = Column(Enum(TakeResult))
    leg = relationship('Leg', back_populates='takes', single_parent=True,
                       lazy='joined')  # IF PROBLEMS ARISE RE-ADD passive_deletes='all' !!
    player = relationship('Player', back_populates='all_takes', lazy='joined')
    darts = relationship('Dart', order_by=Dart.time_stamp, back_populates='take',
                         lazy='joined')  # type: List[Dart]

    def __init__(self, leg: "Leg", player: "Player", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.now()
        self.leg = leg
        self.player = player

    def size(self) -> int:
        return len(self.darts)

    def add_dart(self, dart: Dart):
        self.darts.append(dart)

    def is_complete(self) -> bool:
        return self.result is not None

    def get_score(self) -> int:
        return sum([dart.get_score() for dart in self.darts]) if not self.result == TakeResult.BUST else 0

    def __repr__(self):
        return '%s<%s, %s>' % (self.__class__.__name__, self.id, self.darts)
