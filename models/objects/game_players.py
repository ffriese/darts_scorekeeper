from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from database import BaseObject


class GamePlayers(BaseObject.Base):
    __tablename__ = 'game_players'
    game_id = Column(Integer, ForeignKey('games.id'), primary_key=True)
    player_id = Column(Integer, ForeignKey('players.id'), primary_key=True)
    player_index = Column(Integer)
    player = relationship("Player")
    game = relationship("Game", back_populates='game_players')

    def __init__(self, game: "Game", player: "Player", player_index: int):
        self.player = player
        self.game = game
        self.player_index = player_index
