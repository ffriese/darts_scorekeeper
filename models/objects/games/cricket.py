from typing import List

from sqlalchemy import Column, Integer, ForeignKey, Boolean

from database.types import DartIntent, TakeResult
from models.dartboard import Segment, Bed, DartBoard
from models.helper import Option
from models.objects.dart import Dart
from models.objects.game import Game
from widgets.game_info_widgets.cricket_info_widget import CricketInfoWidget
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class Cricket(Game):
    def create_game_info_widget(self, parent) -> GameInfoWidget:
        return CricketInfoWidget(game=self, parent=parent)

    id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    cut_throat = Column(Boolean)
    __tablename__ = 'cricket'
    __mapper_args__ = {
        'polymorphic_identity': 'cricket',
        'polymorphic_load': 'inline'
    }
    goal_segments = [20, 19, 18, 17, 16, 15, 25]
    sector_hits = {}

    @classmethod
    def get_option_list(cls) -> List[Option]:
        options = super().get_option_list()
        options.extend(
            [
                Option('cut_throat', bool)
            ]
        )
        return options

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _set_defaults(self):
        super()._set_defaults()
        self.win_function = min if self.cut_throat else max

    def is_closed(self, sector):
        return min(self.sector_hits[sector].values()) >= 3

    def is_closed_by_all_opponents_of(self, player: "Player", sector: int):
        return min([self.sector_hits[sector][p] for p in self.players if p != player]) >= 3

    def _recalculate_leg_scores(self):
        self.sector_hits = {
            s: {p: 0 for p in self.players} for s in self.goal_segments
        }
        self.player_scores = {p: 0 for p in self.players}
        for take in self.get_current_leg().takes:
            for dart in take.darts:
                if dart.get_segment().sector in self.goal_segments:

                    if not self.is_closed(dart.get_segment().sector):
                        for hit in range(dart.get_segment().bed.get_multiplier()):
                            self.sector_hits[dart.get_segment().sector][take.player] += 1
                            if self.is_closed(dart.get_segment().sector):
                                break
                        diff = min(dart.get_segment().bed.get_multiplier(),
                                   self.sector_hits[dart.get_segment().sector][take.player] - 3)
                        if diff > 0:
                            if self.cut_throat:
                                for p in self.players:
                                    if p != take.player and self.sector_hits[dart.get_segment().sector][p] < 3:
                                        self.player_scores[p] += diff * dart.get_segment().sector
                            else:
                                self.player_scores[take.player] += diff * dart.get_segment().sector

    def add_dart(self, dart: "Dart") -> None:
        super().add_dart(dart)

    def undo_dart(self) -> None:
        super().undo_dart()
        self.updated.emit()

    @staticmethod
    def max_sector(sectors: List[int]):
        # bulls-eye is hard, dont choose this for scoring if there is another option...
        values = {sector: 25 if sector == 25 else sector * 3 for sector in sectors}
        return max(values, key=values.get)

    def generate_next_dart(self) -> "Dart":
        player = self.get_current_player()
        if self.player_scores[player] == self.win_function(self.player_scores.values()):
            # player is leading -> close next highest segment
            sc = self.max_sector([gs for gs in self.goal_segments if not self.sector_hits[gs][player] > 2])
        else:
            # player is behind -> find scoring segment
            if self.cut_throat:
                # find scoring segment to attack the leading player
                best_player = min(self.player_scores, key=self.player_scores.get)
                print('detected opponent:', best_player.name)
                sc = self.max_sector([gs for gs in self.goal_segments if not self.sector_hits[gs][best_player] > 2])
            else:
                # find highest possible scoring segment
                sc = self.max_sector([gs for gs in self.goal_segments if not self.is_closed_by_all_opponents_of(player, gs)])

        target_segment = Segment(sc, Bed.DOUBLE if sc == 25 else Bed.TRIPLE)
        target = DartBoard.get_center_estimate(target_segment)
        dart = Dart(player.get_current_take(), hit_location=DartBoard.aim_dart_at(
            target, player.horizontal_deviation, player.vertical_deviation
        ), target_location=target, intent=DartIntent.CHECKOUT)
        return dart

    def _handle_take_completion(self, player: "Player", updated=False) -> None:
        if self.get_player_score(player) == self.win_function(self.player_scores.values()) and \
                min([sector_hits[player] for sector_hits in self.sector_hits.values()]) >= 3:
            player.darts_left = 0
            self._complete_take(player.get_current_take(), result=TakeResult.WIN)
        elif player.get_current_take().size() > 2:
            self._complete_take(player.get_current_take(), result=TakeResult.FINISHED)
