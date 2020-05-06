from typing import List

from sqlalchemy import Column, Integer, ForeignKey, Boolean, orm

from database.types import DartIntent, TakeResult
from models.dartboard import DartBoard, Bed, Segment
from models.helper import Option
from models.objects.dart import Dart
from models.objects.game import Game
from widgets.game_info_widgets.x01_info_widget import X01InfoWidget
from widgets.game_info_widgets.game_info_widget import GameInfoWidget


class X01(Game):

    def create_game_info_widget(self, parent) -> GameInfoWidget:
        return X01InfoWidget(game=self, parent=parent)

    __tablename__ = 'x01'
    id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    double_out = Column(Boolean)
    double_in = Column(Boolean)
    x = Column(Integer, default=3)
    __mapper_args__ = {
        'polymorphic_identity': 'x01',
        'polymorphic_load': 'inline'
    }

    @classmethod
    def get_option_list(cls) -> List[Option]:
        options = super().get_option_list()
        options.extend(
            [
                Option('x', int, list(range(1, 10))),
                Option('double_out', bool),
                Option('double_in', bool)
            ]
        )
        return options

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_score = (self.x * 100) + 1

    @orm.reconstructor
    def init_on_load(self):
        self.target_score = (self.x * 100) + 1
        super().init_on_load()

    def __repr__(self):
        info = dict(self.__dict__)
        while not 'id' in info.keys():
            print('WEIRD BUG. WORKAROUND....')
            import time
            time.sleep(0.0001)
            info = dict(self.__dict__)
        info['type'] = '%s01' % self.x
        if self.double_out:
            info['type'] += ' DO'
        if self.double_in:
            info['type'] += ' DI'
        try:
            return '{id}: {type} - {start_time}'.format(**info)
        except KeyError:
            return '%r' % info

    def get_name(self):
        return '%s01' % self.x

    def _recalculate_leg_scores(self):
        self.player_scores = {p: (self.x*100 + 1) for p in self.players}
        for take in self.get_current_leg().takes:
            if not take.result == TakeResult.BUST:
                self.player_scores[take.player] -= sum(d.get_score() for d in take.darts)

    def generate_next_dart(self) -> "Dart":
        player = self.get_current_player()
        score = self.get_player_score(player)
        target_segment = None
        intent = DartIntent.SCORE
        if score > 100:
            # scoring
            target_segment = player.get_preferred_scoring_segment()
            print(player.name, 'with', score, '-> trying to score on', target_segment)
        else:
            available_scores = DartBoard.get_available_scores()
            if self.double_out:
                available_scores = {score: [s for s in segments if s.bed == Bed.DOUBLE] for score, segments in
                                    available_scores.items() if [s for s in segments if s.bed == Bed.DOUBLE]}
                print('DOUBLEOUT:', available_scores)
            if score in available_scores.keys():
                # CHECKOUT POSSIBLE!
                if self.double_out:
                    target_segment = Segment(int(score/2), Bed.DOUBLE)
                else:
                    target_segment = DartBoard.easiest_segment_for_score(score)
                intent = DartIntent.CHECKOUT
            else:
                # SETUP NEEDED
                intent = DartIntent.SETUP
                if self.double_out:
                    for dbl in player.preferred_doubles:
                        print('testing', dbl, 'for score', score, ':', score - (2 * dbl))
                        if score - (2 * dbl) in DartBoard.get_available_scores().keys():
                            target_segment = DartBoard.easiest_segment_for_score(score - 2 * dbl)
                            print('GOT: ', target_segment)
                            break
                    if target_segment is None:
                        if score < 40:
                            target_segment = Segment(1, Bed.OUTER_SINGLE)
                        else:
                            # TODO: find better ways
                            target_segment = Segment(25, Bed.DOUBLE)
                else:
                    if score > 60:
                        # TODO: find better ways
                        target_segment = Segment(25, Bed.DOUBLE)
                    elif score > 40:
                        target_segment = Segment(score - 40, Bed.OUTER_SINGLE)
                    elif score > 20:
                        target_segment = Segment(score - 20, Bed.OUTER_SINGLE)

        target = DartBoard.get_center_estimate(target_segment)
        dart = Dart(player.get_current_take(), hit_location=DartBoard.aim_dart_at(
            target, player.horizontal_deviation, player.vertical_deviation
        ), target_location=target, intent=intent)
        return dart

    def _handle_take_completion(self, player: "Player", updated=False) -> None:
        score = self.get_player_score(player)
        if score < 0 or (self.double_out and score == 0
                         and player.get_current_take().darts[-1].get_segment().bed != Bed.DOUBLE):
            self._complete_take(player.get_current_take(), result=TakeResult.BUST)
        elif score == 0:
            self._complete_take(player.get_current_take(), result=TakeResult.WIN)
        elif player.get_current_take().size() > 2:
            self._complete_take(player.get_current_take(), result=TakeResult.FINISHED)

    def _announce_take_result(self, score: int):
        from controllers.sound_controller import SoundController, SoundJob
        SoundController.instance().play_job(SoundJob.from_score(score), blocking=self.enable_blocking)

    def _next_player(self, delay_ms=0, skip_introduce=False) -> None:
        if not skip_introduce:
            from controllers.sound_controller import SoundJob
            jobs = []
            score = self.get_player_score(self.get_player_after(self.get_current_player()))
            if score <= 180:
                jobs.append(SoundJob.from_required_score(score))
        else:
            jobs = None
        super()._next_player(sound_jobs=jobs, skip_introduce=skip_introduce)
