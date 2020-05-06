from typing import Tuple, Union, List

from PyQt5.QtGui import QColor
from sqlalchemy import Column, String, Float, orm
from sqlalchemy.orm import relationship
from database import BaseObject
from database.types import SQLSegment, IntList, TakeResult
from models.dartboard import Segment, Bed
from models.objects.game import Game
from models.helper import create_id_column
from models.objects.leg import Leg
from models.objects.take import Take


class Player(BaseObject.Base):
    __tablename__ = 'players'
    id = create_id_column('player')
    name = Column(String, unique=True)
    sound_file = Column(String)
    horizontal_deviation = Column(Float, default=35.0)
    vertical_deviation = Column(Float, default=45.0)
    preferred_scoring_segment = Column(SQLSegment, default=Segment(20, Bed.TRIPLE))
    preferred_doubles = Column(IntList, default=[20, 16, 8])
    games = relationship('Game', secondary='game_players', order_by=Game.start_time,
                         back_populates='players', lazy='dynamic')  # type: AppenderQuery
    all_takes = relationship('Take', back_populates='player', lazy='dynamic')  # type: AppenderQuery
    color = QColor(255, 0, 0)
    darts_left = 0
    _current_game = None
    _current_leg_takes = None
    _current_set_takes = None
    _current_game_takes = None
    _current_take = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset_cached_data()

    @orm.reconstructor
    def init_on_load(self):
        self.reset_cached_data()

    def reset_cached_data(self):
        self._current_game = None
        self._current_leg_takes = None
        self._current_set_takes = None
        self._current_game_takes = None
        self._current_take = None

    def remove_last_dart(self) -> Tuple[Union["Take", None], Union["Dart", None]]:
        if self.get_current_leg_takes() or self.get_current_game_takes():
            if not self.get_current_leg_takes():
                # noinspection PyProtectedMember
                self.get_current_game()._remove_last_leg()
            last_take = self.get_current_take()
            if last_take.size() > 0:
                removed_dart = last_take.darts.pop(last_take.size() - 1)
                last_take.result = None
                self.darts_left = 3 - last_take.size()
                if last_take.size() == 0:
                    print(self._current_leg_takes, last_take)
                    self.get_current_leg_takes().remove(last_take)
                    self._current_take = None
                return last_take, removed_dart
        return None, None

    def number_of_won_legs(self) -> int:
        return sum([1 for winning_leg in
                    self.get_current_game().get_current_set().legs if winning_leg.winner == self])

    def number_of_won_sets(self) -> int:
        return sum([1 for winning_set in
                    self.get_current_game().sets if winning_set.winner == self])

    def get_current_game(self) -> Game:
        if self._current_game is None:
            self._current_game = self.games[-1]
        return self._current_game

    def get_current_game_takes(self) -> List["Take"]:
        if True:  # self._current_game_takes is None:
            self._current_game_takes = self.all_takes.filter(
                Take.leg.has(Leg.set_id.in_([set.id for set in self.get_current_game().sets]))).all()
            # print('REINIT CURRENT GAME TAKES for', self.name, 'to len ', self._current_game_takes.__len__())
        return self._current_game_takes

    def get_current_leg_takes(self) -> List["Take"]:
        if self._current_leg_takes is None:
            try:
                cur_leg_id = self.get_current_game().sets[-1].legs[-1].id
                self._current_leg_takes = self.all_takes.filter(
                    Take.leg.has(Leg.id == cur_leg_id)).all()
                # print('REINIT CURRENT LEG TAKES for', self.name, 'to len ', self._current_leg_takes.__len__())
            except IndexError:
                return []
        return self._current_leg_takes

    def get_current_set_takes(self) -> List["Take"]:
        if True:  # self._current_set_takes is None:
            try:
                cur_set_id = self.get_current_game().sets[-1].id
                self._current_set_takes = self.all_takes.filter(
                Take.leg.has(Leg.set_id.in_([cur_set_id]))).all()
            except IndexError:
                return []
        return self._current_set_takes

    def get_darts_left(self):
        return self.darts_left

    def get_current_take(self) -> "Take":
        # print('get cgt for', self.name)
        if self._current_take is None:
            takes = self.get_current_game_takes()
            if takes:
                self._current_take = takes[-1]
        return self._current_take

    def get_cumulative_score(self) -> int:
        return sum([sum([dart.get_score() for dart in take.darts])
                    for take in self.get_current_leg_takes() if not take.result == TakeResult.BUST])

    def get_preferred_scoring_segment(self) -> Segment:
        if self.preferred_scoring_segment is not None:
            return self.preferred_scoring_segment
        else:
            return Segment(20, Bed.TRIPLE)

    def get_preferred_doubles(self):
        if self.preferred_doubles is not None:
            return self.preferred_doubles
        else:
            return [20, 16, 8]
