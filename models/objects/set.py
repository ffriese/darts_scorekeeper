import datetime
from typing import List

from sqlalchemy import Column, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import BaseObject
from models.helper import create_id_column
from models.objects.leg import Leg


class Set(BaseObject.Base):
    __tablename__ = 'sets'
    id = create_id_column('set')
    start_time = Column(DateTime)
    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    beginner_id = Column(Integer, ForeignKey('players.id'))
    winner_id = Column(Integer, ForeignKey('players.id'))
    game = relationship("Game", back_populates='sets')  # type: "Game"
    legs = relationship('Leg', order_by=Leg.start_time, single_parent=True,
                        passive_deletes='all', back_populates='set')  # type: List[Leg]
    beginner = relationship('Player', foreign_keys=[beginner_id], lazy='joined')
    winner = relationship('Player', foreign_keys=[winner_id], lazy='joined')

    def __init__(self, game: "Game", beginner: "Player", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.datetime.now()
        self.game = game
        self.beginner = beginner
