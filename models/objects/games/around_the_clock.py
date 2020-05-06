from sqlalchemy import Column, Integer, ForeignKey, orm

from database.types import DartIntent, TakeResult
from models.dartboard import Segment, Bed, DartBoard
from models.objects.dart import Dart
from models.objects.game import Game
from widgets.game_info_widgets.around_the_clock_info_widget import AroundTheClockInfoWidget
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class AroundTheClock(Game):
    def create_game_info_widget(self, parent) -> GameInfoWidget:
        return AroundTheClockInfoWidget(game=self, parent=parent)

    id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    __tablename__ = 'around_the_clock'
    __mapper_args__ = {
        'polymorphic_identity': 'around_the_clock',
        'polymorphic_load': 'inline'
    }

    def _recalculate_leg_scores(self):
        self.player_scores = {p: 1 for p in self.players}
        for take in self.get_current_leg().takes:
            for dart in take.darts:
                if dart.get_segment().sector == self.player_scores[take.player]:
                    self.player_scores[take.player] += 1

    def generate_next_dart(self) -> "Dart":
        player = self.get_current_player()
        target_segment = Segment(self.get_player_score(player), Bed.OUTER_SINGLE)
        target = DartBoard.get_center_estimate(target_segment)
        dart = Dart(player.get_current_take(), hit_location=DartBoard.aim_dart_at(
            target, player.horizontal_deviation, player.vertical_deviation
        ), target_location=target, intent=DartIntent.CHECKOUT)
        return dart

    def _handle_take_completion(self, player: "Player", updated=False) -> None:
        if self.get_player_score(player) == 21:
            player.darts_left = 0
            self._complete_take(player.get_current_take(), result=TakeResult.WIN)
        elif player.get_current_take().size() > 2:
            self._complete_take(player.get_current_take(), result=TakeResult.FINISHED)
